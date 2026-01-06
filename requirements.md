# Requirements: Portable Claude Code Sessions

This document defines testable requirements for the cctrace session export/import feature. 

**Document Structure:**
- **Behavioral Requirements** (Section 1): User-facing outcomes, written before technical discovery. These define *what* must happen from the user's perspective.
- **Technical Requirements** (Section 2): Implementation-specific details, to be added after investigation phase. These define *how* it happens internally.

---

## 1. Behavioral Requirements

These requirements are testable via integration tests and define success from the user's perspective.

### 1.1 Export

#### 1.1.1 Basic Export

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| EXP-001 | User can export current session | Running `/export-session` in an active Claude Code session creates an export in `.claude-sessions/` |
| EXP-002 | Export includes conversation history | Exported data contains all user messages and Claude responses from the session |
| EXP-003 | Export includes tool usage | Exported data contains all tool invocations (bash commands, file operations) and their results |
| EXP-004 | Export includes thinking blocks | Exported data contains Claude's reasoning/thinking blocks |
| EXP-005 | Export includes timestamps | Each message in the export has associated timestamp metadata |
| EXP-006 | Export includes session metadata | Export contains session ID, model used, token usage, and project path |

#### 1.1.2 Git Integration

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| EXP-010 | Export requires git repository | If current directory is not a git repo, user is prompted to initialize or abort |
| EXP-011 | Export respects .gitignore | Files listed in .gitignore are not included in the export |
| EXP-012 | Export shows excluded files | User is shown which files are excluded by .gitignore before confirming export |
| EXP-013 | Repository uses required prefix | Exported repository name must begin with `cctrace_` |

#### 1.1.3 Export Manifest

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| EXP-020 | Export creates manifest | `.cctrace-manifest.json` is created in the export directory |
| EXP-021 | Manifest contains checksums (Phase 2) | SHA-256 checksums — deferred, git provides integrity |
| EXP-022 | Manifest contains version info | Manifest includes cctrace version and Claude Code version |
| EXP-023 | Manifest contains export metadata | Manifest includes export timestamp, session ID, and author (if not anonymized) |
| EXP-024 | Manifest validates export origin | Manifest structure allows import to verify this is a valid cctrace export |

#### 1.1.4 GitHub Rendering

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| EXP-030 | Export creates RENDERED.md | A human-readable markdown file is generated in the export directory |
| EXP-031 | RENDERED.md displays on GitHub | When viewed on GitHub, the file renders with proper formatting |
| EXP-032 | RENDERED.md shows conversation | The rendered view shows user/Claude exchanges with clear visual distinction |
| EXP-033 | RENDERED.md has collapsible sections (Phase 2) | Rich formatting — evaluate based on user feedback |
| EXP-034 | RENDERED.md shows metadata | Session duration, turn count, files modified, and model used are visible |

#### 1.1.5 Export Options

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| EXP-040 | User can name the export | User is prompted to provide a name for the export folder |
| EXP-041 | Duplicate names are handled | If export name exists, user can rename, auto-rename, or abort |
| EXP-042 | User can anonymize export | User can choose to exclude username/machine info from export |
| EXP-043 | Environment variables excluded by default | .env files and environment variables are not exported unless explicitly enabled |

---

### 1.2 Import

#### 1.2.1 Basic Import

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| IMP-001 | User can import session | Running `/import-session <path>` loads a session from the specified export |
| IMP-002 | Import restores conversation context | After import, Claude Code has access to full conversation history |
| IMP-003 | Claude can continue session | After import, Claude can respond to new prompts with awareness of prior conversation |
| IMP-004 | Import works across users | User B can import a session exported by User A |
| IMP-005 | Import works across machines | A session exported on machine A can be imported on machine B |

#### 1.2.2 Validation

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| IMP-010 | Import validates manifest | Import fails with clear error if `.cctrace-manifest.json` is missing |
| IMP-011 | Import validates checksums (Phase 2) | Checksum validation — deferred with manifest checksums |
| IMP-012 | Import warns on version mismatch | If Claude Code version differs from export, user is warned and can choose to proceed or abort |
| IMP-013 | Import reports dependencies | Missing MCP servers and packages are reported to user before import proceeds |

#### 1.2.3 Session ID Handling

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| IMP-020 | Import generates new session ID by default | Imported session receives a new unique session ID |
| IMP-021 | Original session ID preserved in metadata | The original session ID from export is recorded but not used as the active ID |
| IMP-022 | User can request preserved session ID | With `--preserve-session-id` flag, original session ID is used |
| IMP-023 | Conflicting session ID aborts import | If preserved session ID already exists locally, import aborts with error |

#### 1.2.4 Non-Destructive Behavior

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| IMP-030 | Import never silently overwrites | If any destination file exists, import aborts (does not overwrite) |
| IMP-031 | Import creates snapshot | Before modifying any files, pre-import snapshot is created |
| IMP-032 | Pre-import snapshot updated each import | Before each import, current session storage state is captured |
| IMP-033 | Initial snapshot (Phase 2) | Permanent initial snapshot — evaluate after Phase 1 if needed |

#### 1.2.5 Path Handling (Phase 2 — Evaluate Post-Implementation)

*See Section 5.1. Phase 1 approach: Import paths as-is, add CLAUDE.md note for context.*

| ID | Requirement | Phase |
|----|-------------|-------|
| IMP-040 | Import detects path conflicts | Phase 2 |
| IMP-041 | User can resolve paths interactively | Phase 2 |
| IMP-042 | User can batch convert paths | Phase 2 |
| IMP-043 | URLs excluded from conversion | Phase 2 |
| IMP-044 | Conversation text not modified | Phase 1 (default: no modification) |
| IMP-045 | CLAUDE.md note added on import | Phase 1 — Note explains original environment context |

---

### 1.3 Restore

#### 1.3.1 Restore Functionality

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| RST-001 | User can restore pre-import state | `/restore-backup` restores state before most recent import |
| RST-002 | Restore to initial state (Phase 2) | Permanent initial restore point — evaluate after Phase 1 |
| RST-003 | Restore requires explicit confirmation | User must type RESTORE (not just y) to proceed |
| RST-004 | Restore shows what will be lost | User is warned that post-snapshot work will be lost |

#### 1.3.2 Restore Limitations

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| RST-010 | Restore is destructive | After restore, there is no undo |
| RST-011 | Snapshot preserved after restore | Using the snapshot does not delete it |

---

### 1.4 Error Handling

#### 1.4.1 Export Errors

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ERR-001 | No active session error | If no active Claude Code session, export fails with clear message |
| ERR-002 | Not a git repo error | If directory not a git repo and user declines init, export aborts cleanly |
| ERR-003 | Write permission error | If cannot write to export location, error message indicates the problem |

#### 1.4.2 Import Errors

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ERR-010 | Invalid export path error | If specified path doesn't exist or isn't a valid export, clear error shown |
| ERR-011 | Manifest missing error | If `.cctrace-manifest.json` missing, error explains this isn't a valid cctrace export |
| ERR-012 | Checksum mismatch error (Phase 2) | Deferred with checksum validation |
| ERR-013 | Session conflict error | If session ID exists and preservation requested, error explains conflict |

#### 1.4.3 Restore Errors

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ERR-020 | No snapshot exists error | If user runs restore before any imports, clear error shown |
| ERR-021 | Snapshot corrupted error | If snapshot files are missing/corrupted, error indicates manual recovery needed |

---

### 1.5 Logging

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| LOG-001 | Imports are logged | Each import creates a log file in `~/.claude-session-imports/<id>/` |
| LOG-002 | Log contains actions taken | Log records which files were written and where |
| LOG-003 | Import history tracked | `index.json` maintains history of all imports with timestamps |
| LOG-004 | User can view import history | User can see list of past imports and their status |

---

## 2. Technical Requirements

*To be added after investigation phase.*

This section will contain implementation-specific requirements based on discovery of:
- Exact file locations and formats for Claude Code sessions
- Required fields and their schemas
- Path-containing fields that need conversion handling
- Session ID fields and references
- Any platform-specific considerations

---

## 3. Requirement Traceability

*To be updated after discovery.*

This section will map behavioral requirements to technical requirements, ensuring each user-facing behavior is supported by specific implementation details.

---

## 4. Out of Scope

The following are explicitly not requirements for the initial version:

- Real-time collaborative sessions
- Partial session import (specific turns only)
- Session branching (multiple continuations)
- Automatic merge conflict resolution for sessions
- Secret scanning/redaction
- Automatic dependency installation

---

## 5. Phase 2 (Evaluate After Phase 1 Implementation)

The following features were identified as potentially over-engineered. They should be evaluated for necessity after Phase 1 is complete and real-world usage provides feedback:

### 5.1 Interactive Path Conversion (Deferred)

Originally specified: Interactive prompt system for converting paths during import (user paths, platform paths, absolute/relative).

**Deferred because:** Claude Code itself can handle path mismatches post-import. When Claude encounters a non-existent path, it can identify the issue and either fix it or ask the user. This is more flexible and context-aware than pre-import conversion.

**Phase 1 approach:** Import paths as-is. Add a note to CLAUDE.md in the imported session explaining the situation:

```markdown
## Imported Session Note

This session was imported from another user/machine. Some paths in the 
conversation history may reference the original environment:
- Original user: alice
- Original path: /home/alice/myproject/

If you encounter path errors, the files are likely in the current 
working directory or need path adjustment for this environment.
```

### 5.2 Dual Permanent Snapshots (Deferred)

Originally specified: Two snapshots — initial (never overwritten) + pre-import (overwritten each import).

**Deferred because:** Pre-import snapshot alone is likely sufficient. The "initial snapshot forever" guards against a cascading failure mode that may never occur.

**Phase 1 approach:** Single pre-import snapshot only. If real-world usage reveals need for initial snapshot, add in Phase 2.

### 5.3 RENDERED.md Rich Features (Evaluate)

Originally specified: Collapsible sections, metadata dashboards, GitHub alert syntax, turn-by-turn navigation.

**Evaluate because:** A simpler markdown format may provide 80% of the value. Rich formatting should be driven by user feedback on what's actually useful for review.

**Phase 1 approach:** Start with clean, readable markdown. Add rich features if users request them.

### 5.4 Manifest Checksums (Deferred)

Originally specified: SHA-256 checksums for all exported files.

**Deferred because:** Git already provides integrity checking. Checksums add complexity for a problem git solves.

**Phase 1 approach:** Manifest validates export is from cctrace (required fields, version info) but omits file checksums. Add checksums if integrity issues emerge in practice.
