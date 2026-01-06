import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from import_session import (
    validate_manifest,
    get_normalized_project_dir,
    get_target_directory,
    generate_new_session_id,
    generate_new_agent_id,
    regenerate_message_uuids,
    read_session_jsonl,
    write_session_file,
)


# =============================================================================
# Manifest Validation Tests
# =============================================================================

def test_validate_manifest_missing(tmp_path):
    """Should raise ImportError when manifest is missing."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    with pytest.raises(ImportError) as excinfo:
        validate_manifest(export_dir)

    assert "No .cctrace-manifest.json found" in str(excinfo.value)


def test_validate_manifest_invalid_json(tmp_path):
    """Should raise ImportError when manifest is invalid JSON."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    manifest_path = export_dir / ".cctrace-manifest.json"
    manifest_path.write_text("not valid json {", encoding="utf-8")

    with pytest.raises(ImportError) as excinfo:
        validate_manifest(export_dir)

    assert "Invalid manifest JSON" in str(excinfo.value)


def test_validate_manifest_missing_fields(tmp_path):
    """Should raise ImportError when required fields are missing."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    manifest_path = export_dir / ".cctrace-manifest.json"
    manifest_path.write_text(json.dumps({"cctrace_version": "2.0.0"}), encoding="utf-8")

    with pytest.raises(ImportError) as excinfo:
        validate_manifest(export_dir)

    assert "Missing required fields" in str(excinfo.value)


def test_validate_manifest_valid(tmp_path):
    """Should return manifest dict when valid."""
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    manifest = {
        "cctrace_version": "2.0.0",
        "session_id": "test-session-id",
        "session_data": {"main_session": "session/main.jsonl"}
    }

    manifest_path = export_dir / ".cctrace-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_manifest(export_dir)

    assert result == manifest


# =============================================================================
# Path Normalization Tests
# =============================================================================

def test_get_normalized_project_dir_unix():
    """Should normalize Unix paths correctly."""
    # Unix path: /mnt/c/python/cctrace -> -mnt-c-python-cctrace
    result = get_normalized_project_dir("/mnt/c/python/cctrace")

    # On Unix, should have - prefix
    import os
    if os.name != 'nt':
        assert result == "-mnt-c-python-cctrace"


def test_get_normalized_project_dir_underscore():
    """Should convert underscores to hyphens."""
    result = get_normalized_project_dir("/mnt/c/python/cctrace_test")

    import os
    if os.name != 'nt':
        assert result == "-mnt-c-python-cctrace-test"


def test_get_normalized_project_dir_dots():
    """Should convert dots to hyphens."""
    result = get_normalized_project_dir("/mnt/c/my.project")

    import os
    if os.name != 'nt':
        assert result == "-mnt-c-my-project"


def test_get_target_directory(tmp_path, monkeypatch):
    """Should return correct target directory path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    result = get_target_directory(Path("/mnt/c/python/myproject"))

    import os
    if os.name != 'nt':
        expected = fake_home / ".claude" / "projects" / "-mnt-c-python-myproject"
        assert result == expected


# =============================================================================
# UUID Generation Tests
# =============================================================================

def test_generate_new_session_id():
    """Should generate valid UUID string."""
    result = generate_new_session_id()

    # Should be valid UUID format
    import uuid
    uuid.UUID(result)  # Raises ValueError if invalid
    assert len(result) == 36


def test_generate_new_agent_id():
    """Should generate 7-character hex string."""
    result = generate_new_agent_id()

    assert len(result) == 7
    assert all(c in "0123456789abcdef" for c in result)


# =============================================================================
# UUID Regeneration Tests
# =============================================================================

def test_regenerate_message_uuids_updates_session_id():
    """Should update sessionId in all messages."""
    messages = [
        {"sessionId": "old-session-id", "uuid": "msg-1"},
        {"sessionId": "old-session-id", "uuid": "msg-2"},
    ]

    result = regenerate_message_uuids(messages, "new-session-id", "/new/path")

    assert all(msg["sessionId"] == "new-session-id" for msg in result)


def test_regenerate_message_uuids_updates_cwd():
    """Should update cwd in all messages."""
    messages = [
        {"sessionId": "old", "uuid": "msg-1", "cwd": "/old/path"},
        {"sessionId": "old", "uuid": "msg-2", "cwd": "/old/path"},
    ]

    result = regenerate_message_uuids(messages, "new-session", "/new/path")

    assert all(msg["cwd"] == "/new/path" for msg in result)


def test_regenerate_message_uuids_maintains_parent_refs():
    """Should update parentUuid references correctly."""
    messages = [
        {"sessionId": "old", "uuid": "parent-uuid", "parentUuid": None},
        {"sessionId": "old", "uuid": "child-uuid", "parentUuid": "parent-uuid"},
    ]

    result = regenerate_message_uuids(messages, "new-session", "/new/path")

    # Get new UUIDs
    new_parent_uuid = result[0]["uuid"]
    new_child_uuid = result[1]["uuid"]

    # Child should reference new parent UUID
    assert result[1]["parentUuid"] == new_parent_uuid

    # UUIDs should be different from originals
    assert new_parent_uuid != "parent-uuid"
    assert new_child_uuid != "child-uuid"


def test_regenerate_message_uuids_generates_new_agent_id():
    """Should generate new agentId for all messages."""
    messages = [
        {"sessionId": "old", "uuid": "msg-1", "agentId": "abc1234"},
        {"sessionId": "old", "uuid": "msg-2", "agentId": "abc1234"},
    ]

    result = regenerate_message_uuids(messages, "new-session", "/new/path")

    # All messages should have same new agentId
    agent_ids = [msg["agentId"] for msg in result]
    assert len(set(agent_ids)) == 1
    assert agent_ids[0] != "abc1234"


# =============================================================================
# Session File Read/Write Tests
# =============================================================================

def test_read_session_jsonl(tmp_path):
    """Should read JSONL file and return list of messages."""
    session_file = tmp_path / "session.jsonl"

    messages = [
        {"uuid": "msg-1", "type": "user"},
        {"uuid": "msg-2", "type": "assistant"},
    ]

    session_file.write_text(
        "\n".join(json.dumps(m) for m in messages),
        encoding="utf-8"
    )

    result = read_session_jsonl(session_file)

    assert result == messages


def test_read_session_jsonl_handles_blank_lines(tmp_path):
    """Should skip blank lines in JSONL file."""
    session_file = tmp_path / "session.jsonl"

    content = '{"uuid": "msg-1"}\n\n{"uuid": "msg-2"}\n'
    session_file.write_text(content, encoding="utf-8")

    result = read_session_jsonl(session_file)

    assert len(result) == 2


def test_write_session_file_creates_file(tmp_path):
    """Should write messages to JSONL file."""
    target_path = tmp_path / "sessions" / "new-session.jsonl"

    messages = [
        {"uuid": "msg-1", "type": "user"},
        {"uuid": "msg-2", "type": "assistant"},
    ]

    write_session_file(messages, target_path)

    assert target_path.exists()

    # Read back and verify
    with open(target_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    assert len(lines) == 2
    assert json.loads(lines[0]) == messages[0]


def test_write_session_file_refuses_overwrite(tmp_path):
    """Should raise FileExistsError if target exists."""
    target_path = tmp_path / "session.jsonl"
    target_path.write_text("{}\n", encoding="utf-8")

    messages = [{"uuid": "msg-1"}]

    with pytest.raises(FileExistsError):
        write_session_file(messages, target_path)


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_uuid_regeneration_preserves_protected_fields():
    """Should NOT modify message.id, requestId, signature, tool_use.id."""
    messages = [
        {
            "sessionId": "old-session",
            "uuid": "msg-uuid",
            "cwd": "/old/path",
            "message": {
                "id": "msg_01ANTHROPIC_ID",
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "test", "signature": "CRYPTO_SIG"},
                    {"type": "tool_use", "id": "toolu_01TOOL_ID", "name": "Read"}
                ]
            },
            "requestId": "req_01REQUEST_ID"
        }
    ]

    result = regenerate_message_uuids(messages, "new-session", "/new/path")

    # These should be changed
    assert result[0]["sessionId"] == "new-session"
    assert result[0]["cwd"] == "/new/path"
    assert result[0]["uuid"] != "msg-uuid"

    # These should NOT be changed
    assert result[0]["message"]["id"] == "msg_01ANTHROPIC_ID"
    assert result[0]["requestId"] == "req_01REQUEST_ID"
    assert result[0]["message"]["content"][0]["signature"] == "CRYPTO_SIG"
    assert result[0]["message"]["content"][1]["id"] == "toolu_01TOOL_ID"
