---
description: Import a cctrace session export into Claude Code
---

Import a session from a cctrace export directory. This allows resuming sessions that were exported from another environment.

## Usage

```
/import-session <export-path>
```

Where `<export-path>` is the path to a `.claude-sessions/<name>/` directory.

## What This Does

1. Validates the export has a valid `.cctrace-manifest.json`
2. Creates a pre-import snapshot for recovery
3. Generates a new session ID (avoids conflicts)
4. Imports the session file to `~/.claude/projects/<normalized-path>/`
5. Imports auxiliary files (file-history, todos, plan)
6. Imports config files (commands, skills, hooks, agents, rules)
7. Adds import context note to CLAUDE.md

## Examples

Import a session from the current repo:
```
/import-session .claude-sessions/my-session/
```

Import from a cloned repo:
```
/import-session ../other-project/.claude-sessions/exported/
```

## After Import

Continue the session with:
```
claude -c
```

If something goes wrong, restore with:
```
/restore-backup
```

## Implementation

Run the import tool:
```bash
python3 import_session.py "$ARGUMENTS" --non-interactive
```

If no arguments provided, list available exports:
```bash
ls -la .claude-sessions/ 2>/dev/null || echo "No .claude-sessions/ directory found"
```
