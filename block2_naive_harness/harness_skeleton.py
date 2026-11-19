"""Build the naive harness: fill in the TWO small gaps in the agent loop.

The loop structure, tool dispatcher, client setup, and tool schemas are all
provided. You write the two moments that matter most:

  TODO 1 — ask the model what to do next   (~4 lines)
  TODO 2 — execute a tool and feed the result back   (~5 lines)

Usage: uv run harness_skeleton.py <workspace_dir> "<task instructions>"

Check yourself against solution/harness.py if you get stuck.
"""

import json
from collections import Counter
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import TOOL_SCHEMAS, Workspace, print_run_header  # noqa: E402
from scoreboard import Scoreboard  # noqa: E402  (observer-side commentary)

SYSTEM_PROMPT = """You are a coding agent operating on a local workspace via tools.
Work step by step: inspect files, make edits, and run the tests to check yourself.
The task is complete only when run_tests reports that every test passed.
When the tests are green, reply with a short summary instead of calling tools."""

# The loop budget, a real harness decision. 20 turns is plenty for the
# short tasks and about what the long one needs, with no margin. The
# model is never told how many it has.
MAX_TURNS = 20


def run(workspace_dir: str, task: str) -> None:
    """Drive one agent session: give the model a task and a set of tools,
    then loop — model call, tool execution, results fed back — until the
    model stops calling tools (its way of saying "done") or MAX_TURNS runs
    out.

    `workspace_dir` is the directory the tools operate in; `task` is the
    natural-language instruction that becomes the first user message. The
    conversation (`messages`) is the agent's entire memory: every
    file read, tool result, and edit accumulates there, and the full list is
    resent to the model on every turn.
    """
    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )
    model = os.environ["LLM_MODEL"]
    ws = Workspace(workspace_dir)
    # What this run works on and calls (never the key): the first thing to
    # check when two runs disagree. Blocks 3 and 4 open the same way.
    print_run_header(f"naive harness × {ws.root.parent.name}", [
        ("workspace", os.path.relpath(ws.root)),
        ("task", task),
        ("provider", os.environ["LLM_BASE_URL"]),
        ("model", model),
    ])

    # The tool dispatcher: the bridge between what the model SAYS and what
    # actually HAPPENS. The model only ever emits a tool name plus JSON
    # arguments — it cannot touch the filesystem itself. This dict maps each
    # name from TOOL_SCHEMAS to the code that really runs. Every key here is
    # a capability you've granted the agent; anything not in this dict, the
    # agent simply cannot do. (In production harnesses this same idea grows
    # into permissions, sandboxing, and guardrails.) You'll use it in TODO 2.
    dispatch = {
        "list_files": lambda args: ws.list_files(),
        "read_file": lambda args: ws.read_file(args["path"]),
        "write_file": lambda args: ws.write_file(args["path"], args["content"]),
        "search": lambda args: ws.search(args["pattern"]),
        "run_tests": lambda args: ws.run_tests(),
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    # Commentary for you, not for the agent — see scoreboard.py. Nothing below
    # changes what the model sees or what the loop does.
    board = Scoreboard(MAX_TURNS)
    board.legend()

    for turn in range(1, MAX_TURNS + 1):
        # ------------------------------------------------------------------
        # TODO 1 — ask the model what to do next (~4 lines)
        #
        # Call the chat completions API, passing the FULL conversation so
        # far and the tool schemas:
        #
        #   response = client.chat.completions.create(
        #       model=model, messages=messages,
        #       tools=TOOL_SCHEMAS, temperature=0.1)
        #
        # On api.anthropic.com, leave out temperature=0.1: Anthropic's newer
        # models reject it with a 400 error.
        #
        # Notice: `messages` — the whole conversation — goes over the wire on
        # EVERY turn. That fact will matter later today.
        # ------------------------------------------------------------------
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0.1,
        )

        board.record_usage(response)
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            print(f"\033[1;32m❝  [turn {turn}] agent finished:\033[0m"
                  f"\n\033[32m{msg.content}\033[0m")
            board.summary(finished=True, turn=turn)
            return

        # Models often narrate alongside their tool calls ("the tests expect
        # X, so I'll..."), but on many turns content is empty and the intent
        # lives only in the tool calls themselves. Show both: narration when
        # present, plus which tools this turn reaches for. Makes the agent
        # watchable — and lets you see the moment its plan starts to drift.
        # The turn number goes on this line once, with a count of each tool
        # it calls; the calls themselves are listed below it.
        counts = Counter(c.function.name for c in msg.tool_calls)
        tally = ", ".join(f"{n} × {name}" for name, n in counts.items())
        narration = msg.content.strip() if msg.content else "(no commentary)"
        print(f"\033[32m❝  [turn {turn}] agent says: {narration}\033[0m  [{tally}]")

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            board.record_tool(name, turn, args)
            print(f"     {name}({', '.join((f'{k}={v!r}' if k == 'path' else f'{k}={str(v)[:40]!r}') for k, v in args.items())})")
            # --------------------------------------------------------------
            # TODO 2 — execute the tool, feed the result back (~5 lines)
            #
            # Look up `name` in `dispatch` and invoke it with `args`. If it
            # raises, use f"tool error: {exc}" as the result instead. Then
            # append the result so the model sees it next turn:
            #
            #   messages.append(
            #       {"role": "tool", "tool_call_id": call.id,
            #        "content": result})
            # --------------------------------------------------------------
            try:
                result = dispatch[name](args)
            except Exception as exc:
                result = f"tool error: {exc}"

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

        board.report(turn, messages)

    board.summary(finished=False, workspace=ws)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the naive agent harness on a task.",
        epilog='Example: uv run harness_skeleton.py tasks/short/01_fix_bug/workspace '
        '"Two tests fail. Find the bug and fix it."',
    )
    parser.add_argument(
        "workspace",
        help="directory the agent operates on — its tools can only see files under this root",
    )
    parser.add_argument(
        "task",
        help="natural-language instruction for the agent (quote it); becomes the first user message",
    )
    cli = parser.parse_args()
    run(cli.workspace, cli.task)
