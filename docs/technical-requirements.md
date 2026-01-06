# Technical Requirements: Portable Claude Code Sessions

This document provides the technical requirements (Section 2 of `requirements.md`) based on Phase 0 investigation findings.

---

## 2. Technical Requirements

### 2.1 Session Storage

#### 2.1.1 Location Requirements

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-001 | Session directory location | `~/.claude/projects/<normalized-path>/` |
| TECH-002 | Path normalization (Unix) | Replace `/`, `.`, `_` with `-`, prefix with `-` |
| TECH-003 | Path normalization (Windows) | Replace `\`, `/`, `:`, `.`, `_` with `-`, no prefix |
| TECH-004 | Dot handling | Replace `.` with `-` in path normalization |
| TECH-005 | Underscore handling | Replace `_` with `-` in path normalization (**CRITICAL**) |
| TECH-006 | Session file format | JSONL (JSON Lines) |
| TECH-007 | Session file naming | `<sessionId>.jsonl` (UUID format recommended) |

#### 2.1.2 Export Location

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-010 | Export directory | `.claude-sessions/<export-name>/` in project root |
| TECH-011 | Required files | Session JSONL, `.cctrace-manifest.json`, `RENDERED.md` |
| TECH-012 | Config export | `.claude/` directory contents (optional) |

### 2.2 Session JSONL Format

#### 2.2.1 Message Types

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-020 | File history snapshot | `{"type": "file-history-snapshot", ...}` |
| TECH-021 | User message | `{"type": "user", "message": {"role": "user", ...}}` |
| TECH-022 | Assistant message | `{"type": "assistant", "message": {"role": "assistant", ...}}` |

#### 2.2.2 Required Fields (User/Assistant Messages)

| ID | Field | Type | Required | Notes |
|----|-------|------|----------|-------|
| TECH-030 | `sessionId` | UUID string | YES | Session identifier |
| TECH-031 | `uuid` | UUID string | YES | Message identifier |
| TECH-032 | `parentUuid` | UUID string \| null | YES | Threading reference |
| TECH-033 | `timestamp` | ISO-8601 string | YES | Message creation time |
| TECH-034 | `type` | "user" \| "assistant" | YES | Message type |
| TECH-035 | `message` | object | YES | Message content |
| TECH-036 | `cwd` | absolute path string | YES | Working directory |
| TECH-037 | `version` | semver string | YES | Claude Code version |
| TECH-038 | `userType` | "external" | YES | Always "external" |
| TECH-039 | `isSidechain` | boolean | YES | Sidechain indicator |

#### 2.2.3 Optional Fields

| ID | Field | Type | Notes |
|----|-------|------|-------|
| TECH-040 | `agentId` | string | Short session ID |
| TECH-041 | `slug` | string | Human-readable session name |
| TECH-042 | `gitBranch` | string | Current git branch |
| TECH-043 | `thinkingMetadata` | object | Extended thinking config |
| TECH-044 | `todos` | array | Associated todos |
| TECH-045 | `requestId` | string | Anthropic request ID |

#### 2.2.4 Content Block Types

| ID | Block Type | Structure | Contains Paths? |
|----|------------|-----------|-----------------|
| TECH-050 | `thinking` | `{type, thinking, signature}` | NO |
| TECH-051 | `text` | `{type, text}` | Possibly (in text) |
| TECH-052 | `tool_use` | `{type, id, name, input}` | YES (`input.file_path`, `input.path`) |
| TECH-053 | `tool_result` | `{type, tool_use_id, content}` | Possibly (in content) |

### 2.3 Protected Fields (DO NOT MODIFY)

| ID | Requirement | Fields | Reason |
|----|-------------|--------|--------|
| TECH-060 | Anthropic identifiers | `message.id`, `requestId` | Token tracking/audit |
| TECH-061 | Cryptographic signatures | `content[].signature` | Integrity verification |
| TECH-062 | Tool invocation IDs | `tool_use.id`, `tool_result.tool_use_id` | Result matching |
| TECH-063 | Thinking block text | `content[].thinking` | Signed content |
| TECH-064 | Timestamps | `timestamp` | Historical record |

### 2.4 Modifiable Fields

| ID | Requirement | Fields | Condition |
|----|-------------|--------|-----------|
| TECH-070 | Session identifier | `sessionId` | Generate new on import |
| TECH-071 | Message UUIDs | `uuid`, `parentUuid` | Update consistently |
| TECH-072 | Agent identifier | `agentId` | Generate new on import |
| TECH-073 | Working directory | `cwd` | Optional path conversion |
| TECH-074 | File paths in tool input | `input.file_path` | Optional path conversion |
| TECH-075 | Version field | `version` | Can update to current |

### 2.5 Manifest Schema

#### 2.5.1 Required Manifest Fields

| ID | Field | Type | Purpose |
|----|-------|------|---------|
| TECH-080 | `cctrace_version` | string | cctrace version that created export |
| TECH-081 | `export_timestamp` | ISO-8601 | When export was created |
| TECH-082 | `session_id` | UUID | Original session ID |
| TECH-083 | `session_folder_name` | string | Name of export folder |
| TECH-084 | `files_included` | string[] | List of files in export |
| TECH-085 | `claude_code_version` | string | Claude Code version |

#### 2.5.2 Optional Manifest Fields

| ID | Field | Type | Purpose |
|----|-------|------|---------|
| TECH-090 | `original_user` | string | Username who exported |
| TECH-091 | `original_platform` | string | Platform (linux/darwin/win32) |
| TECH-092 | `original_repo_path` | string | Original project path |
| TECH-093 | `anonymized` | boolean | Whether authorship hidden |
| TECH-094 | `original_repo_name` | string | Original repo name |

#### 2.5.3 Manifest Example

```json
{
  "cctrace_version": "2.0.0",
  "export_timestamp": "2026-01-06T09:30:00Z",
  "session_id": "132b2f66-ee5f-46f6-8904-32d9dc4d36c3",
  "session_folder_name": "auth-implementation",
  "claude_code_version": "2.0.76",
  "files_included": [
    "session.jsonl",
    "RENDERED.md",
    ".cctrace-manifest.json"
  ],
  "original_user": "jim",
  "original_platform": "linux",
  "original_repo_path": "/mnt/c/python/myproject",
  "anonymized": false
}
```

### 2.6 Import Requirements

#### 2.6.1 File Placement

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-100 | Target directory | `~/.claude/projects/<normalized-current-path>/` |
| TECH-101 | Session file naming | Use new UUID or preserve original name |
| TECH-102 | No database entry needed | JSONL file presence is sufficient |

#### 2.6.2 Session ID Handling

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-110 | Default behavior | Generate new `sessionId` UUID |
| TECH-111 | UUID regeneration | Update all `uuid` and `parentUuid` consistently |
| TECH-112 | Agent ID | Generate new `agentId` (7-char hex) |
| TECH-113 | Preserve original | Store original `sessionId` in manifest or metadata |

#### 2.6.3 Path Handling (Phase 1)

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-120 | Default: No conversion | Import paths as-is |
| TECH-121 | CLAUDE.md note | Add import context note to project CLAUDE.md |
| TECH-122 | Note contents | Original user, path, platform, export date |

#### 2.6.4 Conflict Detection

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-130 | Session ID conflict | Check if `sessionId` already exists locally |
| TECH-131 | File conflict | Check if target file path already exists |
| TECH-132 | Conflict action | Abort import (never overwrite silently) |

### 2.7 Backup/Restore

#### 2.7.1 Pre-Import Snapshot

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-140 | Snapshot location | `~/.claude-session-imports/pre-import-snapshot/` |
| TECH-141 | Snapshot contents | Copy of `~/.claude/projects/<target>/` |
| TECH-142 | Overwrite behavior | New snapshot overwrites previous |

#### 2.7.2 Import Logging

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-150 | Log location | `~/.claude-session-imports/<timestamp>/import.log` |
| TECH-151 | Log contents | Files written, paths used, any warnings |
| TECH-152 | Index file | `~/.claude-session-imports/index.json` |

### 2.8 Associated Data (Phase 2)

#### 2.8.1 Optional Export Items

| ID | Data Type | Location | Phase |
|----|-----------|----------|-------|
| TECH-160 | File history | `~/.claude/file-history/<sessionId>/` | Phase 2 |
| TECH-161 | Session environment | `~/.claude/session-env/<sessionId>/` | Phase 2 |
| TECH-162 | Todo data | `~/.claude/todos/<sessionId>-*.json` | Phase 2 |
| TECH-163 | Plan files | `~/.claude/plans/<slug>.md` | Phase 2 |

### 2.9 Platform Compatibility

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-170 | Linux support | Full support |
| TECH-171 | macOS support | Full support (same path format) |
| TECH-172 | Windows (WSL) | Full support |
| TECH-173 | Windows (native) | Path normalization differs |
| TECH-174 | Cross-platform import | Detect source platform from manifest |

### 2.10 Version Compatibility

| ID | Requirement | Specification |
|----|-------------|---------------|
| TECH-180 | Version storage | Store `version` field in manifest |
| TECH-181 | Version check | Compare export version with current Claude Code |
| TECH-182 | Mismatch action | Warn user, allow proceed or abort |
| TECH-183 | Format migration | Not supported in Phase 1 |

---

## 3. Requirement Traceability

### 3.1 Export Requirements Mapping

| Behavioral | Technical |
|------------|-----------|
| EXP-001 | TECH-001, TECH-005, TECH-010 |
| EXP-002 | TECH-020-022, TECH-030-045 |
| EXP-003 | TECH-052, TECH-053 |
| EXP-004 | TECH-050 |
| EXP-005 | TECH-033 |
| EXP-006 | TECH-030, TECH-037, TECH-085 |
| EXP-020 | TECH-080-094 |

### 3.2 Import Requirements Mapping

| Behavioral | Technical |
|------------|-----------|
| IMP-001 | TECH-100-102 |
| IMP-002 | TECH-020-053 (preserved) |
| IMP-003 | TECH-100-102 |
| IMP-010 | TECH-080-085 |
| IMP-020 | TECH-110 |
| IMP-021 | TECH-113 |
| IMP-030 | TECH-130-132 |
| IMP-031 | TECH-140-142 |
| IMP-045 | TECH-120-122 |

### 3.3 Restore Requirements Mapping

| Behavioral | Technical |
|------------|-----------|
| RST-001 | TECH-140-142 |
| RST-003 | User confirmation (implementation) |
| RST-004 | User warning (implementation) |

---

## 4. Validation Rules

### 4.1 Export Validation

| ID | Rule | Error Message |
|----|------|---------------|
| VAL-001 | Session JSONL must exist | "No session file found at {path}" |
| VAL-002 | Session must be valid JSONL | "Invalid JSONL format: {error}" |
| VAL-003 | Export directory must be writable | "Cannot write to {path}" |
| VAL-004 | Git repo required (if configured) | "Not a git repository" |

### 4.2 Import Validation

| ID | Rule | Error Message |
|----|------|---------------|
| VAL-010 | Manifest must exist | "No .cctrace-manifest.json found" |
| VAL-011 | Manifest must be valid JSON | "Invalid manifest: {error}" |
| VAL-012 | Required manifest fields | "Missing required field: {field}" |
| VAL-013 | Session file must exist | "Session file {name} not found in export" |
| VAL-014 | No target file conflict | "File already exists: {path}" |
| VAL-015 | No session ID conflict | "Session {id} already exists locally" |

### 4.3 Manifest Validation

| ID | Rule | Specification |
|----|------|---------------|
| VAL-020 | `cctrace_version` | Must be present, string |
| VAL-021 | `export_timestamp` | Must be valid ISO-8601 |
| VAL-022 | `session_id` | Must be valid UUID |
| VAL-023 | `files_included` | Must be array of strings |
| VAL-024 | `claude_code_version` | Must be present, string |
