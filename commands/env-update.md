---
description: "Update coding-env to latest version — fetch repo, pull changes, and reinstall"
---

# Environment Update

> Maintains coding-env in sync with repo changes. Reads install manifest, checks for updates, and reinstalls with user confirmation.

**Automated Phases**: find → fetch → pull → reinstall → verify

---

## Phase 1 — FIND MANIFEST

**Goal**: Locate install manifest to discover repo path and scope.

1. Check for `.claude/.coding-env.json` in `$PWD` (project scope)
2. If not found, check `~/.claude/.coding-env.json` (user scope)
3. If neither exists → **Fallback**: Ask user for repo path interactively

### Manifest Validation

When found, verify:
- `version` == 1
- `repo_path` exists and is a directory
- `scope` ∈ { "project", "user" }

If validation fails, report the error and stop.

### Fallback: Interactive Input (No Manifest)

```
[INFO] Install manifest not found.
[INFO] Enter the coding-env repo path (or 'skip' to abort):
> /path/to/coding-env
```

If user enters a valid path → continue with Phase 2 (but don't create manifest).  
If user enters 'skip' or Ctrl+C → stop without error.

---

## Phase 2 — FETCH & DETECT

**Goal**: Check for upstream changes.

```bash
cd "$repo_path"
```

### Check repo status

```bash
git status
```

If not a git repository → **ERROR**: "Not a git repository: $repo_path"

Log status (dirty/detached state is OK, just warn):
- Dirty: `[WARN] Working tree has uncommitted changes. Continuing...`
- Detached HEAD: `[WARN] Repository is in detached HEAD state. Continuing...`

### Verify upstream

```bash
git rev-parse --abbrev-ref '@{u}'
```

If command fails (no tracking branch set) → **ERROR**: "Tracking branch not set. Run: git branch --set-upstream-to=origin/main" → stop.

### Fetch origin

```bash
git fetch origin
```

If fails → **ERROR**: "Failed to fetch from origin"

### Detect changes

```bash
git log --oneline 'HEAD..@{u}'   # commits in remote not in local
git log --oneline '@{u}..HEAD'   # commits in local not in remote (divergence)
```

If local has commits not in remote AND remote has commits not in local → **ERROR**: "Branches have diverged. Manual resolution required."

If no new commits in upstream → **INFO**: "Already up to date. No changes." → exit 0

If new commits exist:

```
[INFO] Remote has N new commits:
  <log output here>
[INFO] Proceed with update? (y/n)
```

Wait for user input.  
If `y` → continue to Phase 3.  
If `n` or other → stop, no error.

---

## Phase 3 — PULL

**Goal**: Fast-forward merge.

```bash
git pull --ff-only
```

If fails (merge conflict) → **ERROR**: "Pull failed with conflicts. Please resolve manually and run env-update again."

Report: `[OK] Merged N commits`

---

## Phase 4 — REINSTALL

**Goal**: Run install.sh in the correct context.

### For project scope

**IMPORTANT**: The install.sh --scope project must run from the target project directory.

```bash
cd "$target_base_dir"
"$repo_path/install.sh" --scope project
```

If exit 0 → continue to Phase 5.

If exit 1 (diff conflict reported by install.sh):

```
[WARN] Install reported conflicts in modified files.
[INFO] Use --force to overwrite? (y/n)
```

If `y` → rerun:
```bash
cd "$target_base_dir"
"$repo_path/install.sh" --scope project --force
```

If exit 0 → continue to Phase 5.  
If exit 1 again → **ERROR**: "Force reinstall failed. Resolve manually." → exit 1

If `n` → stop without error.

### For user scope

```bash
"$repo_path/install.sh" --scope user
```

Same conflict handling as above.

---

## Phase 5 — VERIFY MANIFEST

**Goal**: Confirm installation succeeded.

The install.sh script automatically updates the manifest's `installed_from_commit` when successful.

Verify:
```bash
cat "$manifest_path" | grep -q "installed_from_commit"
```

Extract current HEAD:
```bash
git -C "$repo_path" rev-parse HEAD
```

If `installed_from_commit` in manifest equals current HEAD → **OK**: Installation verified.

Report:
```
[OK] Update complete
[OK] Manifest updated: installed_from_commit = <hash>
```

If mismatch → **WARN**: "Manifest commit mismatch. Manifest may not have been updated."

Exit 0.

---

## Error Handling Summary

| Condition | Action |
|-----------|--------|
| Manifest not found | Fallback: ask user for repo path |
| Not a git repo | ERROR: stop |
| No tracking branch | ERROR: stop with `git branch --set-upstream-to` hint |
| Fetch fails | ERROR: stop |
| Branches diverged | ERROR: stop |
| Already up to date | INFO: stop, exit 0 |
| Pull fails | ERROR: stop |
| install.sh conflict | WARN: ask `--force?` |
| install.sh force fails | ERROR: stop |
| Manifest verification fails | WARN: report mismatch but exit 0 |

---

## Notes

- **Manifest is runtime metadata**: Not part of the deployed files, so it's never backed up or version-controlled.
- **User modifications preserved**: If local rules/agents are modified, install.sh will require `--force` to overwrite. User must decide.
- **Dirty repo is OK**: Minor uncommitted changes won't block the update. Major conflicts will be caught by install.sh.
