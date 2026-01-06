#!/usr/bin/env python3
"""
Claude Code Session Restore Tool

Restores from pre-import snapshot after a failed or unwanted import.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path


def get_import_storage_dir() -> Path:
    """Get the import storage directory path."""
    return Path.home() / '.claude-session-imports'


def get_snapshot_dir() -> Path:
    """Get the pre-import snapshot directory path."""
    return get_import_storage_dir() / 'pre-import-snapshot'


def get_snapshot_info() -> dict:
    """Get information about the current pre-import snapshot.

    Returns:
        dict: Snapshot information including:
            - exists: bool - Whether a snapshot exists
            - timestamp: str - When the snapshot was created (ISO format)
            - target_directory: str - The directory that was backed up
            - backup_exists: bool - Whether the snapshot contains actual backup data
            - backup_path: str - Path to the backup content (if exists)
            - age_hours: float - Hours since snapshot was created

    Raises:
        FileNotFoundError: If no snapshot exists
    """
    snapshot_dir = get_snapshot_dir()
    info_path = snapshot_dir / 'snapshot_info.json'

    if not info_path.exists():
        raise FileNotFoundError(
            "No pre-import snapshot found.\n"
            "A snapshot is only created when you run import_session.py.\n"
            f"Expected location: {snapshot_dir}"
        )

    with open(info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)

    # Calculate age
    try:
        snapshot_time = datetime.fromisoformat(info['timestamp'].replace('Z', '+00:00'))
        now = datetime.now(snapshot_time.tzinfo)
        age_hours = (now - snapshot_time).total_seconds() / 3600
    except:
        age_hours = None

    # Check for backup content
    backup_path = None
    if info.get('backup_exists'):
        target_dir = Path(info['target_directory'])
        backup_path = snapshot_dir / 'projects' / target_dir.name
        if not backup_path.exists():
            backup_path = None

    return {
        'exists': True,
        'timestamp': info.get('timestamp'),
        'target_directory': info.get('target_directory'),
        'backup_exists': info.get('backup_exists', False),
        'backup_path': str(backup_path) if backup_path else None,
        'age_hours': age_hours
    }


def get_last_import_info() -> dict:
    """Get information about the most recent import.

    Returns:
        dict: Import information or None if no imports recorded
    """
    index_path = get_import_storage_dir() / 'index.json'

    if not index_path.exists():
        return None

    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    imports = index.get('imports', {})
    if not imports:
        return None

    # Get the most recent import
    latest_key = max(imports.keys())
    latest = imports[latest_key]

    return {
        'import_id': latest_key,
        'session_name': latest.get('session_name'),
        'source_path': latest.get('source_path'),
        'imported_at': latest.get('imported_at')
    }


def restore_snapshot(force: bool = False) -> dict:
    """Restore from pre-import snapshot.

    This is a DESTRUCTIVE operation that:
    1. Removes the current state of the target directory
    2. Restores the pre-import state (or leaves empty if no prior content)

    Args:
        force: Skip confirmation prompt (DANGEROUS)

    Returns:
        dict: Restore summary

    Raises:
        FileNotFoundError: If no snapshot exists
        RuntimeError: If restore fails
    """
    snapshot_info = get_snapshot_info()
    target_dir = Path(snapshot_info['target_directory'])
    snapshot_dir = get_snapshot_dir()

    # Show what will happen
    print("\n" + "=" * 60)
    print("⚠️  PRE-IMPORT SNAPSHOT RESTORE")
    print("=" * 60)
    print(f"\nSnapshot created: {snapshot_info['timestamp']}")
    if snapshot_info['age_hours'] is not None:
        print(f"Snapshot age: {snapshot_info['age_hours']:.1f} hours ago")
    print(f"\nTarget directory: {target_dir}")

    if snapshot_info['backup_exists']:
        print(f"\nRestore action: REPLACE current content with snapshot backup")
        print(f"Backup location: {snapshot_info['backup_path']}")
    else:
        print(f"\nRestore action: DELETE imported content (directory was empty before)")

    # Show what will be lost
    last_import = get_last_import_info()
    if last_import:
        print(f"\nMost recent import:")
        print(f"  - Session: {last_import['session_name']}")
        print(f"  - Imported: {last_import['imported_at']}")

    # List current session files that will be affected
    if target_dir.exists():
        session_files = list(target_dir.glob('*.jsonl'))
        if session_files:
            print(f"\nSession files that will be affected ({len(session_files)}):")
            for sf in session_files[:5]:
                print(f"  - {sf.name}")
            if len(session_files) > 5:
                print(f"  ... and {len(session_files) - 5} more")

    print("\n" + "-" * 60)
    print("⚠️  WARNING: This operation is DESTRUCTIVE and IRREVERSIBLE!")
    print("    Any sessions created AFTER the import will be LOST.")
    print("-" * 60)

    # Confirmation
    if not force:
        print("\nTo proceed, type 'RESTORE' (all caps): ", end='')
        confirmation = input().strip()

        if confirmation != 'RESTORE':
            print("\n❌ Restore cancelled. You typed:", repr(confirmation))
            return {'restored': False, 'reason': 'cancelled'}

    # Perform restore
    print("\n🔄 Restoring...")

    try:
        if snapshot_info['backup_exists'] and snapshot_info['backup_path']:
            backup_path = Path(snapshot_info['backup_path'])

            # Remove current target directory
            if target_dir.exists():
                shutil.rmtree(target_dir)
                print(f"   ✓ Removed current: {target_dir}")

            # Restore from backup
            shutil.copytree(backup_path, target_dir)
            print(f"   ✓ Restored from: {backup_path}")

        else:
            # No prior content - just delete the target directory
            if target_dir.exists():
                shutil.rmtree(target_dir)
                print(f"   ✓ Removed: {target_dir}")
            else:
                print(f"   ✓ Directory already empty: {target_dir}")

        # Clean up snapshot after successful restore
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
            print(f"   ✓ Cleaned up snapshot")

        print("\n✅ Restore complete!")
        print("   The state before the import has been restored.")

        return {
            'restored': True,
            'target_directory': str(target_dir),
            'had_backup': snapshot_info['backup_exists']
        }

    except Exception as e:
        print(f"\n❌ Restore failed: {e}")
        print("   The snapshot has NOT been deleted.")
        print("   You may need to manually restore from:")
        print(f"   {snapshot_dir}")
        raise RuntimeError(f"Restore failed: {e}")


def show_info():
    """Display snapshot information without restoring."""
    try:
        info = get_snapshot_info()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1

    print("\n📸 Pre-Import Snapshot Information")
    print("=" * 50)
    print(f"Snapshot exists: Yes")
    print(f"Created: {info['timestamp']}")
    if info['age_hours'] is not None:
        print(f"Age: {info['age_hours']:.1f} hours")
    print(f"\nTarget directory: {info['target_directory']}")
    print(f"Had existing content: {'Yes' if info['backup_exists'] else 'No'}")

    if info['backup_path']:
        print(f"Backup location: {info['backup_path']}")
        # Show backup contents
        backup_path = Path(info['backup_path'])
        if backup_path.exists():
            session_files = list(backup_path.glob('*.jsonl'))
            print(f"\nBackup contains {len(session_files)} session file(s)")

    last_import = get_last_import_info()
    if last_import:
        print(f"\nMost recent import:")
        print(f"  Session: {last_import['session_name']}")
        print(f"  Imported: {last_import['imported_at']}")

    print(f"\nTo restore: python restore_backup.py --restore")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Restore from pre-import snapshot after a failed or unwanted import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Show snapshot information
  %(prog)s --restore    # Restore from snapshot (requires confirmation)
  %(prog)s --restore --yes  # Restore without confirmation (DANGEROUS)

Safety:
  - A snapshot is created automatically before each import
  - Each new import overwrites the previous snapshot
  - After restoring, the snapshot is deleted
  - This operation is IRREVERSIBLE - any post-import sessions will be lost
"""
    )

    parser.add_argument(
        '--restore',
        action='store_true',
        help='Perform the restore operation (requires confirmation)'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt (DANGEROUS - for automation only)'
    )

    args = parser.parse_args()

    try:
        if args.restore:
            result = restore_snapshot(force=args.yes)
            return 0 if result.get('restored') else 1
        else:
            return show_info()

    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    except RuntimeError as e:
        print(f"❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n❌ Restore cancelled by user.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
