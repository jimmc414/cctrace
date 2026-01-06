#!/usr/bin/env python3
"""
Claude Code Session Import Tool

Imports a cctrace session export into Claude Code, enabling session resumption.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
import uuid

# Version for compatibility checking
CCTRACE_VERSION = "2.0.0"


def get_normalized_project_dir(project_path):
    """Get the normalized Claude project directory name for a given path.

    Replicates Claude Code's path normalization:
    - / -> -
    - \\ -> -
    - : -> -
    - . -> -
    - _ -> -
    - Unix paths: prefix with -
    - Windows paths: no prefix
    """
    project_path = str(project_path)
    if os.name == 'nt':  # Windows
        project_dir_name = project_path.replace('\\', '-').replace(':', '-').replace('/', '-').replace('.', '-').replace('_', '-')
    else:  # Unix-like
        normalized_project_path = project_path.replace('\\', '/')
        project_dir_name = normalized_project_path.replace('/', '-').replace('.', '-').replace('_', '-')

    if project_dir_name.startswith('-'):
        project_dir_name = project_dir_name[1:]

    if os.name == 'nt':
        return project_dir_name
    else:
        return f'-{project_dir_name}'


def validate_manifest(export_path: Path) -> dict:
    """Validate .cctrace-manifest.json exists and is valid.

    Args:
        export_path: Path to the export directory

    Returns:
        dict: Parsed manifest content

    Raises:
        ImportError: If manifest is missing or invalid
    """
    manifest_path = export_path / '.cctrace-manifest.json'

    if not manifest_path.exists():
        raise ImportError(
            f"No .cctrace-manifest.json found in {export_path}.\n"
            "This does not appear to be a valid cctrace export."
        )

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ImportError(f"Invalid manifest JSON: {e}")

    # Validate required fields
    required_fields = ['cctrace_version', 'session_id', 'session_data']
    missing_fields = [f for f in required_fields if f not in manifest]

    if missing_fields:
        raise ImportError(
            f"Manifest validation failed:\n"
            f"  Missing required fields: {', '.join(missing_fields)}\n"
            "The export may be corrupted or manually modified."
        )

    return manifest


def check_version_compatibility(manifest: dict) -> tuple:
    """Check Claude Code version compatibility.

    Args:
        manifest: Parsed manifest dictionary

    Returns:
        tuple: (is_compatible: bool, warning_message: str or None)
    """
    # Get current Claude Code version
    try:
        import subprocess
        result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
        current_version = result.stdout.strip().split()[-1] if result.returncode == 0 else None
    except:
        current_version = None

    export_version = manifest.get('claude_code_version')

    if not current_version:
        return True, "Could not determine current Claude Code version."

    if not export_version:
        return True, "Export manifest does not specify Claude Code version."

    if current_version != export_version:
        return True, (
            f"Version mismatch detected:\n"
            f"  Session created with: Claude Code {export_version}\n"
            f"  Your version: Claude Code {current_version}\n"
            "Proceeding may have compatibility issues."
        )

    return True, None


def generate_new_session_id() -> str:
    """Generate a new UUID for the imported session."""
    return str(uuid.uuid4())


def generate_new_agent_id() -> str:
    """Generate a new short agent ID (7 hex characters)."""
    return uuid.uuid4().hex[:7]


def regenerate_message_uuids(messages: list, new_session_id: str, new_cwd: str) -> list:
    """Regenerate all UUIDs while maintaining parent references.

    Args:
        messages: List of message dictionaries from JSONL
        new_session_id: New session UUID
        new_cwd: New working directory path

    Returns:
        list: Messages with updated UUIDs
    """
    # Create mapping from old UUIDs to new UUIDs
    uuid_mapping = {}
    new_agent_id = generate_new_agent_id()

    # First pass: generate new UUIDs for all messages
    for msg in messages:
        if 'uuid' in msg:
            old_uuid = msg['uuid']
            if old_uuid not in uuid_mapping:
                uuid_mapping[old_uuid] = str(uuid.uuid4())

    # Second pass: update all references
    updated_messages = []
    for msg in messages:
        updated_msg = msg.copy()

        # Update sessionId
        if 'sessionId' in updated_msg:
            updated_msg['sessionId'] = new_session_id

        # Update uuid
        if 'uuid' in updated_msg:
            updated_msg['uuid'] = uuid_mapping.get(updated_msg['uuid'], updated_msg['uuid'])

        # Update parentUuid reference
        if 'parentUuid' in updated_msg and updated_msg['parentUuid']:
            updated_msg['parentUuid'] = uuid_mapping.get(
                updated_msg['parentUuid'],
                updated_msg['parentUuid']
            )

        # Update agentId
        if 'agentId' in updated_msg:
            updated_msg['agentId'] = new_agent_id

        # Update cwd
        if 'cwd' in updated_msg:
            updated_msg['cwd'] = new_cwd

        # Keep slug unchanged (per user preference)

        # DO NOT modify:
        # - message.id (Anthropic message ID)
        # - requestId (Anthropic request ID)
        # - signature in thinking blocks
        # - tool_use.id (tool invocation ID)
        # - timestamp (historical record)
        # - thinking block text content

        updated_messages.append(updated_msg)

    return updated_messages


def get_target_directory(project_path: Path) -> Path:
    """Get ~/.claude/projects/<normalized-path>/ for the given project.

    Args:
        project_path: Path to the target project

    Returns:
        Path: Target directory for session files
    """
    normalized_dir = get_normalized_project_dir(str(project_path))
    return Path.home() / '.claude' / 'projects' / normalized_dir


def create_snapshot(target_dir: Path, import_storage_dir: Path) -> Path:
    """Create pre-import backup of the target directory.

    Args:
        target_dir: Directory to backup
        import_storage_dir: Base directory for import storage

    Returns:
        Path: Path to the snapshot directory
    """
    snapshot_dir = import_storage_dir / 'pre-import-snapshot'

    # Remove old snapshot if exists
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Backup target directory if it exists
    if target_dir.exists():
        target_backup = snapshot_dir / 'projects' / target_dir.name
        target_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target_dir, target_backup)

    # Record snapshot timestamp
    with open(snapshot_dir / 'snapshot_info.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'target_directory': str(target_dir),
            'backup_exists': target_dir.exists()
        }, f, indent=2)

    return snapshot_dir


def write_session_file(messages: list, target_path: Path) -> None:
    """Write processed JSONL to target location.

    Args:
        messages: List of message dictionaries
        target_path: Path to write the session file

    Raises:
        FileExistsError: If target file already exists
    """
    if target_path.exists():
        raise FileExistsError(
            f"Session file already exists: {target_path}\n"
            "Import aborted to prevent data loss."
        )

    # Create parent directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSONL
    with open(target_path, 'w', encoding='utf-8') as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')


def import_file_history(export_path: Path, manifest: dict, new_session_id: str) -> int:
    """Import file history snapshots to ~/.claude/file-history/<sessionId>/.

    Args:
        export_path: Path to the export directory
        manifest: Parsed manifest dictionary
        new_session_id: New session UUID

    Returns:
        int: Number of files imported
    """
    file_history_list = manifest.get('session_data', {}).get('file_history', [])
    if not file_history_list:
        return 0

    # Target directory
    target_dir = Path.home() / '.claude' / 'file-history' / new_session_id
    target_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for fh_relative in file_history_list:
        source_path = export_path / fh_relative
        if source_path.exists():
            target_path = target_dir / source_path.name
            shutil.copy2(source_path, target_path)
            count += 1

    return count


def import_todos(export_path: Path, manifest: dict, new_session_id: str, old_session_id: str) -> int:
    """Import todos to ~/.claude/todos/.

    Args:
        export_path: Path to the export directory
        manifest: Parsed manifest dictionary
        new_session_id: New session UUID
        old_session_id: Original session UUID

    Returns:
        int: Number of todo files imported
    """
    todos_path = manifest.get('session_data', {}).get('todos')
    if not todos_path:
        return 0

    source_path = export_path / todos_path
    if not source_path.exists():
        return 0

    # Target directory
    target_dir = Path.home() / '.claude' / 'todos'
    target_dir.mkdir(parents=True, exist_ok=True)

    # Read and update session ID in todos
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            todos = json.load(f)
    except:
        return 0

    # Write with new session ID in filename
    target_path = target_dir / f'{new_session_id}-todos.json'
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(todos, f, indent=2)

    return 1


def import_plan(export_path: Path, manifest: dict) -> bool:
    """Import plan file to ~/.claude/plans/<slug>.md.

    Args:
        export_path: Path to the export directory
        manifest: Parsed manifest dictionary

    Returns:
        bool: True if plan was imported
    """
    plan_path = manifest.get('session_data', {}).get('plan_file')
    if not plan_path:
        return False

    source_path = export_path / plan_path
    if not source_path.exists():
        return False

    # Get slug from manifest
    slug = manifest.get('session_slug')
    if not slug:
        return False

    # Target directory
    target_dir = Path.home() / '.claude' / 'plans'
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f'{slug}.md'

    # Don't overwrite existing plan
    if target_path.exists():
        print(f"  ⚠️  Plan file already exists: {target_path}")
        return False

    shutil.copy2(source_path, target_path)
    return True


def import_config(export_path: Path, manifest: dict, project_path: Path) -> dict:
    """Import config files to project .claude/ directory.

    Args:
        export_path: Path to the export directory
        manifest: Parsed manifest dictionary
        project_path: Target project path

    Returns:
        dict: Summary of imported files
    """
    summary = {
        'commands': 0,
        'skills': 0,
        'hooks': 0,
        'agents': 0,
        'rules': 0,
        'conflicts': []
    }

    config_snapshot = manifest.get('config_snapshot', {})
    project_claude_dir = project_path / '.claude'

    # Helper function to import config files
    def import_config_files(config_type: str, subdir: str):
        files = config_snapshot.get(config_type, [])
        if not files:
            return

        target_dir = project_claude_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        for relative_path in files:
            source_path = export_path / relative_path
            if not source_path.exists():
                continue

            target_path = target_dir / source_path.name

            if target_path.exists():
                summary['conflicts'].append(str(target_path))
            else:
                shutil.copy2(source_path, target_path)
                summary[config_type] += 1

    # Import each config type
    import_config_files('commands', 'commands')
    import_config_files('skills', 'skills')
    import_config_files('hooks', 'hooks')
    import_config_files('agents', 'agents')
    import_config_files('rules', 'rules')

    # Settings - skip (too risky to merge)
    # settings_path = config_snapshot.get('settings')
    # Skipped intentionally

    return summary


def add_claude_md_note(project_path: Path, manifest: dict) -> None:
    """Append import context section to CLAUDE.md.

    Args:
        project_path: Target project path
        manifest: Parsed manifest dictionary
    """
    claude_md_path = project_path / 'CLAUDE.md'

    # Prepare import context note
    original_context = manifest.get('original_context', {})
    note = f"""

## Imported Session Context

This session was imported via cctrace from another environment.

**Original environment:**
- User: {original_context.get('user', 'Unknown')}
- Path: {original_context.get('repo_path', 'Unknown')}
- Platform: {original_context.get('platform', 'Unknown')}
- Exported: {manifest.get('export_timestamp', 'Unknown')}
- Session ID: {manifest.get('session_id', 'Unknown')}

Some paths in the conversation history may reference the original environment.
"""

    if claude_md_path.exists():
        # Append to existing file
        with open(claude_md_path, 'a', encoding='utf-8') as f:
            f.write(note)
    else:
        # Create new file
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(f"# CLAUDE.md\n{note}")


def log_import(import_storage_dir: Path, manifest: dict, new_session_id: str,
               target_path: Path, summary: dict) -> Path:
    """Log import details for recovery.

    Args:
        import_storage_dir: Base directory for import storage
        manifest: Parsed manifest dictionary
        new_session_id: New session UUID
        target_path: Path to imported session file
        summary: Import summary dictionary

    Returns:
        Path: Path to the import log
    """
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    log_dir = import_storage_dir / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)

    log_content = {
        'import_timestamp': datetime.utcnow().isoformat() + 'Z',
        'original_session_id': manifest.get('session_id'),
        'new_session_id': new_session_id,
        'original_export_name': manifest.get('export_name'),
        'target_session_file': str(target_path),
        'summary': summary
    }

    log_path = log_dir / 'import.log'
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_content, f, indent=2)

    # Update index
    index_path = import_storage_dir / 'index.json'
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {'last_snapshot_taken': None, 'imports': {}}

    index['imports'][timestamp] = {
        'session_name': manifest.get('export_name'),
        'source_path': str(target_path.parent),
        'imported_at': log_content['import_timestamp']
    }
    index['last_snapshot_taken'] = datetime.utcnow().isoformat() + 'Z'

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    return log_path


def read_session_jsonl(session_path: Path) -> list:
    """Read messages from a session JSONL file.

    Args:
        session_path: Path to the JSONL file

    Returns:
        list: List of message dictionaries
    """
    messages = []
    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def import_session(export_path: Path, project_path: Path = None,
                   preserve_session_id: bool = False,
                   skip_config: bool = False,
                   skip_auxiliary: bool = False,
                   non_interactive: bool = False) -> dict:
    """Main import orchestrator.

    Args:
        export_path: Path to the export directory
        project_path: Target project path (default: current directory)
        preserve_session_id: Keep original session ID
        skip_config: Don't import config files
        skip_auxiliary: Don't import file-history/todos/plan
        non_interactive: No prompts

    Returns:
        dict: Import summary
    """
    if project_path is None:
        project_path = Path.cwd()

    project_path = Path(project_path).resolve()
    export_path = Path(export_path).resolve()

    print(f"🔍 Validating export at: {export_path}")

    # 1. Validate manifest
    manifest = validate_manifest(export_path)
    print(f"✓ Valid cctrace export (v{manifest.get('cctrace_version', 'unknown')})")

    original_context = manifest.get('original_context', {})
    print(f"✓ Exported by: {original_context.get('user', 'Unknown')}")
    print(f"✓ Original platform: {original_context.get('platform', 'Unknown')}")

    # 2. Check version compatibility
    is_compatible, warning = check_version_compatibility(manifest)
    if warning:
        print(f"⚠️  {warning}")
        if not non_interactive:
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                print("Import aborted.")
                return None

    # 3. Check for conflicts
    target_dir = get_target_directory(project_path)
    old_session_id = manifest.get('session_id')

    if preserve_session_id:
        new_session_id = old_session_id
        target_session_path = target_dir / f'{new_session_id}.jsonl'

        if target_session_path.exists():
            raise FileExistsError(
                f"Session ID {new_session_id} already exists locally.\n"
                "Import aborted. Options:\n"
                "  - Use default import (generates new session ID)\n"
                "  - Manually delete existing session at {target_session_path}"
            )
    else:
        new_session_id = generate_new_session_id()
        target_session_path = target_dir / f'{new_session_id}.jsonl'

    print(f"\n📥 Importing as session: {new_session_id}")
    if old_session_id != new_session_id:
        print(f"   (Original: {old_session_id})")

    # 4. Create pre-import snapshot
    import_storage_dir = Path.home() / '.claude-session-imports'
    import_storage_dir.mkdir(parents=True, exist_ok=True)

    print("\n📸 Creating pre-import snapshot...")
    snapshot_path = create_snapshot(target_dir, import_storage_dir)
    print(f"   Snapshot saved to: {snapshot_path}")

    # 5. Process session
    print("\n📝 Processing session...")

    # Find session file - prefer session/main.jsonl, fallback to raw_messages.jsonl
    session_data = manifest.get('session_data', {})
    main_session_path = session_data.get('main_session')

    source_session_path = None
    if main_session_path:
        source_session_path = export_path / main_session_path
    if not source_session_path or not source_session_path.exists():
        source_session_path = export_path / 'raw_messages.jsonl'

    if not source_session_path.exists():
        raise FileNotFoundError(f"Session file not found in export: {export_path}")

    messages = read_session_jsonl(source_session_path)
    print(f"   Read {len(messages)} messages")

    # Regenerate UUIDs unless preserving
    if not preserve_session_id:
        messages = regenerate_message_uuids(messages, new_session_id, str(project_path))
        print(f"   Regenerated UUIDs and updated cwd")
    else:
        # Still need to update cwd
        for msg in messages:
            if 'cwd' in msg:
                msg['cwd'] = str(project_path)

    # 6. Write session file
    print(f"\n💾 Writing session file...")
    write_session_file(messages, target_session_path)
    print(f"   ✓ Wrote session to: {target_session_path}")

    # 7. Import auxiliary files
    summary = {
        'session_file': str(target_session_path),
        'file_history_count': 0,
        'todos_imported': False,
        'plan_imported': False,
        'config': {}
    }

    if not skip_auxiliary:
        print(f"\n📦 Importing auxiliary files...")

        # File history
        fh_count = import_file_history(export_path, manifest, new_session_id)
        summary['file_history_count'] = fh_count
        print(f"   ✓ File history: {fh_count} snapshots")

        # Todos
        todos_imported = import_todos(export_path, manifest, new_session_id, old_session_id)
        summary['todos_imported'] = todos_imported > 0
        print(f"   ✓ Todos: {'imported' if todos_imported else 'none'}")

        # Plan
        plan_imported = import_plan(export_path, manifest)
        summary['plan_imported'] = plan_imported
        print(f"   ✓ Plan: {'imported' if plan_imported else 'skipped/none'}")

    # 8. Import config files
    if not skip_config:
        print(f"\n⚙️  Importing config files...")
        config_summary = import_config(export_path, manifest, project_path)
        summary['config'] = config_summary

        total_config = sum([
            config_summary['commands'],
            config_summary['skills'],
            config_summary['hooks'],
            config_summary['agents'],
            config_summary['rules']
        ])

        if total_config > 0:
            print(f"   ✓ Imported {total_config} config files:")
            if config_summary['commands']:
                print(f"      - {config_summary['commands']} commands")
            if config_summary['skills']:
                print(f"      - {config_summary['skills']} skills")
            if config_summary['hooks']:
                print(f"      - {config_summary['hooks']} hooks")
            if config_summary['agents']:
                print(f"      - {config_summary['agents']} agents")
            if config_summary['rules']:
                print(f"      - {config_summary['rules']} rules")

        if config_summary['conflicts']:
            print(f"   ⚠️  Skipped {len(config_summary['conflicts'])} files (already exist)")

    # 9. Add CLAUDE.md note
    print(f"\n📝 Adding import context to CLAUDE.md...")
    add_claude_md_note(project_path, manifest)
    print(f"   ✓ Updated CLAUDE.md")

    # 10. Log import
    log_path = log_import(import_storage_dir, manifest, new_session_id,
                          target_session_path, summary)

    print(f"\n✅ Import complete!")
    print(f"   Session: {manifest.get('session_slug', new_session_id[:8])}")
    print(f"   Session ID: {new_session_id}")
    print(f"   Log: {log_path}")
    print(f"\n💡 To continue this session:")
    print(f"   cd {project_path}")
    print(f"   claude -c")
    print(f"\n⚠️  If problems occur: python restore_backup.py")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Import a cctrace session export into Claude Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s .claude-sessions/my-session/
  %(prog)s exports/session-backup/ --preserve-session-id
  %(prog)s .claude-sessions/imported/ --skip-config --non-interactive
"""
    )

    parser.add_argument(
        'export_path',
        type=Path,
        help='Path to .claude-sessions/<name>/ directory'
    )

    parser.add_argument(
        '--project-path',
        type=Path,
        default=None,
        help='Target project path (default: current directory)'
    )

    parser.add_argument(
        '--preserve-session-id',
        action='store_true',
        help='Keep original session ID (fails on conflict)'
    )

    parser.add_argument(
        '--skip-config',
        action='store_true',
        help="Don't import config files (commands, skills, etc.)"
    )

    parser.add_argument(
        '--skip-auxiliary',
        action='store_true',
        help="Don't import file-history, todos, or plan"
    )

    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='No prompts, use defaults'
    )

    args = parser.parse_args()

    try:
        summary = import_session(
            export_path=args.export_path,
            project_path=args.project_path,
            preserve_session_id=args.preserve_session_id,
            skip_config=args.skip_config,
            skip_auxiliary=args.skip_auxiliary,
            non_interactive=args.non_interactive
        )

        if summary:
            return 0
        else:
            return 1

    except ImportError as e:
        print(f"❌ Import validation failed:\n   {e}")
        return 1
    except FileExistsError as e:
        print(f"❌ Conflict detected:\n   {e}")
        return 1
    except FileNotFoundError as e:
        print(f"❌ File not found:\n   {e}")
        return 1
    except Exception as e:
        print(f"❌ Import failed:\n   {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
