# Performance Optimization

## Model Selection Strategy

> Guidance here follows [Choosing a Claude model and effort level](https://claude.com/blog/claude-model-and-effort-level-in-claude-code);
> alias and effort-support specifics come from the [model configuration docs](https://code.claude.com/docs/en/model-config).
> Families and their relative strengths shift between releases — the shape of the decision is the durable part, not the names.

Model choice and effort level (see below) are two independent dials. **Model is the capability axis;
effort is the thoroughness axis.** When Claude gets something wrong, diagnose which one was missing
before reaching for either:

- **It lacked knowledge** — a subtle bug, an unfamiliar domain, an architecture decision → pick a **larger model**
- **It lacked diligence** — skipped a file, did not run the tests, did not double-check its work → raise the **effort level** on the same model

Pick a smaller model when the work is routine: edits you can describe precisely, mechanical changes,
questions about code already in context. Pick a larger model when the problem is genuinely hard.
Roughly, Sonnet is a strong generalist and Opus is the expert. Fable is the specialist: on long,
multi-step work it pulls furthest ahead, finishing jobs that Opus and Sonnet do not reach **at any
effort level** — the sharpest illustration that raising effort cannot substitute for the right model.

Treat both dials as a standing preference for the kind of work you do, not a decision to relitigate
per task. For effort in particular, the published guidance is to use the model's default level for
most tasks and deviate only when you have a reason.

Two things to know before planning around a model:

- **Effort is not available on every model.** The **Effort level** section below lists which models
  take which levels. Haiku is absent from Anthropic's support table entirely — **it has no effort
  levels at all** — so on Haiku the model is the only dial you have, and none of the cost tuning
  below applies.
- **Prefer family aliases** (`opus`, `sonnet`, `haiku`, `fable`) over pinned versions in agent
  frontmatter and settings: an alias points to the recommended version for your provider and updates
  over time, so it does not go stale the way a pinned name does. The caveat is that the recommended
  version can lag the newest release — name the full model when you specifically need a newer one.

Per-stage model assignment for a project's own workflow — which agent runs on which model — belongs
in that project's `CLAUDE.md`, not here. Where `CLAUDE.md` defines it, that is the single source of
truth; this section only covers how to reason about the choice.

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
