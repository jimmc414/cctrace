# Phase 0 Investigation: Portable Claude Code Sessions

## Investigation Status

### Completed Analysis
1. ✅ Session Storage Discovery - mapped complete `~/.claude/` structure
2. ✅ Session Format Analysis - documented JSONL schema and all fields
3. ✅ Existing cctrace Code Review - analyzed `export_claude_session.py`
4. ⏳ Session Resumption Testing - **NEXT: Run hands-on experiments**
5. ✅ Configuration Discovery - identified `.claude/` contents

---

## Key Findings

### 1. Session Storage Location
```
~/.claude/
├── projects/              # Session JSONL files (419MB, 764 sessions)
│   └── -mnt-c-python-*/   # Project dirs (path normalized)
├── file-history/          # Versioned file snapshots by session
├── session-env/           # Session environment data
├── todos/                 # Task tracking per session
├── plans/                 # Plan files (like this one)
├── __store.db             # SQLite database
├── history.jsonl          # Global session history
├── commands/              # Custom slash commands
├── skills/                # Custom skills
├── agents/                # Custom agents
├── rules/                 # Custom rules
└── settings.json          # Global settings
```

### 2. Session JSONL Schema

**Message Structure:**
```json
{
  "sessionId": "UUID",           // Session identifier
  "uuid": "UUID",                // Message ID
  "parentUuid": "UUID|null",     // Parent message (threading)
  "cwd": "/path/to/project",     // FILE PATH - platform specific
  "version": "2.0.76",           // Claude Code version
  "agentId": "a02c6c6",          // Short session ID
  "slug": "human-readable-name", // Session name
  "timestamp": "ISO-8601",       // Message timestamp
  "type": "user|assistant",
  "message": {
    "role": "user|assistant",
    "content": [...],            // Content blocks
    "model": "claude-*",         // (assistant only)
    "id": "msg_*",               // Anthropic ID - DO NOT MODIFY
    "usage": {...}               // Token usage
  },
  "requestId": "req_*"           // Anthropic request ID - DO NOT MODIFY
}
```

**Content Block Types:**
- `thinking` - Has cryptographic `signature` - **DO NOT MODIFY TEXT**
- `text` - Plain text response
- `tool_use` - Contains `input.file_path` (FILE PATHS)
- `tool_result` - Tool output

### 3. Fields Critical for Import

| Category | Fields | Notes |
|----------|--------|-------|
| **FILE PATHS** | `cwd`, `input.file_path`, `filePath` | Need conversion on import |
| **UUIDs** | `sessionId`, `uuid`, `parentUuid`, `agentId` | May regenerate |
| **DO NOT MODIFY** | `message.id`, `requestId`, thinking `signature` | Anthropic/crypto fields |
| **Timestamps** | `timestamp` | Historical record, keep as-is |

### 4. Existing cctrace Capabilities

**Already implemented in `export_claude_session.py`:**
- Session discovery via path normalization
- Raw JSONL export (complete fidelity)
- Markdown/XML formatted output
- Session metadata extraction
- PID-based active session detection

**Not yet implemented:**
- Import functionality
- Path conversion
- Session ID regeneration
- Backup/restore
- Configuration export (.claude/ directory)

---

## Testing Plan (To Execute)

### Experiment 1: Copy Session As-Is
- Copy existing session to new project directory
- Test if Claude Code recognizes it
- Expected: Should work (file presence is detection mechanism)

### Experiment 2: Modify CWD Path
- Copy session, change `cwd` field to different path
- Test if Claude handles path mismatch
- Expected: May work - Claude often adapts to current directory

### Experiment 3: Change Session ID
- Copy session, generate new `sessionId`
- Test if session loads with new ID
- Expected: Should work - ID is for tracking, not validation

### Experiment 4: Modify Thinking Block (Signature Test)
- Copy session, slightly modify thinking text
- Test if signature validation fails
- Expected: May break - signatures verify integrity

---

## Next Steps After Testing

1. **Create `docs/investigation-findings.md`** - Complete documentation
2. **Create `docs/technical-requirements.md`** - Fill in Section 2 from requirements.md
3. **Create `docs/implementation-plan.md`** - Phased implementation
4. **Write feasibility assessment** - Go/no-go decision with limitations

---

## Preliminary Feasibility Assessment

**Likely FEASIBLE** based on schema analysis:
- Sessions are self-contained JSONL files
- No central registry or validation server
- Path mismatches can be handled via CLAUDE.md notes (per objective.md)
- New session IDs can be generated safely

**Potential Blockers:**
- Thinking block signatures - if Claude Code validates these, modified thinking text would fail
- Platform-specific paths embedded throughout conversation history
- Version compatibility between Claude Code versions

**Testing will confirm** whether session import/resume actually works in practice.
