# Claude Code Trace

A command-line tool that exports Claude Code chat sessions with conversation history, internal reasoning blocks, tool usage, and comprehensive metadata in XML and in markdown.

## Features

- **Automatic Session Detection**: Intelligently identifies your current Claude Code session, returns the session id, transcript and all session metadata, even with multiple concurrent sessions.
- **Complete Export**: Captures all messages, thinking blocks, tool uses, and responses
- **PID Cross Reference Validation**: Cross reference PID to ensure the correct session is exported
- **Multiple Output Formats**: Generates Markdown, JSON, and raw JSONL files
- **Session Statistics**: Provides detailed metrics about your conversation
- **Slash Command Integration**: Export directly from Claude Code with `/export`
- **Timestamped Archives**: Each export is saved with timestamp and session ID
- **Auto-Copy to Working Directory**: Automatically copies export to your current directory (configurable)

![image](https://github.com/user-attachments/assets/b316bd46-94f0-44ef-8030-e73b393cb119)

![image](https://github.com/user-attachments/assets/5c3ff16a-7470-408c-87de-a6a1aabd33b3)



## Requirements

- Python 3.6 or higher
- Claude Code running on Linux or WSL
- Access to `~/.claude/projects/` directory

### Optional Dependencies

- **jq** - Required for hook scripts to parse Claude environment variables
  - Install on Ubuntu/Debian: `sudo apt-get install jq`
  - Install on macOS: `brew install jq`
- **pytest** - Required only for running unit tests
  - Install: `pip install pytest` or `pip install -r requirements.txt`

## Quick Start

```bash
# Clone or download this repository
git clone https://github.com/jimmc414/cctrace.git
cd cctrace

# Run the installer
chmod +x setup.sh
./setup.sh

# Use in Claude Code
/user:export
# Or
/export
```

## Installation

### Automated Installation

1. Run the installation script:
   ```bash
   ./setup.sh
   ```

2. The installer will:
   - Create necessary directories
   - Copy files to appropriate locations
   - Set up the slash command
   - Verify the installation

### Manual Installation

1. Copy the export script:
   ```bash
   mkdir -p ~/claude_sessions
   cp export_claude_session.py ~/claude_sessions/
   chmod +x ~/claude_sessions/export_claude_session.py
   ```

2. Install the slash command:
   ```bash
   mkdir -p ~/.claude/commands
   cp export.md ~/.claude/commands/
   ```

## Usage

### Using the Slash Command (Recommended)

In any Claude Code session, simply type:
```
/user:export
```
or 
```
/export
```

This will:
1. Automatically detect your current session
2. Export all conversation data
3. Display a summary directly in Claude Code

### Using the Command Line

```bash
# Export current active session
python3 ~/claude_sessions/export_claude_session.py

# Export with custom options
python3 ~/claude_sessions/export_claude_session.py --max-age 600

# Export specific session by ID
python3 ~/claude_sessions/export_claude_session.py --session-id f33cdb42-0a41-40d4-91eb-c89c109af38a

# Export to custom directory
python3 ~/claude_sessions/export_claude_session.py --output-dir /path/to/exports
```

### Command Line Options

- `--session-id <uuid>`: Export a specific session by ID
- `--max-age <seconds>`: Set the maximum age for active session detection (default: 300)
- `--output-dir <path>`: Specify custom output directory
- `--format <md|xml|all>`: Choose output format (default: all)
- `--no-copy-to-cwd`: Do not copy export to current directory

## Export Contents

Each export creates a timestamped directory containing:

```
~/claude_sessions/exports/2025-07-02_16-45-00_f33cdb42/
├── session_info.json      # Complete session metadata including SESSION ID
├── conversation_full.md   # Human-readable conversation with all content
├── conversation_full.xml  # Fully labeled XML with complete metadata
├── raw_messages.jsonl     # Original JSONL data with all fields
└── summary.txt            # Quick overview with session ID and statistics
```

### Detailed File Contents

#### **session_info.json** - Complete Session Metadata
Contains ALL session metadata including:
- **Session ID** (unique identifier for your chat session)
- Project directory path
- Start and end timestamps
- Total message counts by type
- Models used
- Token usage statistics

Example:
```json
{
  "session_id": "f33cdb42-0a41-40d4-91eb-c89c109af38a",
  "project_dir": "/mnt/c/python/myproject",
  "start_time": "2025-07-02T20:06:59.614Z",
  "end_time": "2025-07-02T21:39:11.037Z",
  "total_messages": 145,
  "user_messages": 58,
  "assistant_messages": 87,
  "tool_uses": 42,
  "models_used": ["claude-opus-4-20250514"]
}
```

#### **conversation_full.xml** - Complete XML Export
Comprehensive XML format with FULL metadata labeling:
- **Session-level metadata**: Session ID, version, timestamps, working directory
- **Message-level metadata**: 
  - UUID and parent-UUID for message relationships
  - Event types and request IDs
  - Role (user/assistant) and model information
- **Content preservation**:
  - Text messages with proper encoding
  - Thinking blocks with cryptographic signatures
  - Tool uses with complete input/output data
  - Tool execution metadata (response codes, duration, bytes)
- **Token usage per message**: Input/output tokens, cache tokens, service tier

Example XML structure:
```xml
<claude-session xmlns="https://claude.ai/session-export/v1" export-version="1.0">
  <metadata>
    <session-id>f33cdb42-0a41-40d4-91eb-c89c109af38a</session-id>
    <working-directory>/mnt/c/python/myproject</working-directory>
    <start-time>2025-07-02T20:06:59.614Z</start-time>
    <export-time>2025-07-02T22:15:00.000Z</export-time>
  </metadata>
  <messages>
    <message uuid="492b16e4-af89-408f-b144-ae571d4047b5" 
             parent-uuid="null" 
             timestamp="2025-07-02T20:06:59.614Z">
      <role>user</role>
      <content>
        <text>Your message here</text>
      </content>
    </message>
    <message uuid="6892a3b3-63cf-4052-8f3f-850dca83d50c" 
             parent-uuid="492b16e4-af89-408f-b144-ae571d4047b5"
             timestamp="2025-07-02T20:07:07.357Z">
      <role>assistant</role>
      <model>claude-opus-4-20250514</model>
      <content>
        <thinking signature="Es0ICkYIBRgCKkCeXs4...">
          Internal reasoning content
        </thinking>
        <text>Assistant response</text>
        <tool-use id="toolu_01ABC..." name="Bash">
          <input>{"command": "ls -la", "description": "List files"}</input>
        </tool-use>
      </content>
      <usage>
        <input-tokens>1500</input-tokens>
        <output-tokens>750</output-tokens>
        <cache-creation-tokens>0</cache-creation-tokens>
        <service-tier>standard</service-tier>
      </usage>
    </message>
  </messages>
</claude-session>
```

#### **conversation_full.md** - Human-Readable Export
Markdown format including:
- Session ID prominently displayed at the top
- All user messages and assistant responses
- Collapsible thinking/reasoning blocks
- Tool usage with inputs and outputs
- Timestamps for each interaction

#### **raw_messages.jsonl** - Original Data
Complete, unmodified JSONL file containing:
- Every field from the original Claude Code session
- Session IDs, UUIDs, parent relationships
- All metadata exactly as stored by Claude Code
- Perfect for programmatic processing or analysis

#### **summary.txt** - Quick Reference
Plain text summary featuring:
- Session ID for easy reference
- Export timestamp
- Key statistics
- File locations

### Export Formats

By default, the tool exports **both** Markdown and XML formats to give you maximum flexibility.

#### Markdown (`--format md`)
Provides a clean, human-readable view of your conversation with collapsible sections for internal reasoning. Perfect for reviewing conversations and sharing with others.

#### XML (`--format xml`)
Preserves all available data fields in a structured format:
- Session metadata and statistics
- Message hierarchy with UUID relationships
- Complete tool usage information including execution times and response codes
- Thinking blocks with cryptographic signatures
- All token usage statistics
- Suitable for XSLT transformations and automated processing

#### All Formats (`--format all`) - **Default**
Generates both Markdown and XML outputs in the same export, giving you the best of both worlds:
- Human-readable Markdown for easy review
- Machine-parseable XML with complete data preservation

## Auto-Copy to Working Directory

By default, the export tool automatically copies the complete export folder to your current working directory with the name `claude_export_YYYY-MM-DD_HH-MM-SS_sessionid`. This makes it easy to:
- Include exports in your project repository
- Access exports without navigating to `~/claude_sessions/exports/`
- Keep exports with the relevant project code

### Disabling Auto-Copy

You can disable this feature in three ways:

1. **Command line flag:**
   ```bash
   python3 export_claude_session.py --no-copy-to-cwd
   ```

2. **Environment variable:**
   ```bash
   export CLAUDE_EXPORT_COPY_TO_CWD=false
   python3 export_claude_session.py
   ```

3. **In your shell configuration:**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export CLAUDE_EXPORT_COPY_TO_CWD=false
   ```

The copied folders are automatically excluded from git via the `.gitignore` pattern `claude_export_*/`.

## How It Works

### Session Detection Process

1. **Project Mapping**: Converts your current directory to Claude's naming convention
2. **Session Discovery**: Finds all JSONL files in `~/.claude/projects/<project-name>/`
3. **Active Session Detection**: Identifies sessions modified within the last 5 minutes
4. **PID Validation**: When multiple active sessions exist:
   - Detects the parent Claude process PID
   - Creates a temporary marker file
   - Identifies which session file responds to the marker
   - Ensures the correct session is exported

### Multiple Concurrent Sessions

The tool handles multiple Claude Code sessions running in the same directory by:
- Using process hierarchy to identify the calling Claude instance
- Employing file activity detection to correlate sessions
- Providing clear feedback about which session is being exported
- Falling back gracefully when automatic detection isn't possible

## Troubleshooting

### "No Claude Code sessions found"
- Ensure you're running from a directory with active Claude Code sessions
- Check that `~/.claude/projects/` exists and contains your project

### "Could not identify specific session"
- The tool will default to the most recently active session
- Use `--session-id` to manually specify a session
- Ensure the session file has been recently modified

### Permission Errors
- Verify you have read access to `~/.claude/projects/`
- Ensure write permissions for the export directory

### Session Not Updating
- Claude Code writes to JSONL files in real-time
- If a session appears stale, try sending a message to trigger an update


## Development

The tool uses only Python standard library modules for core functionality, making it dependency-free for basic usage.

### Running Tests

To run the test suite:
```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/
```

### Key Functions

- `get_parent_claude_pid()`: Detects if running inside Claude Code
- `identify_current_session()`: Correlates process with session file
- `parse_jsonl_file()`: Extracts and processes conversation data
- `format_message_markdown()`: Converts messages to readable format

### Platform Compatibility

- **Linux**: Fully supported
- **WSL (Windows Subsystem for Linux)**: Fully supported
- **macOS**: Core functionality works; hook scripts require `jq` installation
