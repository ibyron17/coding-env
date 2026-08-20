# Performance Optimization

## Model Selection Strategy

**Haiku** (90% of Sonnet capability, 3x cost savings):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet** (Best coding model):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus** (Deepest reasoning):
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Extended Thinking + Plan Mode

> Facts in this section track [Claude Code's model configuration docs](https://code.claude.com/docs/en/model-config).
> Level names, defaults, and variables change between releases — verify there before relying on a specific one.

Current Claude models use **adaptive reasoning**: no fixed thinking budget is reserved up front.
The model decides, at each step, whether to think and how much, based on task complexity. The
primary control over how much thinking happens is therefore the **effort level**, not a token cap.

### Effort level (the primary control)

| Level | When to use it |
|-------|----------------|
| `low` | Short, scoped, latency-sensitive tasks that are not intelligence-sensitive |
| `medium` | Cost-sensitive work that can trade off some intelligence |
| `high` | **The default on every model except Opus 4.7.** Balances token usage and intelligence |
| `xhigh` | Deeper reasoning at higher token spend. **The default on Opus 4.7** |
| `max` | Can improve performance on demanding tasks, but may show diminishing returns and is prone to overthinking — test before adopting broadly |

Supported levels vary by model: Fable 5, Opus 5, Sonnet 5, Opus 4.8, and Opus 4.7 support all five;
Opus 4.6 and Sonnet 4.6 have no `xhigh`. Setting a level the active model does not support falls
back to the highest supported level at or below it. **The scale is calibrated per model** — the same
level name does not represent the same underlying value across models.

How to set it, highest precedence first: the `CLAUDE_CODE_EFFORT_LEVEL` environment variable, then
the `effortLevel` settings field, then the model default. Per-session: `/effort`, the `/model`
effort slider, or the `--effort` launch flag. The `effort` frontmatter field on a skill or subagent
overrides the session level while that skill or subagent is active, but not the environment variable.
The `effortLevel` settings field accepts only `low`, `medium`, `high`, and `xhigh` — `max` and
`ultracode` are session-only.

To go deeper for a single turn, put `ultrathink` anywhere in the prompt: this adds an in-context
instruction and leaves the effort level sent to the API unchanged. Phrases like `think hard` and
`think more` are **not** keywords — they pass through as ordinary prompt text.

Within a given effort level you can also just ask: say in the prompt or in `CLAUDE.md` that
Claude should think more or less often than the current level produces, and the model responds to
that guidance within its effort setting.

### Turning thinking on and off

- **Session toggle**: Option+T (macOS) / Alt+T (Windows/Linux)
- **Global default**: the thinking toggle in `/config`, stored as `alwaysThinkingEnabled` in `~/.claude/settings.json`
- **Disable regardless of effort**: `MAX_THINKING_TOKENS=0`
- **Display**: Ctrl+O toggles verbose mode

Values other than `0` for `MAX_THINKING_TOKENS` apply **only to a fixed thinking budget**, so on a
model using adaptive reasoning, setting it to something like `10000` does nothing at all. This is
easy to mistake for a cap that is in force, so to reduce thinking, lower the effort level instead.
The one exception is Opus 4.6 and Sonnet 4.6, where `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`
reverts to the older fixed-budget mode and makes `MAX_THINKING_TOKENS` effective again. Fable 5,
Sonnet 5, and Opus 4.7 and later always use adaptive reasoning, so neither the fixed-budget mode
nor that variable applies to them. On Fable 5 thinking cannot be turned off at all: the session
toggle, `alwaysThinkingEnabled`, and `MAX_THINKING_TOKENS=0` all have no effect there.

### What thinking actually costs (measured)

Measured over 30 sessions / 1,667 assistant turns. Method: `usage` fields summed from the session
transcripts. The split within `output` is a **residual estimate** — tool-call and prose tokens are
estimated from character counts and the remainder is attributed to thinking. Only three
content-block types occur in the sample (thinking, tool_use, text), so nothing else is hiding in
that residual. The weighting is Opus rate ratios used as a reference for *where* spend goes, not
an actual bill.

- Billing-weighted (base input = 1): `cache_read` ~70%, `output` ~19%, `cache_creation` ~11%
- Within that `output` share, holding across a wide swing of character-to-token assumptions:
  **thinking 86-92%**, tool-call arguments ~8-9%, **visible response prose 1.9-3.2%**

Two consequences. First, instructing shorter responses saves under 1% of total spend, and that
figure already includes the re-reads a response causes by sitting in context for the rest of the
session. To actually reduce cost, look at the effort level and at context size — the latter is what
`cache_read` measures. Second, **you are billed for every thinking token generated, even when it is
collapsed or redacted.** Transcripts store only a short summary of each thinking block, so most
output tokens leave no trace in the session record. The expensive part is the part you cannot see.

For complex tasks requiring deep reasoning:
1. Raise the effort level for the session rather than relying on prompt phrasing
2. Enable **Plan Mode** for structured approach
3. Use multiple critique rounds for thorough analysis
4. Use split role sub-agents for diverse perspectives

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix
