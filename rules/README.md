# Rules
## Structure

Rules are organized into a **common** layer plus **language-specific** and **domain-specific** directories:

```
rules/
├── common/          # Language-agnostic principles (always loaded)
│   ├── coding-style.md
│   ├── git-workflow.md
│   ├── testing.md
│   ├── performance.md
│   ├── patterns.md
│   ├── hooks.md
│   ├── agents.md
│   ├── security.md
│   ├── code-review.md
│   └── development-workflow.md
├── typescript/      # TypeScript/JavaScript specific
├── python/          # Python specific
├── golang/          # Go specific
├── web/             # Web and frontend specific (always loaded)
├── swift/           # Swift specific
└── php/             # PHP specific
```

- **common/** (10 files) contains universal principles — no language-specific code examples. **Always loaded at launch**, same priority as `.claude/CLAUDE.md`.
- **web/** (7 files) contains domain-specific guidance for frontend and web projects. **Always loaded**.
- **Language directories** (typescript, python, golang, swift, php) extend common rules with framework-specific patterns, tools, and code examples. Each file references its common counterpart.
- **Conditional loading via `paths` frontmatter**: Language-specific files declare glob patterns in frontmatter (e.g., `paths: ["**/*.py"]`). Files are loaded only when the glob matches files in the current project. See [Claude docs: Memory](https://code.claude.com/docs/en/memory).

## Installation

### Install All Rules (Default)

All 79 rules are installed and conditionally loaded via `paths` frontmatter. Rule files without `paths` frontmatter (common/, web/, README.md) are always loaded. Language-specific files load only when their glob patterns match files in your project.

```bash
# Install to project directory (.claude/rules/)
./install.sh --scope project

# Or install to user home (~/.claude/rules/)
./install.sh --scope user
```

### How Conditional Loading Works

1. **Always loaded** (12 files):
   - `common/` (11 files: coding-style.md, git-workflow.md, karpathy-guidelines.md, etc.)
   - This README
   - Loaded at launch alongside `CLAUDE.md`

2. **Conditionally loaded** (67 files):
   - `web/` (7 files) — loads when frontend files match (`**/*.tsx`, `**/*.css`, `**/*.vue`, etc.)
   - Language rules (60 files across 12 languages: cpp, csharp, dart, golang, java, kotlin, perl, php, python, rust, swift, typescript)
   - Each file declares `paths: ["**/*.ext"]` frontmatter (e.g., `paths: ["**/*.ts", "**/*.tsx"]` for TypeScript)
   - Loaded only when glob matches project files
   - No setup required — matching happens automatically

## Rules vs Skills

- **Rules** define standards, conventions, and checklists that apply broadly (e.g., "80% test coverage", "no hardcoded secrets").
- **Skills** (`skills/` directory) provide deep, actionable reference material for specific tasks (e.g., `python-patterns`, `golang-testing`).

Language-specific rule files reference relevant skills where appropriate. Rules tell you *what* to do; skills tell you *how* to do it.

## Adding a New Language

To add support for a new language (e.g., `rust/`):

1. Create a `rules/rust/` directory
2. Add files that extend the common rules:
   - `coding-style.md` — formatting tools, idioms, error handling patterns
   - `testing.md` — test framework, coverage tools, test organization
   - `patterns.md` — language-specific design patterns
   - `hooks.md` — PostToolUse hooks for formatters, linters, type checkers
   - `security.md` — secret management, security scanning tools
3. Each file should start with:
   ```
   > This file extends [common/xxx.md](../common/xxx.md) with <Language> specific content.
   ```
4. Reference existing skills if available, or create new ones under `skills/`.

For non-language domains like `web/`, follow the same layered pattern when there is enough reusable domain-specific guidance to justify a standalone ruleset.

## Rule Priority

When language-specific rules and common rules conflict, **language-specific rules take precedence** (specific overrides general). This follows the standard layered configuration pattern (similar to CSS specificity or `.gitignore` precedence).

- `rules/common/` defines universal defaults applicable to all projects.
- `rules/golang/`, `rules/python/`, `rules/swift/`, `rules/php/`, `rules/typescript/`, etc. override those defaults where language idioms differ.

### Example

`common/coding-style.md` recommends immutability as a default principle. A language-specific `golang/coding-style.md` can override this:

> Idiomatic Go uses pointer receivers for struct mutation — see [common/coding-style.md](../common/coding-style.md) for the general principle, but Go-idiomatic mutation is preferred here.

### Common rules with override notes

Rules in `rules/common/` that may be overridden by language-specific files are marked with:

> **Language note**: This rule may be overridden by language-specific rules for languages where this pattern is not idiomatic.
