import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from restore_backup import (
    get_snapshot_info,
    get_last_import_info,
    restore_snapshot,
    get_snapshot_dir,
    get_import_storage_dir,
)


# =============================================================================
# Snapshot Info Tests
# =============================================================================

def test_get_snapshot_info_no_snapshot(tmp_path, monkeypatch):
    """Should raise FileNotFoundError when no snapshot exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    with pytest.raises(FileNotFoundError) as excinfo:
        get_snapshot_info()

    assert "No pre-import snapshot found" in str(excinfo.value)


def test_get_snapshot_info_with_snapshot(tmp_path, monkeypatch):
    """Should return snapshot info when snapshot exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create snapshot directory structure
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': '/home/test/.claude/projects/-test-project',
        'backup_exists': False
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    result = get_snapshot_info()

    assert result['exists'] is True
    assert result['timestamp'] == '2026-01-06T12:00:00Z'
    assert result['target_directory'] == '/home/test/.claude/projects/-test-project'
    assert result['backup_exists'] is False


def test_get_snapshot_info_with_backup(tmp_path, monkeypatch):
    """Should return backup path when backup exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create snapshot directory structure with backup
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    # Create backup content
    backup_dir = snapshot_dir / 'projects' / '-test-project'
    backup_dir.mkdir(parents=True)
    (backup_dir / 'old-session.jsonl').write_text('{}')

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': str(fake_home / '.claude' / 'projects' / '-test-project'),
        'backup_exists': True
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    result = get_snapshot_info()

    assert result['exists'] is True
    assert result['backup_exists'] is True
    assert result['backup_path'] is not None
    assert '-test-project' in result['backup_path']


# =============================================================================
# Last Import Info Tests
# =============================================================================

def test_get_last_import_info_no_index(tmp_path, monkeypatch):
    """Should return None when no index exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    result = get_last_import_info()

    assert result is None


def test_get_last_import_info_with_imports(tmp_path, monkeypatch):
    """Should return most recent import info."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create index
    import_dir = fake_home / '.claude-session-imports'
    import_dir.mkdir(parents=True)

    index = {
        'last_snapshot_taken': '2026-01-06T12:00:00Z',
        'imports': {
            '2026-01-05-100000': {
                'session_name': 'old-session',
                'source_path': '/path/to/old',
                'imported_at': '2026-01-05T10:00:00Z'
            },
            '2026-01-06-120000': {
                'session_name': 'new-session',
                'source_path': '/path/to/new',
                'imported_at': '2026-01-06T12:00:00Z'
            }
        }
    }

    with open(import_dir / 'index.json', 'w') as f:
        json.dump(index, f)

    result = get_last_import_info()

    assert result is not None
    assert result['session_name'] == 'new-session'
    assert result['import_id'] == '2026-01-06-120000'


# =============================================================================
# Restore Tests
# =============================================================================

def test_restore_snapshot_no_snapshot(tmp_path, monkeypatch):
    """Should raise FileNotFoundError when no snapshot exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    with pytest.raises(FileNotFoundError):
        restore_snapshot(force=True)


def test_restore_snapshot_empty_backup(tmp_path, monkeypatch):
    """Should delete target directory when backup was empty."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create target directory with imported content
    target_dir = fake_home / '.claude' / 'projects' / '-test-project'
    target_dir.mkdir(parents=True)
    (target_dir / 'imported-session.jsonl').write_text('{"sessionId": "new"}')

    # Create snapshot (no backup - directory was empty before)
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': str(target_dir),
        'backup_exists': False
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    # Perform restore
    result = restore_snapshot(force=True)

    assert result['restored'] is True
    assert not target_dir.exists()  # Should be deleted
    assert not snapshot_dir.exists()  # Snapshot should be cleaned up


def test_restore_snapshot_with_backup(tmp_path, monkeypatch):
    """Should restore backup content when backup exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create target directory with imported content
    target_dir = fake_home / '.claude' / 'projects' / '-test-project'
    target_dir.mkdir(parents=True)
    (target_dir / 'imported-session.jsonl').write_text('{"sessionId": "new"}')

    # Create snapshot with backup
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    backup_dir = snapshot_dir / 'projects' / '-test-project'
    backup_dir.mkdir(parents=True)
    (backup_dir / 'original-session.jsonl').write_text('{"sessionId": "original"}')

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': str(target_dir),
        'backup_exists': True
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    # Perform restore
    result = restore_snapshot(force=True)

    assert result['restored'] is True
    assert target_dir.exists()
    assert (target_dir / 'original-session.jsonl').exists()
    assert not (target_dir / 'imported-session.jsonl').exists()
    assert not snapshot_dir.exists()  # Snapshot should be cleaned up


def test_restore_snapshot_cleans_up_snapshot(tmp_path, monkeypatch):
    """Should delete snapshot directory after successful restore."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create snapshot
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    target_dir = fake_home / '.claude' / 'projects' / '-test-project'

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': str(target_dir),
        'backup_exists': False
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    # Perform restore
    restore_snapshot(force=True)

    # Snapshot should be deleted
    assert not snapshot_dir.exists()


# =============================================================================
# Edge Cases
# =============================================================================

def test_get_snapshot_info_calculates_age(tmp_path, monkeypatch):
    """Should calculate snapshot age in hours."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create snapshot with timestamp 2 hours ago
    from datetime import datetime, timezone, timedelta
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    info = {
        'timestamp': two_hours_ago.isoformat().replace('+00:00', 'Z'),
        'target_directory': '/test',
        'backup_exists': False
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    result = get_snapshot_info()

    assert result['age_hours'] is not None
    assert 1.9 < result['age_hours'] < 2.1  # Approximately 2 hours


def test_restore_cancelled_without_force(tmp_path, monkeypatch):
    """Should return cancelled when not confirmed (simulated)."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create snapshot
    snapshot_dir = fake_home / '.claude-session-imports' / 'pre-import-snapshot'
    snapshot_dir.mkdir(parents=True)

    info = {
        'timestamp': '2026-01-06T12:00:00Z',
        'target_directory': str(fake_home / '.claude' / 'projects' / '-test'),
        'backup_exists': False
    }

    with open(snapshot_dir / 'snapshot_info.json', 'w') as f:
        json.dump(info, f)

    # Mock input to return wrong confirmation
    monkeypatch.setattr('builtins.input', lambda: 'WRONG')

    result = restore_snapshot(force=False)

    assert result['restored'] is False
    assert result['reason'] == 'cancelled'
    assert snapshot_dir.exists()  # Should NOT be deleted
