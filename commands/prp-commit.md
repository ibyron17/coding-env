---
description: "Quick commit with natural language file targeting — describe what to commit in plain English"
argument-hint: "[target description] (blank = all changes)"
---

# Smart Commit

> Adapted from PRPs-agentic-eng by Wirasm. Part of the PRP workflow series.

**Input**: $ARGUMENTS

---

## Phase 1 — ASSESS

```bash
git status --short
```

If output is empty → stop: "Nothing to commit."

Show the user a summary of what's changed (added, modified, deleted, untracked).

---

## Phase 2 — INTERPRET & STAGE

Interpret `$ARGUMENTS` to determine what to stage:

| Input | Interpretation | Git Command |
|---|---|---|
| *(blank / empty)* | Stage everything | `git add -A` |
| `staged` | Use whatever is already staged | *(no git add)* |
| `*.ts` or `*.py` etc. | Stage matching glob | `git add '*.ts'` |
| `except tests` | Stage all, then unstage tests | `git add -A && git reset -- '**/*.test.*' '**/*.spec.*' '**/test_*' 2>/dev/null \|\| true` |
| `only new files` | Stage untracked files only | `git ls-files --others --exclude-standard \| grep . && git ls-files --others --exclude-standard \| xargs git add` |
| `the auth changes` | Interpret from status/diff — find auth-related files | `git add <matched files>` |
| Specific filenames | Stage those files | `git add <files>` |

For natural language inputs (like "the auth changes"), cross-reference the `git status` output and `git diff` to identify relevant files. Show the user which files you're staging and why.

```bash
git add <determined files>
```

After staging, verify:
```bash
git diff --cached --stat
```

If nothing staged, stop: "No files matched your description."

---

## Phase 3 — COMMIT

### Resolve the commit convention (priority order)

1. **Project CLAUDE.md** — if the project's CLAUDE.md defines a commit convention
   (커밋 컨벤션 / commit format section), follow it.
2. **Commitlint config** — if any of these files exist, read it and comply with its rules:
   - `.commitlintrc` / `.commitlintrc.{json,yaml,yml,js,cjs,mjs,ts,cts,mts}`
   - `commitlint.config.{js,cjs,mjs,ts,cts,mts}`
   - `commitlint` field in `package.json`

   When the config `extends` a preset (e.g. `@commitlint/config-conventional`), apply the
   preset's rules plus any local overrides. A commit-msg hook may reject non-conforming
   messages, so treat these rules as hard constraints.
3. **Default format** — if neither exists, use the default format below.

If both 1 and 2 exist, satisfy the commitlint rules first (they are tool-enforced),
and apply CLAUDE.md guidance for anything commitlint does not constrain.

### Default format

Craft a single-line commit message in imperative mood:

```
{type}: {description}
```

Types:
- `feat` — New feature or capability
- `fix` — Bug fix
- `refactor` — Code restructuring without behavior change
- `docs` — Documentation changes
- `test` — Adding or updating tests
- `chore` — Build, config, dependencies
- `perf` — Performance improvement
- `ci` — CI/CD changes

Rules:
- Imperative mood ("add feature" not "added feature")
- Lowercase after the type prefix
- No period at the end
- Under 72 characters
- Describe WHAT changed, not HOW

```bash
git commit -m "<message following the resolved convention>"
```

---

## Phase 4 — OUTPUT

Report to user:

```
Committed: {hash_short}
Message:   {message}
Files:     {count} file(s) changed

Next steps:
  - git push           → push to remote
  - /prp-pr            → create a pull request
  - /code-review       → review before pushing
```

---

## Examples

| You say | What happens |
|---|---|
| `/prp-commit` | Stages all, auto-generates message |
| `/prp-commit staged` | Commits only what's already staged |
| `/prp-commit *.ts` | Stages all TypeScript files, commits |
| `/prp-commit except tests` | Stages everything except test files |
| `/prp-commit the database migration` | Finds DB migration files from status, stages them |
| `/prp-commit only new files` | Stages untracked files only |
