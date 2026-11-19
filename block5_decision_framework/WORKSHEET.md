# Harness decision worksheet

Pick an agent you're working on, or one you'll build soon. Answer four
questions about it, then decide. In the workshop you have 12 minutes:
questions 1 and 2, then the decision. Questions 3 and 4 can wait until
after. Short answers are fine. Why each question matters, with what we saw this morning:
[WHY.md](WHY.md).

## Your agent

- **What does it do?** An AI agent integrated with Trinity that uses MCP tools to search and retrieve information from Hangar, TIMS, and Paperplane, including signatures, rulesets, and tasking statuses.
- **Model it uses today, and who serves it:** GPT-5.6
  - *For example: Claude from Anthropic, GPT from Azure, an open model from Fireworks.*

## Questions 1 and 2 can rule a harness out

**1. Will it work with your model and your code?**

- Will you need to switch model providers? ☐ yes ☐ no ☑ not sure
- Will it go into an existing project, next to the libraries already there? ☑ yes ☐ no
  - *If yes, install it into your real project before you compare anything.*

**2. What will you need to add or change?**

- Steps it must take whatever the model decides (an approval, a spending limit, "done means the tests pass"):
  1. Verify user permissions before executing MCP tools and require approval for sensitive write operations.
  2. Handle tool errors, limit large responses, and log tool calls for troubleshooting.
- Its unit of work (one file? one record? one rule?): One MCP tool operation, such as searching signatures, retrieving a ruleset, or creating a tag.
  - *On the migration, tools that didn't match the unit of work cost 2 to 4 times the tokens.*

## Now rule them out

**In our runs, one thing crossed harnesses out: switching providers.** If
you'll switch, cross out Claude Agent SDK and OpenAI Agents, unless you'd
pay to leave them later, and Google ADK too if adding LiteLLM to your
project is a problem. Every harness had somewhere to plug your steps in,
and its own tools only decide adopt or extend. If your agent differs from
ours, the rules and the table below are what we saw for each harness:

- **Switching providers?** Cross out the ones that needed workarounds off
  their own model, unless you'd pay to leave them later.
- **A step you need has nowhere to plug in?** Cross it out.
- **Its own tools don't match your unit of work?** Keep it, but you'll be
  extending it.

| Harness | Off its own model (question 1) | Its own tools (question 2) | Where you plug in (question 2) | Still standing? |
|---|---|---|---|---|
| Claude Agent SDK | Bearer auth through `ANTHROPIC_AUTH_TOKEN`, plus an unrecognized-model warning; built for Anthropic's API | Claude Code's whole kit, Bash included (you can switch them off) | hooks (`PreToolUse`, `PostToolUse`, `Stop`, …), `can_use_tool` | ☐ Pending provider compatibility |
| OpenAI Agents | an explicit model object, and tracing to OpenAI turned off; its own shell tools don't work off OpenAI | none that work off OpenAI: you write them | `RunHooks`, guardrails, `needs_approval` | ☐ Pending provider compatibility |
| Google ADK | needs LiteLLM to reach other providers; shares an environment with OpenAI Agents only with LiteLLM held at 1.83 | none for this kind of task: you write them | `before_tool_callback` (and the other callbacks), plugins | ☐ Pending dependency compatibility |
| Deep Agents | none: any LangChain model | its own file tools, subagents, and a shell if you add one | LangChain callbacks, `interrupt_on`, `HarnessProfile` | ☑ Candidate |
| Pydantic AI | none: the provider is a setting | none for this kind of task: you write them | `event_stream_handler`, `requires_approval` | ☑ Preferred candidate |

## Questions 3 and 4 are your job, whichever harness you pick

**3. What can your agent reach or affect?** Tick all that apply.

- ☐ files outside its own folder
- ☐ code it runs (the test runner counts)
- ☐ a shell
- ☑ money, customers or production (potential access to internal systems and production data, depending on deployment)

*Each tick is something to sandbox, limit, or guard inside a tool.*

**4. What will you need to watch?**

- **Cost.** Every call re-sends the whole conversation, so its size sets
  the cost.
  - Model calls per run: ☑ under ten (estimated) ☐ dozens ☐ a hundred or more
  - Biggest thing a tool returns: ☑ a screen of text (typical response) ☐ whole files or logs
  - *Ticked dozens or more, or whole files? Find out how the harness keeps the conversation from growing. Otherwise a lighter harness costs less.*
- **The trace.** In it, I'll need:
  - ☑ what the model is actually sent
  - ☑ every tool call with its arguments
  - ☐ when it ran the tests
  - ☑ cost per step

## Decide

- ☐ **Adopt:** a harness still standing, whose built-in settings plus the tools you write anyway cover your steps from question 2
- ☑ **Extend:** a harness still standing, but you'll write code into its hooks, or change or replace its defaults and tools
- ☐ **Drop down a level or build:** every harness is crossed out (rarely right; Blocks 2 and 3 showed what building costs)

If more than one is still standing, use 3 and 4 to choose: the lighter one for a small conversation, the one that already shows what you need to watch.

**The harness I'd adopt or extend:** Pydantic AI, if compatible with Trinity, using our existing FastMCP tools and custom approval, validation, and logging controls. Otherwise, extend the existing Trinity agent infrastructure directly.

**What's still my job (from 3 and 4):** Maintaining MCP tools, enforcing authentication and permissions, validating responses, handling errors, and monitoring tool calls, performance, and cost.

**In a design review, I'd say (with a number you have, or the one you'll
measure and the value that would change your mind):**

*For example: "We'll extend OpenAI Agents with our own rename tool,
because on our migration it cut the tool calls from 278–315 to 35–88
per run. We'd look again if another harness matched that on the same
test."*

*Or, before you've measured: "We'll adopt Pydantic AI, because our
provider will change. We'll replay 50 past tickets and count refunds
that differ from what the team did; above 2%, we'd look again."*

______________________________________________________________________
"I'd extend Pydantic AI with our existing MCP tools if it integrates with Trinity, rather than build a new harness. In Block 4, a better tool reduced calls from 275 to 49. I'd aim to reduce unnecessary MCP tool calls by at least 30% without lowering task accuracy or weakening security. I'd reconsider if the framework introduced integration problems or failed to meet our approval and authorization requirements."

- **I'd test it by:** Running 20 representative Hangar/TIMS/Paperplane tasks several times using the same model, prompts, and budget. Compare accuracy, tool calls, tokens, and execution traces, and independently verify API results and permission enforcement.
  - *Several runs, the same prompt and budget, and check the results yourself.*
