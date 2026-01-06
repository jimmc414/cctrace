---
description: Export current Claude Code session for sharing or backup
---

Export the current session to a portable format that can be shared via Git or imported into another environment.

## Usage

```
/export-session [name]
```

Where `[name]` is an optional export name (defaults to session slug).

## What This Does

1. Finds the current session in `~/.claude/projects/<normalized-path>/`
2. Creates `.claude-sessions/<name>/` with:
   - `session/main.jsonl` - The full session transcript
   - `session/file-history/` - File snapshots from the session
   - `config/` - Commands, skills, hooks, agents, rules
   - `.cctrace-manifest.json` - Metadata for import
   - `RENDERED.md` - Human-readable session for GitHub
   - Legacy files for backwards compatibility

## Examples

Export with auto-generated name:
```
/export-session
```

Export with custom name:
```
/export-session my-feature-session
```

## After Export

The export will be in `.claude-sessions/<name>/`. You can:
- Commit and push to share via GitHub
- Copy to another machine
- Import with `/import-session`

## Implementation

Run the export tool:
```bash
python3 export_claude_session.py --in-repo --export-name "$ARGUMENTS" --max-age 86400
```

If no arguments, use default name:
```bash
python3 export_claude_session.py --in-repo --max-age 86400
```
