# Claude Code Investigation Kickoff Prompt

Copy and paste the following into Claude Code after:
1. Cloning cctrace repo
2. Placing objective.md and requirements.md in the repo root

---

## Prompt:

I'm building a major new feature for cctrace: portable, resumable Claude Code sessions. The goal is to let users export sessions to GitHub (with nice rendering) and allow other users to clone and import those sessions to continue them.

I've created two planning documents:
- `objective.md` — Complete design intent, user workflows, and Phase 1/2 scope
- `requirements.md` — Testable behavioral requirements (technical requirements TBD after investigation)

**Before writing any code, I need you to complete Phase 0: Investigation.**

Please read both documents thoroughly first, then investigate the following:

### Investigation Tasks

**1. Session Storage Discovery**
- Where exactly does Claude Code store session data? (You already know `~/.claude/projects/` from existing cctrace — verify this is complete)
- What files/directories constitute a complete session?
- Is there a session registry or index file beyond the individual session JSONL files?
- Are there any files in `~/.claude/` (global) vs `.claude/` (project-local) that affect sessions?
- Are sessions tied to machine-specific or user-specific identifiers?

**2. Session Format Analysis**
- What is the complete schema of session JSONL files?
- Document all fields and their purposes
- Which fields contain file paths? (Critical for import)
- Which fields contain UUIDs/session IDs that might need regeneration?
- Which fields contain timestamps?
- Are there any signatures, checksums, or authentication tokens embedded?

**3. Session Resumption Testing**
Manually test what's required to resume a session:
- Can you copy a session JSONL to a different project directory and have Claude Code recognize it?
- What happens if you copy to a different user's machine (simulate by changing paths)?
- What happens if you change the session ID/UUID in the file?
- What breaks? What works?
- Document the minimum viable set of changes needed for successful import

**4. Configuration Discovery**
- What files in `.claude/` (commands, hooks, skills, agents) affect session behavior?
- Are any of these referenced in session files?
- What would need to be exported alongside session data for full portability?

**5. Existing cctrace Code Review**
- Review `export_claude_session.py` — what does it already handle well?
- What would need to change to support the new export format (raw files + RENDERED.md + manifest)?
- Are there any assumptions in the current code that conflict with the new design?

### Deliverables

After investigation, please create:

1. **`docs/investigation-findings.md`** — Complete documentation of everything you discovered, organized by the sections above

2. **`docs/technical-requirements.md`** — The "Section 2" from requirements.md, now filled in with specific technical requirements based on your findings

3. **`docs/implementation-plan.md`** — A phased implementation plan that includes:
   - What existing cctrace code to keep/modify/replace
   - Order of implementation
   - Test strategy for each component
   - Any risks or blockers identified

4. **Feasibility assessment** — Explicit statement: Is session import/resume feasible? What limitations exist?

### Important Notes

- Do not write implementation code yet — investigation only
- If you need to create test files to experiment with session copying, do so in a clearly marked test directory
- Be thorough — assumptions here affect everything built on top
- If you discover something that contradicts the objective.md design, document it clearly so we can adjust

Start by reading objective.md and requirements.md, then tell me your investigation plan before beginning.
