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


def test_find_project_sessions_handles_underscore_in_project_path(tmp_path, monkeypatch):
    """Claude replaces underscores with dashes in project directory names."""
    fake_home = tmp_path / "home"
    # Underscore in path should become hyphen: cctrace_test -> cctrace-test
    claude_dir = fake_home / ".claude" / "projects" / "-mnt-c-python-cctrace-test"
    claude_dir.mkdir(parents=True)

    session_file = claude_dir / "session456.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Input has underscore, but Claude stores with hyphen
    sessions = find_project_sessions("/mnt/c/python/cctrace_test")

    assert [session["path"] for session in sessions] == [session_file]


def test_find_project_sessions_handles_multiple_special_chars(tmp_path, monkeypatch):
    """Claude replaces dots, underscores, and path separators with dashes."""
    fake_home = tmp_path / "home"
    # Path with dot, underscore, and separators: my_project.v2 -> my-project-v2
    claude_dir = fake_home / ".claude" / "projects" / "-mnt-c-my-project-v2"
    claude_dir.mkdir(parents=True)

    session_file = claude_dir / "session789.jsonl"
    session_file.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    sessions = find_project_sessions("/mnt/c/my_project.v2")

    assert [session["path"] for session in sessions] == [session_file]
