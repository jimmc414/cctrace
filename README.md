# cctrace

Export and import Claude Code sessions.

Claude Code stores conversation history in `~/.claude/projects/<normalized-path>/*.jsonl`. This tool extracts those sessions into portable formats for archival, analysis, or sharing.

## What's New

**v2.0** adds portable sessions: export a session to your git repository, push it, and let someone else import it to continue where you left off. The original export functionality remains unchanged.

## Two Modes of Operation

### Classic Export

Exports to `~/claude_sessions/exports/` with timestamped directories. This is the original behavior and remains the default.

```bash
python3 export_claude_session.py
```

Produces:
```
~/claude_sessions/exports/2025-07-02_16-45-00_f33cdb42/
├── raw_messages.jsonl     # Original session data
├── conversation_full.md   # Human-readable markdown
├── conversation_full.xml  # Structured XML with full metadata
├── session_info.json      # Session metadata
└── summary.txt            # Statistics
```

### Portable Export

Exports to `.claude-sessions/<name>/` within your repository. Designed to be committed and shared.

```bash
python3 export_claude_session.py --in-repo --export-name my-session
```

Produces:
```
.claude-sessions/my-session/
├── .cctrace-manifest.json    # Required for import
├── RENDERED.md               # Renders on GitHub
├── session/
│   ├── main.jsonl            # Session transcript
│   ├── file-history/         # File snapshots from undo history
│   ├── todos.json            # Todo state
│   └── plan.md               # Plan file if present
├── config/
│   ├── commands/             # Slash commands
│   ├── skills/               # Skills
│   └── ...                   # Other .claude/ config
└── [legacy files]            # For backwards compatibility
```

The portable export includes everything needed to resume the session: conversation history, file snapshots, todos, plans, and project-specific Claude Code configuration.

## Importing a Session

Someone clones your repo and wants to continue your session:

```bash
python3 import_session.py .claude-sessions/my-session/
claude -c  # Lists available sessions, including the imported one
```

### What Import Does

1. Validates the export has a `.cctrace-manifest.json`
2. Creates a pre-import snapshot for recovery
3. Generates a new session ID (your local sessions remain unaffected)
4. Rewrites internal UUIDs while preserving message threading
5. Updates `cwd` paths to the local project directory
6. Copies session file to `~/.claude/projects/<normalized-path>/`
7. Imports auxiliary data (file-history, todos, plans)
8. Imports config files (commands, skills, hooks, agents, rules)

### What Import Preserves

Certain fields are cryptographically signed or tied to Anthropic's API and must not be modified:

- `message.id` (Anthropic message ID)
- `requestId` (Anthropic request ID)
- `signature` in thinking blocks
- `tool_use.id` (tool invocation ID)

These are left untouched. Only the session-local identifiers (`sessionId`, `uuid`, `parentUuid`, `agentId`, `cwd`) are regenerated.

### Restoring After Import

If an import causes problems:

```bash
python3 restore_backup.py           # Show snapshot info
python3 restore_backup.py --restore # Restore pre-import state
```

Restore requires typing "RESTORE" to confirm. The `--yes` flag bypasses this for automation.

## Path Normalization

Claude Code normalizes project paths for storage:

| Character | Replacement |
|-----------|-------------|
| `/` | `-` |
| `\` | `-` |
| `:` | `-` |
| `.` | `-` |
| `_` | `-` |

Unix paths are prefixed with `-`. Windows paths are not.

Examples:
- `/mnt/c/python/my_project` becomes `-mnt-c-python-my-project`
- `C:\Users\dev\project` becomes `C-Users-dev-project`

cctrace replicates this normalization to locate and import sessions correctly.

## Backwards Compatibility

Existing cctrace users are unaffected:

- The default export behavior is unchanged
- All original output files are still generated
- Portable exports include the legacy files alongside the new structure
- The `--in-repo` flag is required to use the new portable format

## Installation

Requires Python 3.6+ and access to `~/.claude/projects/`.

```bash
git clone https://github.com/jimmc414/cctrace.git
cd cctrace
./setup.sh
```

Or manually:

```bash
cp export_claude_session.py ~/claude_sessions/
cp import_session.py ~/claude_sessions/
cp restore_backup.py ~/claude_sessions/
mkdir -p ~/.claude/commands
cp .claude/commands/*.md ~/.claude/commands/
```

## Usage

### Export

```bash
# Classic export to ~/claude_sessions/exports/
python3 export_claude_session.py

# Portable export to .claude-sessions/
python3 export_claude_session.py --in-repo --export-name feature-work

# Export specific session
python3 export_claude_session.py --session-id f33cdb42-0a41-40d4-91eb-c89c109af38a

# Adjust active session detection window (default: 300 seconds)
python3 export_claude_session.py --max-age 600
```

### Import

```bash
# Import from local export
python3 import_session.py .claude-sessions/my-session/

# Skip config file import
python3 import_session.py .claude-sessions/my-session/ --skip-config

# Skip auxiliary files (file-history, todos, plans)
python3 import_session.py .claude-sessions/my-session/ --skip-auxiliary

# Non-interactive mode
python3 import_session.py .claude-sessions/my-session/ --non-interactive
```

### Slash Commands

If installed to `~/.claude/commands/`:

```
/export-session [name]    # Portable export
/import-session <path>    # Import
/restore-backup           # Restore from snapshot
```

## Session Detection

When multiple sessions exist for a project, cctrace identifies the correct one by:

1. Finding all `.jsonl` files in the project's Claude storage directory
2. Filtering to sessions modified within `--max-age` seconds
3. If running inside Claude Code, correlating the parent PID with session activity
4. Falling back to the most recently modified session

## Output Formats

### JSONL (raw_messages.jsonl, session/main.jsonl)

The original session format. Each line is a JSON object representing a message or event. Contains all fields exactly as stored by Claude Code.

### Markdown (conversation_full.md, RENDERED.md)

Human-readable conversation with:
- Timestamps per message
- User and assistant messages clearly delineated
- Thinking blocks in collapsible `<details>` sections
- Tool uses with JSON inputs and results

RENDERED.md includes a header with session metadata and is formatted for GitHub rendering.

### XML (conversation_full.xml)

Structured format preserving:
- Message hierarchy via UUID/parent-UUID relationships
- Token usage per message
- Tool execution metadata (response codes, duration)
- Thinking block signatures

### Manifest (.cctrace-manifest.json)

Required for import. Contains:
- cctrace version
- Original session ID and slug
- Export timestamp
- Original environment context (user, platform, paths)
- Inventory of exported files

## File Locations

| Path | Purpose |
|------|---------|
| `~/.claude/projects/<path>/` | Claude Code session storage |
| `~/claude_sessions/exports/` | Classic export destination |
| `.claude-sessions/` | Portable export destination (in repo) |
| `~/.claude-session-imports/` | Import logs and snapshots |
| `~/.claude/commands/` | User slash commands |

## Limitations

- Sessions are one-way portable: you can export and import, but there's no merge or sync
- File-history snapshots reference files by content hash; the original paths are not preserved
- Import generates new UUIDs, so the imported session is a copy, not the original
- Large sessions (500+ messages) produce large RENDERED.md files that may be slow to render on GitHub

## Tests

```bash
python3 -m pytest tests/ -v
```

33 tests covering manifest validation, UUID regeneration, path normalization, and restore functionality.

## License

MIT
