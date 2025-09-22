import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_claude_session import find_project_sessions


def test_find_project_sessions_handles_dot_in_project_path(tmp_path, monkeypatch):
    """Claude replaces dots with dashes in project directory names."""
    fake_home = tmp_path / "home"
    claude_dir = fake_home / ".claude" / "projects" / "-mnt-c-project-git"
    claude_dir.mkdir(parents=True)

    session_file = claude_dir / "session123.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    sessions = find_project_sessions("/mnt/c/project.git")

    assert [session["path"] for session in sessions] == [session_file]
