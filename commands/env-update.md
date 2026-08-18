---
description: "Update coding-env to latest version — fetch repo, pull changes, and reinstall"
---

# Environment Update

> Maintains coding-env in sync with repo changes. Reads install manifest, checks for updates, and reinstalls automatically. Confirmation is reserved for genuinely ambiguous or destructive situations (diverged branches, a file that looks like a deliberate local customization) — routine pull/reinstall/hub-restart steps proceed without asking.

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

### Check installed manifest freshness

```bash
git -C "$repo_path" rev-parse HEAD
```

Compare this HEAD against the `installed_from_commit` field of the manifest read in Phase 1:

- No manifest was found (interactive fallback path), the `installed_from_commit` field is missing, or its value is `"unknown"` → treat the install as **stale**
- `installed_from_commit` != current HEAD → **stale**
- `installed_from_commit` == current HEAD → **fresh**

### Detect changes

```bash
git log --oneline 'HEAD..@{u}'   # commits in remote not in local
git log --oneline '@{u}..HEAD'   # commits in local not in remote (divergence)
```

If local has commits not in remote AND remote has commits not in local → **ERROR**: "Branches have diverged. Manual resolution required."

If no new commits in upstream AND the install is fresh → **INFO**: "Already up to date. No changes." → exit 0

If no new commits in upstream but the install is stale:

```
[INFO] Repo is up to date, but the installed files are from an older commit.
[INFO] Repo HEAD:      <repo HEAD, short hash>
[INFO] Installed from: <installed_from_commit, short hash (or "unknown")>
[INFO] Reinstalling...
```

Skip Phase 3 (there is nothing to pull) and continue directly to Phase 4. No confirmation — reinstalling from an already-fetched, non-diverged repo only touches managed files and is caught by Phase 4's own conflict check if anything unexpected is in the way.

If new commits exist:

```
[INFO] Remote has N new commits:
  <log output here>
[INFO] Updating...
```

Continue to Phase 3. No confirmation — `git pull --ff-only` cannot lose local work; it fails closed on any conflict (handled in Phase 3), never silently merges or rewrites history.

---

## Phase 3 — PULL

**Goal**: Fast-forward merge.

If Phase 2 triggered a reinstall because only the installed files were stale (no new upstream commits), skip this phase — there is nothing to pull — and go directly to Phase 4.

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
```

install.sh's own stderr already lists which managed files differ (and for small diffs, the actual
diff content). Read that list and judge each flagged file:

- **Looks like plain staleness** (the local copy is just an older/edited version of the same
  distributed content — typos fixed, formatting drift, a stale version of the same section) →
  this is the common case. No confirmation needed.
- **Looks like a deliberate local customization** (project-specific additions with no upstream
  counterpart, content clearly written for this machine/user rather than copied from the repo) →
  flag it by name and ask about that specific file before overwriting it. Don't let one such file
  block the rest of the batch — proceed with `--force` for everything else and call out the held-back
  file separately.

In the common case (no held-back files), rerun immediately:
```bash
cd "$target_base_dir"
"$repo_path/install.sh" --scope project --force
```

If exit 0 → continue to Phase 5.  
If exit 1 again → **ERROR**: "Force reinstall failed. Resolve manually." → exit 1

`install.sh --force` backs up `CLAUDE.md` to a timestamped `.bak-<timestamp>` before overwriting
(see `backup_existing_claude_md` in install.sh) — this is the safety net for the common case, not a
reason to ask first.

### For user scope

```bash
"$repo_path/install.sh" --scope user
```

Same conflict handling as above.

---

## Phase 4b — HUB REINSTALL (conditional)

**Goal**: Keep the independently-installed hub (if present) in sync with the repo, without ever
starting a server the user didn't already have running. Hub is installed separately from
coding-env (`hub/install.sh`), so this phase only acts when it detects an existing installation.

### Detect

```bash
test -f "$repo_path/hub/bin/hub.py" && test -f "$HOME/.claude/hub/bin/hub.py"
```

Actually check the **installed target** (`~/.claude/hub/bin/hub.py`), not the repo copy:

```bash
test -f "$HOME/.claude/hub/bin/hub.py"
```

If not found:
```
[INFO] Hub is not installed. Skipping.
```
Continue to Phase 5. **Do not create anything.**

### If found

1. Check server status:
   ```bash
   python3 "$HOME/.claude/hub/bin/hub.py" server-status --json
   ```
   Read the `alive` field.

2. If `alive == true`, stop it — no confirmation needed, this is the expected end-to-end update:
   ```
   [INFO] Hub server is running. Stopping, updating, and restarting...
   ```
   `python3 "$HOME/.claude/hub/bin/hub.py" server-stop --json`, remember that the server was
   running (`was_running_before_update=true`). Stopping and restarting the hub server is safe —
   it's a local process with no in-flight user data to lose, and step 4 restores it automatically.

   If `alive == false`, continue directly (nothing to stop).

3. Reinstall:
   ```bash
   "$repo_path/hub/install.sh"
   ```
   - exit 0 → continue to step 4.
   - exit 1 (modified-files conflict): apply the same judgment as Phase 4's conflict handling
     (plain staleness → auto `--force`; a file that looks like a deliberate local customization →
     hold that file back and ask about it specifically). Rerun `"$repo_path/hub/install.sh" --force`
     once the call is made.

4. If the server was running before this phase started (`was_running_before_update=true`):
   ```bash
   python3 "$HOME/.claude/hub/bin/hub.py" server-start --json
   ```
   This restores the state the server was actually in before this phase touched it — it is not a
   fresh, unprompted start. A server that was off before `/env-update` stays off.

5. Hooks are never touched here. If the hook command string ever changes, `install-hooks` is
   idempotent, so just note:
   ```
   [INFO] If needed, run /hub install again to refresh the installed hook command.
   ```

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
| Already up to date (repo and install both fresh) | INFO: stop, exit 0 |
| Repo up to date but install stale | INFO: reinstall automatically, skip Phase 3, proceed to Phase 4 |
| Pull fails | ERROR: stop |
| install.sh conflict | WARN: auto `--force`, unless a file looks like a deliberate local customization (then ask about that file only) |
| install.sh force fails | ERROR: stop |
| Hub not installed | INFO: skip Phase 4b, no error |
| Hub server running | INFO: stop, reinstall, restart automatically — no confirmation |
| Manifest verification fails | WARN: report mismatch but exit 0 |

---

## Notes

- **Manifest is runtime metadata**: Not part of the deployed files, so it's never backed up or version-controlled.
- **User modifications**: If local rules/agents/commands are modified, install.sh requires `--force` to overwrite — env-update supplies `--force` automatically for plain staleness, and only stops to ask when a diff looks like a deliberate local customization rather than drift (see Phase 4).
- **Dirty repo is OK**: Minor uncommitted changes won't block the update. Major conflicts will be caught by install.sh.
- **Why the manifest freshness check exists**: Contributors who commit directly in this repo are always at or ahead of `@{u}`, so `git log HEAD..@{u}` is permanently empty for them. Without comparing `installed_from_commit` to repo HEAD, Phase 4's reinstall would never run for that workflow, and the installed files would silently drift out of date.
