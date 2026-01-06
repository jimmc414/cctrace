# Objective: Portable, Resumable Claude Code Sessions

## Problem Statement

Claude Code conversations are currently trapped in local storage. A developer's session—including the conversation history, reasoning, tool usage, custom commands, project-specific configuration, and the resulting code—cannot be packaged and shared.

This limits:
- **Collaboration**: No way to hand off an in-progress session to a teammate
- **Observability**: No way to review the AI-assisted development process after the fact
- **Reproducibility**: No way to clone someone's working environment including their Claude Code setup
- **Archival**: Sessions are ephemeral and disconnected from the code they produced

## Desired Outcome

A complete Claude Code working session should be exportable as a self-contained package that includes:

1. **The conversation** — full message history with metadata
2. **The code** — all project files at their current state
3. **The environment** — Claude Code configuration (skills, hooks, agents, commands)
4. **The dependencies** — what needs to be installed for the session to work

This package should be:
- Committable to a git repository
- Visually readable when viewed on GitHub
- Importable by another user to continue the session

## Core Design Principles

### 1. Direct File Preservation

Session files are exported and imported **as-is**, without transformation:

```
Export: Copy session files directly into repo folder
Import: Copy files from repo folder back to expected locations
```

No parsing, consolidation, or reconstruction. The export folder mirrors whatever Claude Code actually uses. This prevents data loss and means the tool doesn't need deep knowledge of Claude Code's internal format.

### 2. No Programmatic Overwrites

The tool will never overwrite existing local data, even with a force flag. If a session ID already exists locally, import aborts and requires the user to either:
- Use `--new-session-id` to import as a separate session
- Manually delete the existing local session if they truly want to replace it

This eliminates an entire class of data loss bugs.

### 3. Git as the Transport Layer

The repository itself is the complete session state:

```
cctrace_myproject/                   # Repository name with required prefix
├── src/                             # Code files at session end state
├── .claude/                         # Commands, hooks, skills, agents
│   ├── commands/
│   ├── hooks/
│   ├── skills/
│   └── settings.json
├── .claude-sessions/                # Exported session data
│   └── auth-implementation/
│       ├── [raw session files]      # Direct copy from Claude Code storage
│       ├── RENDERED.md              # Generated view for GitHub (read-only)
│       └── .cctrace-manifest.json   # Validation manifest (required for import)
└── README.md
```

How files get to your machine (clone, pull, merge, cherry-pick) is standard git workflow. Our tool only handles the bridge between "files in repo" and "Claude Code's internal storage."

### 4. Interactive Over Flags

Where decisions are needed (path conversions, conflicts), the tool prompts the user in context rather than requiring memorization of flags. Batch operations ("convert all similar") speed up repetitive choices.

### 5. Discoverable Naming Convention

Exported repositories use a required prefix for GitHub discoverability:

```
cctrace_<user-provided-name>
```

Examples:
- `cctrace_auth-api`
- `cctrace_payment-system`
- `cctrace_ml-pipeline`

This enables:
- GitHub search for all exports: `cctrace_ in:name`
- Adoption tracking
- Easy identification of session exports vs regular repos

The prefix is required. Users can customize only the `<name>` portion. For technical users who absolutely need to remove it, the code is structured to make this a simple (but documented) modification — not a flag.

### 6. Manifest-Based Validation

Every export includes a `.cctrace-manifest.json` file that:
- Identifies the export as a valid cctrace session
- Contains original environment context (user, platform, paths)
- Stores metadata needed for import validation

Import will refuse to proceed without a valid manifest.

---

## What Gets Exported

### 1. Conversation Data
- Complete message history (user prompts, Claude responses)
- Thinking/reasoning blocks
- Tool invocations and their results (bash commands, file operations, etc.)
- Timestamps and turn metadata
- Token usage and model information
- Session ID and lineage

### 2. Project Files
- All source code files (respecting .gitignore)
- Configuration files
- Any files created or modified during the session
- File state at time of export

### 3. Claude Code Configuration

**Commands** (`.claude/commands/`)
- Custom slash commands defined for the project

**Hooks** (`.claude/hooks/` or equivalent)
- Pre/post execution hooks
- Custom integrations

**Agents** (if applicable)
- Custom agent configurations
- Agent-specific prompts or behaviors

**Skills** (`.claude/skills/` or equivalent)
- Project-specific skills
- Custom tool definitions

**Project Settings** (`.claude/settings.json`, `CLAUDE.md`, etc.)
- Project-level configuration
- Context files Claude was instructed to reference

### 4. Environment Metadata

A manifest capturing (for informational purposes):

**Claude Code version**
- Version that created the session
- Used to warn on version mismatch during import

**System dependencies observed:**
- Python version
- Node version
- Other runtime requirements detected

**Package dependencies:**
- Python packages (pip)
- Node packages (npm)
- System packages referenced

**MCP servers used:**
- Names of MCP servers invoked during session
- User is responsible for installing these

**Environment variables:**
- Excluded by default
- Optional flag to include (with user acknowledgment)

### 5. Export Manifest

Every export includes `.cctrace-manifest.json`:

```json
{
  "cctrace_version": "2.0",
  "export_timestamp": "2025-01-06T14:32:00Z",
  "original_repo_name": "cctrace_auth-api",
  "original_repo_path": "/home/alice/projects/auth-api",
  "original_user": "alice",
  "original_platform": "linux",
  "session_id": "f33cdb42-0a41-40d4-91eb-c89c109af38a",
  "session_folder_name": "auth-implementation",
  "claude_code_version": "1.2.3",
  "anonymized": false,
  "files_included": [
    "session.jsonl",
    "settings.json",
    "RENDERED.md"
  ]
}
```

This manifest:
- Validates the export is from cctrace (not a random directory)
- Provides context for the importing user (original environment info)
- Preserves metadata needed for import decisions
- Phase 2: File checksums can be added if integrity issues emerge in practice

---

## Export Workflow

### Initiation

```
/export-session
# or
python export_session.py
```

### Git Repository Check

If the current directory is not a git repository:

```
This directory is not a git repository.

Options:
(i) Initialize git repo now (runs git init)
(a) Abort export

Choice: _
```

### Repository Naming

If initializing a new repo or exporting for the first time:

```
Repository name: cctrace_____________
                 ^^^^^^^^ (required prefix)
                         ^^^^^^^^^^^^^ (you provide this part)

Enter name: auth-api

Repository will be named: cctrace_auth-api
```

The `cctrace_` prefix is required for discoverability. Users can only customize the portion after the prefix.

### .gitignore Handling

The export respects `.gitignore`. Before proceeding, show what's excluded:

```
Export summary:

Including:
  - src/ (14 files)
  - .claude/commands/ (3 files)  
  - .claude/hooks/ (2 files)
  - .claude-sessions/auth-impl/ (will be created)

Excluded by .gitignore:
  - .env
  - node_modules/ (1,247 files)
  - __pycache__/ (12 files)
  - .claude/secrets.json

Note: Excluded files will not be available on import.

Proceed with export? (y/n)
```

### Folder Naming

User provides a name for the export:

```
Session export name: auth-implementation
```

Creates: `.claude-sessions/auth-implementation/`

If name already exists:

```
Export folder 'auth-implementation' already exists.

Options:
(r) Rename this export: _____________
(a) Auto-rename to: auth-implementation-2
(o) Abort

Choice: _
```

### Authorship Options

```
Include authorship metadata?

(y) Yes - include username/machine info
(n) No - anonymize export
(Note: conversation content is not anonymized)

Choice: _
```

### Session Files Copy

Raw session files are copied directly from Claude Code's storage location into `.claude-sessions/<name>/`, preserving their original structure and naming.

### Manifest Generation

After files are copied, `.cctrace-manifest.json` is generated:
- Records all files included
- Captures original environment context (user, platform, paths)
- Captures export metadata (timestamp, versions)
- This file is required for import validation

### RENDERED.md Generation

A `RENDERED.md` file is generated for GitHub viewing. This is a one-way transformation for human readability — it is not used for import.

Contents:
- Session summary (duration, turns, files changed, model used)
- Claude Code version
- Dependency manifest
- Visual conversation rendering with:
  - Clear user/Claude distinction
  - Collapsible thinking blocks
  - Syntax-highlighted code
  - Tool invocations and results
  - Timestamps

### Export Complete

```
Export complete: .claude-sessions/auth-implementation/

Files created:
  - .claude-sessions/auth-implementation/[session files]
  - .claude-sessions/auth-implementation/RENDERED.md

Next steps:
  git add .claude-sessions/
  git commit -m "Export Claude Code session: auth-implementation"
  git push
```

---

## GitHub Viewing Experience

When viewing `.claude-sessions/<name>/RENDERED.md` on GitHub:

### Header Section
- Session title
- Export timestamp
- Author (if not anonymized)
- Claude Code version
- Model used
- Key metrics (turns, duration, tokens, files modified)

### Dependency Notice
- Required Claude Code version
- MCP servers used
- System dependencies detected
- Packages referenced

### Conversation View
- Clear visual distinction between User and Claude (using GitHub alert syntax or similar)
- Collapsible reasoning/thinking blocks
- Syntax-highlighted code blocks
- Tool invocations styled distinctly
- Tool results (stdout, stderr, success/failure indicators)
- Timestamps per turn

### Files Summary
- Files created/modified (linking to those files in repo)
- Commands executed
- Key decision points

---

## Import Workflow

### Initiation

After cloning/pulling a repo with an exported session:

```
/import-session .claude-sessions/auth-implementation
# or
python import_session.py .claude-sessions/auth-implementation
```

### Validation Phase

**0. Manifest check:**
```
Checking for valid cctrace export...

✗ No .cctrace-manifest.json found.
  This does not appear to be a valid cctrace export.
  
  Import aborted.
```

Or if manifest exists but is invalid:
```
Checking for valid cctrace export...

✗ Manifest validation failed:
  - Missing required field: claude_code_version
  
  The export may be corrupted or manually modified.
  Import aborted.
```

If valid:
```
Checking for valid cctrace export...

✓ Valid cctrace export (v2.0)
✓ Exported by: alice
✓ Original platform: linux
  
Proceeding with validation...
```

**1. Format validation:**
```
Validating session format...
  ✓ Required files present
  ✓ Structure valid
```

If validation fails, abort with specific error.

**2. Claude Code version check:**
```
Version check:
  Session created with: Claude Code 1.2.3
  Your version: Claude Code 1.3.0

⚠ Version mismatch detected.

Options:
(p) Proceed anyway (may have compatibility issues)
(a) Abort import

Choice: _
```

**3. Dependency report:**
```
Dependencies detected in session:

MCP servers:
  - github (used in turns 12-15)
  - postgres (used throughout)
  
Packages:
  - fastapi==0.104.1
  - pyjwt==2.8.0

These are not automatically installed.
Verify your environment has required dependencies.

Continue? (y/n)
```

### Session ID Handling

**Default behavior:** Generate new session ID

```
Importing as new session: [new-generated-id]
Original session ID preserved in metadata.
```

**If user specifies `--preserve-session-id`:**

```
Checking for session ID conflict...

Session ID abc123 already exists locally.

Import aborted. Options:
  - Use default import (generates new session ID)
  - Manually delete existing session at [path]
```

No programmatic overwrite is offered.

### Destination Conflict Check

Check if any files would be written to locations with existing files:

```
Checking destinations...

Conflict detected:
  ~/.claude/projects/-home-bob-myproject/xyz789.jsonl exists

Options:
(n) Import with new session ID (recommended)
(a) Abort

Choice: _
```

### Snapshot Creation

Before writing any files:

```
Taking snapshot...
  ✓ Pre-import snapshot saved

Proceeding with import...
```

The pre-import snapshot captures current session storage state. It is overwritten on each import, so only the most recent import can be reverted.

### Path Handling (Phase 1 Approach)

Paths are imported as-is without conversion. Instead of complex interactive path resolution, a CLAUDE.md note is added explaining the situation:

```
Importing session files...
  ✓ Wrote session.jsonl → ~/.claude/projects/.../
  ✓ Wrote settings.json → ~/.claude/projects/.../
  ✓ Added import context to CLAUDE.md
  
Import complete.
```

The CLAUDE.md note added to the project:

```markdown
## Imported Session Context

This session was imported via cctrace from another environment.

Original environment:
- User: alice
- Path: /home/alice/myproject/
- Platform: Linux
- Exported: 2025-01-06

Some paths in the conversation history may reference the original environment.
If you encounter path-related errors, files are likely in the current working
directory with adjusted paths for this environment.
```

Claude Code can then handle path mismatches in context — either fixing them when encountered or asking the user for guidance. This is more flexible than pre-import conversion.

**Phase 2 consideration:** If users frequently request interactive path conversion, it can be added later based on real-world feedback.

### Import Execution

```
Importing session files...
  ✓ Wrote session.jsonl → ~/.claude/projects/.../
  ✓ Wrote settings.json → ~/.claude/projects/.../
  
Import complete.

Session ready: auth-implementation
To continue: start Claude Code in this directory

Import log: ~/.claude-session-imports/2025-01-06-143022/import.log
If problems occur: /restore-backup
```

### Import Logging

Every import creates a log:

```
~/.claude-session-imports/
└── 2025-01-06-143022/
    └── import.log          # Detailed log of all actions taken
```

---

## Backup and Restore

Import operations could potentially affect Claude Code session storage in unexpected ways. To protect against this, a pre-import snapshot is taken before each import.

### Storage Structure

```
~/.claude-session-imports/
├── index.json                    # Import history
├── pre-import-snapshot/          # Current snapshot (overwritten on each import)
├── 2025-01-06-143022/
│   └── import.log                # Log of what was done
├── 2025-01-05-091500/
│   └── import.log
└── ...
```

### Restore Backup

If an import causes problems:

```
/restore-backup

⚠ WARNING: This will restore Claude Code session storage to its state 
before the most recent import.

Snapshot taken: 2025-01-06 at 14:30

Any Claude Code work done after this snapshot will be LOST.
This cannot be undone.

Type RESTORE to confirm: _
```

### Important Notes

- Restore is destructive — there is no undo
- Users should export any valuable sessions before restoring
- The pre-import snapshot is overwritten on each import, so only the most recent import can be reverted
- If no imports have been done, `/restore-backup` shows an error

### Phase 2 Consideration

If real-world usage reveals a need for multiple restore points (e.g., initial snapshot that's never overwritten), this can be added based on feedback.

### index.json

Tracks import history:

```json
{
  "last_snapshot_taken": "2025-01-06T14:30:22Z",
  "imports": {
    "2025-01-06-143022": {
      "session_name": "auth-implementation",
      "source_path": ".claude-sessions/auth-implementation/",
      "imported_at": "2025-01-06T14:30:22Z"
    },
    "2025-01-05-091500": {
      "session_name": "payment-system",
      "source_path": ".claude-sessions/payment-system/",
      "imported_at": "2025-01-05T09:15:00Z"
    }
  }
}
```

---

## Non-Interactive Mode

For scripting or CI/CD:

```
python import_session.py .claude-sessions/auth-impl --non-interactive
```

Behavior:
- Uses new session ID (no conflicts possible)
- Keeps all paths as-is (no conversion)
- Takes snapshots as normal
- Fails on validation errors

---

## Open Technical Questions (Investigation Phase)

Before implementation, Claude Code must investigate:

### Session Storage
- What is the exact location of session files?
- What files/directories constitute a complete session?
- Is there a session registry or index file?
- Are sessions tied to machine-specific identifiers?

### Session Format
- What is the complete schema of session files?
- Which fields contain paths?
- Which fields are platform-specific?
- Which fields contain timestamps that might need adjustment?

### Session Restoration
- Can a session be created by placing files in the correct location?
- What validation does Claude Code perform on session files?
- Are there checksums, signatures, or authentication tokens?
- What's the minimum data required for Claude to recognize a session?

### Path Dependencies
- Are absolute paths stored in session data?
- What specific fields contain paths?
- What breaks when a project moves to a different location?
- What breaks when a session moves to a different user's machine?

### Version Compatibility
- Where is Claude Code version stored?
- How does session format change between versions?
- What's the compatibility story for older sessions?

### Configuration Scope  
- Are all relevant configs in `.claude/` or are some stored globally?
- Are there user-specific settings that affect session behavior?
- What in `~/.claude/` (global) vs `.claude/` (project) affects sessions?

---

## Deliverables

### Phase 0: Investigation
- Enumerate all files/data that constitute a Claude Code session
- Document file locations and formats
- Test manual session copying scenarios
- Document what breaks and why
- Map all path-containing fields
- Verify version compatibility concerns
- **Assess feasibility of session import/resume**

### Phase 1a: Export Tool
- Copy session files to `.claude-sessions/<n>/`
- Generate `RENDERED.md` for GitHub viewing (simple, clean formatting)
- Generate `.cctrace-manifest.json` (no checksums)
- Handle git initialization prompt
- Respect and report .gitignore exclusions
- Handle export naming collisions
- Capture dependency/version metadata
- Support authorship anonymization option

### Phase 1b: Import Tool (if feasible per Phase 0)
- Validate manifest exists (required for valid export)
- Check Claude Code version compatibility (warn on mismatch)
- Create pre-import snapshot
- Copy session files to Claude Code locations
- Add CLAUDE.md note with original environment context
- Session ID handling (new ID by default)
- Non-destructive conflict handling (abort, don't overwrite)
- Comprehensive logging
- `/restore-backup` for recovery (single restore point)

### Phase 2: Enhancements (Evaluate Post-Phase 1)
- Interactive path conflict resolution (if users request it)
- Initial snapshot (permanent, never overwritten)
- Manifest checksums (if integrity issues emerge)
- Rich RENDERED.md formatting (collapsible sections, etc.)

### Phase 3: Polish
- Non-interactive mode for scripting
- Clear error messages
- User documentation
- Example workflows

---

## Success Criteria

1. **Export works**: A session can be exported to `.claude-sessions/` within the project repo with all necessary files preserved

2. **GitHub renders well**: `RENDERED.md` displays a clear, navigable view of the session when viewed on GitHub

3. **Import works across users**: User B can clone User A's repo and import a session that User A exported

4. **Claude resumes correctly**: After import, Claude Code recognizes the session and can continue with full conversation context

5. **No data loss**: Import never overwrites existing local data without explicit user action outside the tool

6. **Recoverable**: If an import causes problems, user can restore to pre-import or initial state via `/restore-backup`

---

## Future Possibilities (Out of Scope for Initial Version)

- GitHub Action for auto-export on push
- Session diffing (compare two sessions)
- Session search/indexing across repositories
- Real-time collaborative sessions
- Partial session import (specific turns only)
- Session branching (multiple continuations from same point)
- Integration with GitHub Discussions for session-based code review
- VSCode extension for session visualization
