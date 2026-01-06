---
description: Restore from pre-import snapshot after a failed or unwanted import
---

Restore the session state from before the last import. Use this if an import caused problems or you want to undo an import.

## Usage

```
/restore-backup
```

## What This Does

1. Shows information about the pre-import snapshot:
   - When it was created
   - What directory it protects
   - Whether there was existing content before import
2. Lists session files that will be affected
3. Requires typing "RESTORE" to confirm (safety measure)
4. Restores the pre-import state:
   - If there was existing content: restores it
   - If directory was empty: removes imported content
5. Deletes the snapshot after successful restore

## Important Notes

- **DESTRUCTIVE**: Any sessions created AFTER the import will be LOST
- **ONE SNAPSHOT**: Each import overwrites the previous snapshot
- **IRREVERSIBLE**: Once restored, cannot undo the restore

## Examples

Check snapshot status (no restore):
```
/restore-backup --info
```

Perform restore (will prompt for confirmation):
```
/restore-backup
```

## Implementation

Show snapshot info first:
```bash
python3 restore_backup.py
```

If user confirms, perform restore:
```bash
python3 restore_backup.py --restore
```

For the `--info` flag, just show info without prompting:
```bash
python3 restore_backup.py
```
