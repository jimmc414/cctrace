#!/usr/bin/env python3
"""
Claude Code Session Export Tool

Exports the current Claude Code session to a verbose output folder.
Automatically detects the active session based on recent modifications.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom
import html
import re
import uuid
import getpass

# Version for manifest
CCTRACE_VERSION = "2.0.0"

def clean_text_for_xml(text):
    """Remove or replace characters that cause XML parsing issues."""
    if not text:
        return text
    # Remove control characters except newline, tab, and carriage return
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', str(text))
    return text

def get_parent_claude_pid():
    """Get the PID of the parent Claude process if running inside Claude Code."""
    try:
        # Get parent PID of current process
        ppid = os.getppid()
        # Check if parent is a claude process
        result = subprocess.run(['ps', '-p', str(ppid), '-o', 'cmd='], 
                              capture_output=True, text=True)
        if 'claude' in result.stdout:
            return ppid
    except:
        pass
    return None

def identify_current_session(sessions, project_dir):
    """Try to identify which session belongs to the current Claude instance."""
    # If we're running inside Claude Code, create a temporary marker
    claude_pid = get_parent_claude_pid()
    if not claude_pid:
        return None
    
    print(f"📍 Current Claude Code PID: {claude_pid}")
    
    # First, refresh session modification times
    refreshed_sessions = []
    for session in sessions:
        stat = session['path'].stat()
        refreshed_sessions.append({
            'path': session['path'],
            'mtime': stat.st_mtime,
            'session_id': session['session_id']
        })
    
    # Create a unique marker file
    marker_content = f"claude_export_marker_{claude_pid}_{time.time()}"
    marker_file = Path(project_dir) / '.claude_export_marker'
    
    try:
        # Write marker file
        marker_file.write_text(marker_content)
        time.sleep(0.2)  # Give it a moment to register
        
        # Check which session file was modified after marker creation
        marker_mtime = marker_file.stat().st_mtime
        
        for session in refreshed_sessions:
            # Re-check modification time
            current_mtime = session['path'].stat().st_mtime
            if current_mtime > marker_mtime:
                print(f"✓ Session {session['session_id'][:8]}... was modified after marker creation")
                # Clean up marker
                marker_file.unlink(missing_ok=True)
                return session
        
        # Clean up marker
        marker_file.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️  Session identification failed: {e}")
        if marker_file.exists():
            marker_file.unlink(missing_ok=True)
    
    return None

def find_project_sessions(project_path):
    """Find all JSONL session files for the current project."""
    project_path = str(project_path)
    # Convert project path to Claude's directory naming convention
    # Claude normalizes project directories by replacing path separators, dots,
    # AND underscores in the working directory path with hyphens.
    # See: https://github.com/jimmc414/cctrace/issues/4

    # On Windows, paths include drive letters with colons (e.g., C:\, D:\)
    # that must be normalized differently than Unix paths
    if os.name == 'nt':  # Windows
        # Replace backslashes, colons, forward slashes, dots, and underscores with hyphens
        project_dir_name = project_path.replace('\\', '-').replace(':', '-').replace('/', '-').replace('.', '-').replace('_', '-')
    else:  # Unix-like (Linux, macOS)
        # Standard normalization for Unix paths
        normalized_project_path = project_path.replace('\\', '/')
        project_dir_name = normalized_project_path.replace('/', '-').replace('.', '-').replace('_', '-')

    if project_dir_name.startswith('-'):
        project_dir_name = project_dir_name[1:]

    claude_project_dir = Path.home() / '.claude' / 'projects'

    if os.name == 'nt':  # Windows
        claude_project_dir = claude_project_dir / project_dir_name
    else: # Unix-like (Linux, macOS)
        claude_project_dir = claude_project_dir / f'-{project_dir_name}'
    
    if not claude_project_dir.exists():
        return []
    
    # Get all JSONL files sorted by modification time
    jsonl_files = []
    for file in claude_project_dir.glob('*.jsonl'):
        stat = file.stat()
        jsonl_files.append({
            'path': file,
            'mtime': stat.st_mtime,
            'session_id': file.stem
        })
    
    return sorted(jsonl_files, key=lambda x: x['mtime'], reverse=True)

def find_active_session(sessions, max_age_seconds=300):
    """Find the most recently active session (modified within max_age_seconds)."""
    if not sessions:
        return None
    
    current_time = time.time()
    active_sessions = []
    
    for session in sessions:
        age = current_time - session['mtime']
        if age <= max_age_seconds:
            active_sessions.append(session)
    
    return active_sessions

def parse_jsonl_file(file_path):
    """Parse a JSONL file and extract all messages and metadata."""
    messages = []
    metadata = {
        'session_id': None,
        'start_time': None,
        'end_time': None,
        'project_dir': None,
        'total_messages': 0,
        'user_messages': 0,
        'assistant_messages': 0,
        'tool_uses': 0,
        'models_used': set()
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                messages.append(data)
                
                # Extract metadata
                if metadata['session_id'] is None and 'sessionId' in data:
                    metadata['session_id'] = data['sessionId']
                
                if 'cwd' in data and metadata['project_dir'] is None:
                    metadata['project_dir'] = data['cwd']
                
                if 'timestamp' in data:
                    timestamp = data['timestamp']
                    if metadata['start_time'] is None or timestamp < metadata['start_time']:
                        metadata['start_time'] = timestamp
                    if metadata['end_time'] is None or timestamp > metadata['end_time']:
                        metadata['end_time'] = timestamp
                
                # Count message types
                if 'message' in data and 'role' in data['message']:
                    role = data['message']['role']
                    if role == 'user':
                        metadata['user_messages'] += 1
                    elif role == 'assistant':
                        metadata['assistant_messages'] += 1
                        if 'model' in data['message']:
                            metadata['models_used'].add(data['message']['model'])
                
                # Count tool uses
                if 'message' in data and 'content' in data['message']:
                    for content in data['message']['content']:
                        if isinstance(content, dict) and content.get('type') == 'tool_use':
                            metadata['tool_uses'] += 1
                
            except json.JSONDecodeError:
                continue
    
    metadata['total_messages'] = len(messages)
    metadata['models_used'] = list(metadata['models_used'])
    
    return messages, metadata

def format_message_markdown(message_data):
    """Format a single message as markdown."""
    output = []
    
    if 'message' not in message_data:
        return ""
    
    msg = message_data['message']
    timestamp = message_data.get('timestamp', '')
    
    # Add timestamp
    if timestamp:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        output.append(f"**[{dt.strftime('%Y-%m-%d %H:%M:%S')}]**")
    
    # Add role header
    role = msg.get('role', 'unknown')
    if role == 'user':
        output.append("\n### 👤 User\n")
    elif role == 'assistant':
        model = msg.get('model', '')
        output.append(f"\n### 🤖 Assistant ({model})\n")
    
    # Process content
    if 'content' in msg:
        if isinstance(msg['content'], str):
            output.append(msg['content'])
        elif isinstance(msg['content'], list):
            for content in msg['content']:
                if isinstance(content, dict):
                    content_type = content.get('type')
                    
                    if content_type == 'text':
                        output.append(content.get('text', ''))
                    
                    elif content_type == 'thinking':
                        output.append("\n<details>")
                        output.append("<summary>💭 Internal Reasoning (click to expand)</summary>\n")
                        output.append("```")
                        output.append(content.get('thinking', ''))
                        output.append("```")
                        output.append("</details>\n")
                    
                    elif content_type == 'tool_use':
                        tool_name = content.get('name', 'unknown')
                        tool_id = content.get('id', '')
                        output.append(f"\n🔧 **Tool Use: {tool_name}** (ID: {tool_id})")
                        output.append("```json")
                        output.append(json.dumps(content.get('input', {}), indent=2))
                        output.append("```\n")
                    
                    elif content_type == 'tool_result':
                        output.append("\n📊 **Tool Result:**")
                        output.append("```")
                        result = content.get('content', '')
                        if isinstance(result, str):
                            output.append(result[:5000])  # Limit length
                            if len(result) > 5000:
                                output.append(f"\n... (truncated, {len(result) - 5000} chars omitted)")
                        else:
                            output.append(str(result))
                        output.append("```\n")
    
    return '\n'.join(output)

def format_message_xml(message_data, parent_element):
    """Format a single message as XML element."""
    msg_elem = ET.SubElement(parent_element, 'message')
    
    # Add attributes
    msg_elem.set('uuid', message_data.get('uuid', ''))
    if message_data.get('parentUuid'):
        msg_elem.set('parent-uuid', message_data['parentUuid'])
    msg_elem.set('timestamp', message_data.get('timestamp', ''))
    
    # Add metadata
    if 'type' in message_data:
        ET.SubElement(msg_elem, 'event-type').text = message_data['type']
    if 'cwd' in message_data:
        ET.SubElement(msg_elem, 'working-directory').text = message_data['cwd']
    if 'requestId' in message_data:
        ET.SubElement(msg_elem, 'request-id').text = message_data['requestId']
    
    # Process message content
    if 'message' in message_data:
        msg = message_data['message']
        
        # Add role
        if 'role' in msg:
            ET.SubElement(msg_elem, 'role').text = msg['role']
        
        # Add model info
        if 'model' in msg:
            ET.SubElement(msg_elem, 'model').text = msg['model']
        
        # Process content
        if 'content' in msg:
            content_elem = ET.SubElement(msg_elem, 'content')
            
            if isinstance(msg['content'], str):
                content_elem.text = msg['content']
            elif isinstance(msg['content'], list):
                for content in msg['content']:
                    if isinstance(content, dict):
                        content_type = content.get('type')
                        
                        if content_type == 'text':
                            text_elem = ET.SubElement(content_elem, 'text')
                            text_elem.text = clean_text_for_xml(content.get('text', ''))
                        
                        elif content_type == 'thinking':
                            thinking_elem = ET.SubElement(content_elem, 'thinking')
                            if 'signature' in content:
                                thinking_elem.set('signature', content['signature'])
                            thinking_elem.text = clean_text_for_xml(content.get('thinking', ''))
                        
                        elif content_type == 'tool_use':
                            tool_elem = ET.SubElement(content_elem, 'tool-use')
                            tool_elem.set('id', content.get('id', ''))
                            tool_elem.set('name', content.get('name', ''))
                            
                            input_elem = ET.SubElement(tool_elem, 'input')
                            input_elem.text = clean_text_for_xml(json.dumps(content.get('input', {}), indent=2))
                        
                        elif content_type == 'tool_result':
                            result_elem = ET.SubElement(content_elem, 'tool-result')
                            if 'tool_use_id' in content:
                                result_elem.set('tool-use-id', content['tool_use_id'])
                            
                            result_content = content.get('content', '')
                            if isinstance(result_content, str):
                                result_elem.text = clean_text_for_xml(result_content)
                            else:
                                result_elem.text = clean_text_for_xml(str(result_content))
        
        # Add usage info
        if 'usage' in msg:
            usage_elem = ET.SubElement(msg_elem, 'usage')
            usage = msg['usage']
            
            if 'input_tokens' in usage:
                ET.SubElement(usage_elem, 'input-tokens').text = str(usage['input_tokens'])
            if 'output_tokens' in usage:
                ET.SubElement(usage_elem, 'output-tokens').text = str(usage['output_tokens'])
            if 'cache_creation_input_tokens' in usage:
                ET.SubElement(usage_elem, 'cache-creation-tokens').text = str(usage['cache_creation_input_tokens'])
            if 'cache_read_input_tokens' in usage:
                ET.SubElement(usage_elem, 'cache-read-tokens').text = str(usage['cache_read_input_tokens'])
            if 'service_tier' in usage:
                ET.SubElement(usage_elem, 'service-tier').text = usage['service_tier']
    
    # Add tool result metadata if present
    if 'toolUseResult' in message_data:
        tool_result = message_data['toolUseResult']
        if isinstance(tool_result, dict):
            tool_meta = ET.SubElement(msg_elem, 'tool-execution-metadata')
            
            if 'bytes' in tool_result:
                ET.SubElement(tool_meta, 'response-bytes').text = str(tool_result['bytes'])
            if 'code' in tool_result:
                ET.SubElement(tool_meta, 'response-code').text = str(tool_result['code'])
            if 'codeText' in tool_result:
                ET.SubElement(tool_meta, 'response-text').text = tool_result['codeText']
            if 'durationMs' in tool_result:
                ET.SubElement(tool_meta, 'duration-ms').text = str(tool_result['durationMs'])
            if 'url' in tool_result:
                ET.SubElement(tool_meta, 'url').text = tool_result['url']

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    try:
        rough_string = ET.tostring(elem, encoding='unicode', method='xml')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    except Exception as e:
        # Fallback: return unprettified XML if pretty printing fails
        print(f"⚠️  XML prettification failed: {e}")
        return ET.tostring(elem, encoding='unicode', method='xml')


# ============================================================================
# NEW: Enhanced Export Functions
# ============================================================================

def get_normalized_project_dir(project_path):
    """Get the normalized Claude project directory name for a given path."""
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


def collect_agent_sessions(project_path, session_id, messages):
    """Collect all agent session files related to the main session.

    Returns dict with agent_id -> file_path mapping.
    """
    agents = {}

    # Find agent IDs referenced in the main session
    agent_ids = set()
    for msg in messages:
        if 'agentId' in msg:
            agent_id = msg['agentId']
            # Skip if this is the main session's own agent ID
            if agent_id and len(agent_id) == 7:  # Agent IDs are 7 chars
                agent_ids.add(agent_id)

    # Get the Claude project directory
    normalized_dir = get_normalized_project_dir(project_path)
    claude_project_dir = Path.home() / '.claude' / 'projects' / normalized_dir

    if not claude_project_dir.exists():
        return agents

    # Find agent session files
    for agent_file in claude_project_dir.glob('agent-*.jsonl'):
        agent_id = agent_file.stem.replace('agent-', '')
        # Check if this agent is referenced in our session
        if agent_id in agent_ids:
            # Verify session ID matches by checking first line
            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get('sessionId') == session_id:
                            agents[agent_id] = agent_file
            except:
                pass

    return agents


def collect_file_history(session_id):
    """Collect file history snapshots for a session.

    Returns list of file paths or empty list if none.
    """
    file_history_dir = Path.home() / '.claude' / 'file-history' / session_id

    if not file_history_dir.exists():
        return []

    files = []
    for f in file_history_dir.iterdir():
        if f.is_file():
            files.append(f)

    return files


def collect_plan_file(slug):
    """Collect plan file for a session by slug.

    Returns file path or None if not found.
    """
    if not slug:
        return None

    plan_file = Path.home() / '.claude' / 'plans' / f'{slug}.md'

    if plan_file.exists():
        return plan_file

    return None


def collect_todos(session_id):
    """Collect todo files for a session.

    Returns list of file paths or empty list if none.
    """
    todos_dir = Path.home() / '.claude' / 'todos'

    if not todos_dir.exists():
        return []

    files = []
    for f in todos_dir.glob(f'{session_id}-*.json'):
        files.append(f)

    return files


def collect_session_env(session_id):
    """Collect session environment data.

    Returns directory path if exists and non-empty, None otherwise.
    """
    session_env_dir = Path.home() / '.claude' / 'session-env' / session_id

    if session_env_dir.exists():
        # Check if directory has any files
        files = list(session_env_dir.iterdir())
        if files:
            return session_env_dir

    return None


def collect_project_config(project_path):
    """Collect project configuration files.

    Returns dict with config type -> list of file paths.
    """
    project_path = Path(project_path)
    config = {
        'commands': [],
        'skills': [],
        'hooks': [],
        'agents': [],
        'rules': [],
        'settings': None,
        'claude_md': None
    }

    # Check both .claude/ subdirectory and root-level directories
    claude_dir = project_path / '.claude'

    # Commands - check both locations
    for commands_dir in [claude_dir / 'commands', project_path / 'commands']:
        if commands_dir.exists():
            for f in commands_dir.glob('*.md'):
                config['commands'].append(f)

    # Skills
    skills_dir = claude_dir / 'skills'
    if skills_dir.exists():
        for f in skills_dir.glob('*.md'):
            config['skills'].append(f)

    # Hooks
    hooks_dir = claude_dir / 'hooks'
    if hooks_dir.exists():
        for f in hooks_dir.iterdir():
            if f.is_file():
                config['hooks'].append(f)

    # Agents
    agents_dir = claude_dir / 'agents'
    if agents_dir.exists():
        for f in agents_dir.glob('*.md'):
            config['agents'].append(f)

    # Rules
    rules_dir = claude_dir / 'rules'
    if rules_dir.exists():
        for f in rules_dir.glob('*.md'):
            config['rules'].append(f)

    # Settings (not settings.local.json)
    settings_file = claude_dir / 'settings.json'
    if settings_file.exists():
        config['settings'] = settings_file

    # CLAUDE.md
    claude_md = project_path / 'CLAUDE.md'
    if claude_md.exists():
        config['claude_md'] = claude_md

    return config


def generate_manifest(session_id, slug, export_name, metadata, messages,
                     session_files, config_files, project_path, anonymized=False):
    """Generate the .cctrace-manifest.json content."""

    # Get Claude Code version from first message
    claude_code_version = None
    for msg in messages:
        if 'version' in msg:
            claude_code_version = msg['version']
            break

    # Get git branch
    git_branch = None
    for msg in messages:
        if 'gitBranch' in msg:
            git_branch = msg['gitBranch']
            break

    manifest = {
        "cctrace_version": CCTRACE_VERSION,
        "export_timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "session_slug": slug,
        "export_name": export_name,
        "claude_code_version": claude_code_version,

        "original_context": {
            "user": getpass.getuser() if not anonymized else None,
            "platform": sys.platform,
            "repo_path": str(project_path),
            "git_branch": git_branch
        },

        "session_data": {
            "main_session": "session/main.jsonl",
            "agent_sessions": [f"session/agents/{Path(f).name}" for f in session_files.get('agents', {}).values()],
            "file_history": [f"session/file-history/{Path(f).name}" for f in session_files.get('file_history', [])],
            "plan_file": "session/plan.md" if session_files.get('plan') else None,
            "todos": "session/todos.json" if session_files.get('todos') else None,
            "session_env": "session/session-env/" if session_files.get('session_env') else None
        },

        "config_snapshot": {
            "commands": [f"config/commands/{Path(f).name}" for f in config_files.get('commands', [])],
            "skills": [f"config/skills/{Path(f).name}" for f in config_files.get('skills', [])],
            "hooks": [f"config/hooks/{Path(f).name}" for f in config_files.get('hooks', [])],
            "agents": [f"config/agents/{Path(f).name}" for f in config_files.get('agents', [])],
            "rules": [f"config/rules/{Path(f).name}" for f in config_files.get('rules', [])],
            "settings": "config/settings.json" if config_files.get('settings') else None,
            "claude_md": "config/CLAUDE.md" if config_files.get('claude_md') else None
        },

        "statistics": {
            "message_count": metadata['total_messages'],
            "user_messages": metadata['user_messages'],
            "assistant_messages": metadata['assistant_messages'],
            "tool_uses": metadata['tool_uses'],
            "duration_seconds": None,  # Could calculate from timestamps
            "models_used": metadata['models_used']
        }
    }

    # Calculate duration if we have timestamps
    if metadata.get('start_time') and metadata.get('end_time'):
        try:
            start = datetime.fromisoformat(metadata['start_time'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(metadata['end_time'].replace('Z', '+00:00'))
            manifest['statistics']['duration_seconds'] = int((end - start).total_seconds())
        except:
            pass

    if anonymized:
        manifest['original_context']['user'] = None
        manifest['anonymized'] = True

    return manifest


def generate_rendered_markdown(messages, metadata, manifest):
    """Generate RENDERED.md - a GitHub-optimized view of the session."""
    lines = []

    # Header
    lines.append(f"# Claude Code Session: {manifest['export_name']}")
    lines.append("")
    lines.append(f"> Exported from cctrace v{CCTRACE_VERSION}")
    lines.append("")

    # Session info table
    lines.append("## Session Info")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Session ID | `{manifest['session_id']}` |")
    if manifest['session_slug']:
        lines.append(f"| Session Name | {manifest['session_slug']} |")
    lines.append(f"| Project | `{manifest['original_context']['repo_path']}` |")
    if manifest['original_context']['git_branch']:
        lines.append(f"| Git Branch | `{manifest['original_context']['git_branch']}` |")
    lines.append(f"| Claude Code | v{manifest['claude_code_version']} |")
    lines.append(f"| Messages | {manifest['statistics']['message_count']} |")
    lines.append(f"| Tool Uses | {manifest['statistics']['tool_uses']} |")
    if manifest['statistics']['duration_seconds']:
        duration = manifest['statistics']['duration_seconds']
        if duration > 3600:
            duration_str = f"{duration // 3600}h {(duration % 3600) // 60}m"
        elif duration > 60:
            duration_str = f"{duration // 60}m {duration % 60}s"
        else:
            duration_str = f"{duration}s"
        lines.append(f"| Duration | {duration_str} |")
    lines.append(f"| Models | {', '.join(manifest['statistics']['models_used'])} |")
    lines.append("")

    # Session data summary
    lines.append("## Session Data")
    lines.append("")
    lines.append("| Component | Status |")
    lines.append("|-----------|--------|")
    lines.append(f"| Main Session | ✅ `session/main.jsonl` |")
    agent_count = len(manifest['session_data']['agent_sessions'])
    lines.append(f"| Agent Sessions | {'✅ ' + str(agent_count) + ' files' if agent_count else '➖ None'} |")
    fh_count = len(manifest['session_data']['file_history'])
    lines.append(f"| File History | {'✅ ' + str(fh_count) + ' snapshots' if fh_count else '➖ None'} |")
    lines.append(f"| Plan File | {'✅ Included' if manifest['session_data']['plan_file'] else '➖ None'} |")
    lines.append(f"| Todos | {'✅ Included' if manifest['session_data']['todos'] else '➖ None'} |")
    lines.append("")

    # Config summary
    lines.append("## Project Config")
    lines.append("")
    lines.append("| Component | Status |")
    lines.append("|-----------|--------|")
    cmd_count = len(manifest['config_snapshot']['commands'])
    lines.append(f"| Commands | {'✅ ' + str(cmd_count) + ' files' if cmd_count else '➖ None'} |")
    skill_count = len(manifest['config_snapshot']['skills'])
    lines.append(f"| Skills | {'✅ ' + str(skill_count) + ' files' if skill_count else '➖ None'} |")
    hook_count = len(manifest['config_snapshot']['hooks'])
    lines.append(f"| Hooks | {'✅ ' + str(hook_count) + ' files' if hook_count else '➖ None'} |")
    agent_cfg_count = len(manifest['config_snapshot']['agents'])
    lines.append(f"| Agents | {'✅ ' + str(agent_cfg_count) + ' files' if agent_cfg_count else '➖ None'} |")
    rule_count = len(manifest['config_snapshot']['rules'])
    lines.append(f"| Rules | {'✅ ' + str(rule_count) + ' files' if rule_count else '➖ None'} |")
    lines.append(f"| Settings | {'✅ Included' if manifest['config_snapshot']['settings'] else '➖ None'} |")
    lines.append(f"| CLAUDE.md | {'✅ Included' if manifest['config_snapshot']['claude_md'] else '➖ None'} |")
    lines.append("")

    # Conversation
    lines.append("---")
    lines.append("")
    lines.append("## Conversation")
    lines.append("")

    for msg in messages:
        formatted = format_message_markdown(msg)
        if formatted:
            lines.append(formatted)
            lines.append("")
            lines.append("---")
            lines.append("")

    return '\n'.join(lines)


def write_empty_marker(directory, message):
    """Write an _empty marker file in a directory."""
    marker_path = directory / '_empty'
    marker_path.write_text(message, encoding='utf-8')


def export_session_enhanced(session_info, project_path, export_name, output_dir=None,
                           output_format='all', anonymized=False, in_repo=True):
    """Export a session with the enhanced structure.

    Args:
        session_info: Session information dictionary
        project_path: Path to the project directory
        export_name: Name for the export folder
        output_dir: Output directory (default: .claude-sessions/ in project)
        output_format: Format to export ('md', 'xml', or 'all')
        anonymized: Whether to exclude user info
        in_repo: Whether to export to project repo (True) or legacy location (False)
    """
    project_path = Path(project_path)

    # Parse the session file
    messages, metadata = parse_jsonl_file(session_info['path'])

    # Get session ID and slug from messages
    session_id = metadata['session_id'] if metadata['session_id'] else session_info['session_id']
    slug = None
    for msg in messages:
        if 'slug' in msg:
            slug = msg['slug']
            break

    # Determine output directory
    if in_repo:
        if output_dir:
            export_dir = Path(output_dir) / export_name
        else:
            export_dir = project_path / '.claude-sessions' / export_name
    else:
        # Legacy location
        if output_dir:
            export_dir = Path(output_dir) / export_name
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            export_dir = Path.home() / 'claude_sessions' / 'exports' / f"{timestamp}_{session_id[:8]}"

    export_dir.mkdir(parents=True, exist_ok=True)

    # Collect all session data
    print("📦 Collecting session data...")

    agent_sessions = collect_agent_sessions(project_path, session_id, messages)
    file_history = collect_file_history(session_id)
    plan_file = collect_plan_file(slug)
    todos = collect_todos(session_id)
    session_env = collect_session_env(session_id)

    session_files = {
        'agents': agent_sessions,
        'file_history': file_history,
        'plan': plan_file,
        'todos': todos,
        'session_env': session_env
    }

    # Collect project config
    print("📦 Collecting project config...")
    config_files = collect_project_config(project_path)

    # Generate manifest
    manifest = generate_manifest(
        session_id, slug, export_name, metadata, messages,
        session_files, config_files, project_path, anonymized
    )

    # =========================================================================
    # Write legacy files (backwards compatibility)
    # =========================================================================
    print("📝 Writing legacy files...")

    # Save metadata (legacy format)
    metadata_path = export_dir / 'session_info.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    # Copy raw JSONL (legacy)
    raw_path = export_dir / 'raw_messages.jsonl'
    shutil.copy2(session_info['path'], raw_path)

    # Generate markdown conversation (legacy format)
    if output_format in ['md', 'all']:
        md_path = export_dir / 'conversation_full.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Claude Code Session Export\n\n")
            f.write(f"**Session ID:** `{metadata['session_id']}`\n")
            f.write(f"**Project:** `{metadata['project_dir']}`\n")
            f.write(f"**Start Time:** {metadata['start_time']}\n")
            f.write(f"**End Time:** {metadata['end_time']}\n")
            f.write(f"**Total Messages:** {metadata['total_messages']}\n")
            f.write(f"**User Messages:** {metadata['user_messages']}\n")
            f.write(f"**Assistant Messages:** {metadata['assistant_messages']}\n")
            f.write(f"**Tool Uses:** {metadata['tool_uses']}\n")
            f.write(f"**Models Used:** {', '.join(metadata['models_used'])}\n\n")
            f.write("---\n\n")

            for msg in messages:
                formatted = format_message_markdown(msg)
                if formatted:
                    f.write(formatted)
                    f.write("\n\n---\n\n")

    if output_format in ['xml', 'all']:
        # Generate XML conversation (legacy)
        root = ET.Element('claude-session')
        root.set('xmlns', 'https://claude.ai/session-export/v1')
        root.set('export-version', '1.0')

        meta_elem = ET.SubElement(root, 'metadata')
        ET.SubElement(meta_elem, 'session-id').text = metadata['session_id']
        ET.SubElement(meta_elem, 'version').text = messages[0].get('version', '') if messages else ''
        ET.SubElement(meta_elem, 'working-directory').text = metadata['project_dir']
        ET.SubElement(meta_elem, 'start-time').text = metadata['start_time']
        ET.SubElement(meta_elem, 'end-time').text = metadata['end_time']
        ET.SubElement(meta_elem, 'export-time').text = datetime.now().isoformat()

        stats_elem = ET.SubElement(meta_elem, 'statistics')
        ET.SubElement(stats_elem, 'total-messages').text = str(metadata['total_messages'])
        ET.SubElement(stats_elem, 'user-messages').text = str(metadata['user_messages'])
        ET.SubElement(stats_elem, 'assistant-messages').text = str(metadata['assistant_messages'])
        ET.SubElement(stats_elem, 'tool-uses').text = str(metadata['tool_uses'])

        models_elem = ET.SubElement(stats_elem, 'models-used')
        for model in metadata['models_used']:
            ET.SubElement(models_elem, 'model').text = model

        messages_elem = ET.SubElement(root, 'messages')
        for msg in messages:
            format_message_xml(msg, messages_elem)

        xml_path = export_dir / 'conversation_full.xml'
        xml_string = prettify_xml(root)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)

    # Generate summary (legacy)
    summary_path = export_dir / 'summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Claude Code Session Summary\n")
        f.write(f"==========================\n\n")
        f.write(f"Session ID: {metadata['session_id']}\n")
        f.write(f"Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Project Directory: {metadata['project_dir']}\n")
        f.write(f"Duration: {metadata['start_time']} to {metadata['end_time']}\n")
        f.write(f"\nStatistics:\n")
        f.write(f"- Total Messages: {metadata['total_messages']}\n")
        f.write(f"- User Messages: {metadata['user_messages']}\n")
        f.write(f"- Assistant Messages: {metadata['assistant_messages']}\n")
        f.write(f"- Tool Uses: {metadata['tool_uses']}\n")
        f.write(f"- Models: {', '.join(metadata['models_used'])}\n")
        f.write(f"\nExported to: {export_dir}\n")

    # =========================================================================
    # Write new structured session data
    # =========================================================================
    print("📝 Writing session data...")

    # Create session directory structure
    session_dir = export_dir / 'session'
    session_dir.mkdir(exist_ok=True)

    # Main session
    main_session_path = session_dir / 'main.jsonl'
    shutil.copy2(session_info['path'], main_session_path)

    # Agent sessions
    agents_dir = session_dir / 'agents'
    agents_dir.mkdir(exist_ok=True)
    if agent_sessions:
        for agent_id, agent_path in agent_sessions.items():
            shutil.copy2(agent_path, agents_dir / f'agent-{agent_id}.jsonl')
    else:
        write_empty_marker(agents_dir, "No agent sessions for this export.")

    # File history
    file_history_dir = session_dir / 'file-history'
    file_history_dir.mkdir(exist_ok=True)
    if file_history:
        for fh_file in file_history:
            shutil.copy2(fh_file, file_history_dir / fh_file.name)
    else:
        write_empty_marker(file_history_dir, "No file history snapshots for this session.")

    # Plan file
    if plan_file:
        shutil.copy2(plan_file, session_dir / 'plan.md')
    else:
        (session_dir / 'plan.md').write_text("# No Plan\n\nNo plan file was created for this session.\n", encoding='utf-8')

    # Todos
    if todos:
        # Combine all todo files into one
        all_todos = []
        for todo_file in todos:
            try:
                with open(todo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_todos.extend(data)
                    else:
                        all_todos.append(data)
            except:
                pass

        with open(session_dir / 'todos.json', 'w', encoding='utf-8') as f:
            json.dump(all_todos, f, indent=2)
    else:
        with open(session_dir / 'todos.json', 'w', encoding='utf-8') as f:
            json.dump([], f)

    # Session env
    session_env_dir = session_dir / 'session-env'
    session_env_dir.mkdir(exist_ok=True)
    if session_env:
        for env_file in session_env.iterdir():
            if env_file.is_file():
                shutil.copy2(env_file, session_env_dir / env_file.name)
    else:
        write_empty_marker(session_env_dir, "No session environment data.")

    # =========================================================================
    # Write config snapshot
    # =========================================================================
    print("📝 Writing config snapshot...")

    config_dir = export_dir / 'config'
    config_dir.mkdir(exist_ok=True)

    # Commands
    commands_dir = config_dir / 'commands'
    commands_dir.mkdir(exist_ok=True)
    if config_files['commands']:
        for cmd_file in config_files['commands']:
            shutil.copy2(cmd_file, commands_dir / cmd_file.name)
    else:
        write_empty_marker(commands_dir, "No custom commands configured.")

    # Skills
    skills_dir = config_dir / 'skills'
    skills_dir.mkdir(exist_ok=True)
    if config_files['skills']:
        for skill_file in config_files['skills']:
            shutil.copy2(skill_file, skills_dir / skill_file.name)
    else:
        write_empty_marker(skills_dir, "No custom skills configured.")

    # Hooks
    hooks_dir = config_dir / 'hooks'
    hooks_dir.mkdir(exist_ok=True)
    if config_files['hooks']:
        for hook_file in config_files['hooks']:
            shutil.copy2(hook_file, hooks_dir / hook_file.name)
    else:
        write_empty_marker(hooks_dir, "No hooks configured.")

    # Agents
    agents_config_dir = config_dir / 'agents'
    agents_config_dir.mkdir(exist_ok=True)
    if config_files['agents']:
        for agent_file in config_files['agents']:
            shutil.copy2(agent_file, agents_config_dir / agent_file.name)
    else:
        write_empty_marker(agents_config_dir, "No custom agents configured.")

    # Rules
    rules_dir = config_dir / 'rules'
    rules_dir.mkdir(exist_ok=True)
    if config_files['rules']:
        for rule_file in config_files['rules']:
            shutil.copy2(rule_file, rules_dir / rule_file.name)
    else:
        write_empty_marker(rules_dir, "No custom rules configured.")

    # Settings
    if config_files['settings']:
        shutil.copy2(config_files['settings'], config_dir / 'settings.json')
    else:
        (config_dir / 'settings.json').write_text('{}', encoding='utf-8')

    # CLAUDE.md
    if config_files['claude_md']:
        shutil.copy2(config_files['claude_md'], config_dir / 'CLAUDE.md')
    else:
        (config_dir / 'CLAUDE.md').write_text('# No CLAUDE.md\n\nNo CLAUDE.md file in project.\n', encoding='utf-8')

    # =========================================================================
    # Write new metadata files
    # =========================================================================
    print("📝 Writing manifest and RENDERED.md...")

    # Write manifest
    manifest_path = export_dir / '.cctrace-manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    # Write RENDERED.md
    rendered_md = generate_rendered_markdown(messages, metadata, manifest)
    rendered_path = export_dir / 'RENDERED.md'
    with open(rendered_path, 'w', encoding='utf-8') as f:
        f.write(rendered_md)

    return export_dir, manifest


def export_session(session_info, output_dir=None, output_format='all', copy_to_cwd=None):
    """Export a session to the specified output directory.
    
    Args:
        session_info: Session information dictionary
        output_dir: Output directory path (default: ~/claude_sessions/exports)
        output_format: Format to export ('md', 'xml', or 'all')
        copy_to_cwd: Whether to copy export to current directory (default: check env var)
    """
    if output_dir is None:
        output_dir = Path.home() / 'claude_sessions' / 'exports'
    
    # Parse the session file
    messages, metadata = parse_jsonl_file(session_info['path'])
    
    # Create output directory with timestamp and actual session ID from metadata
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # Use the actual session ID from the file content, not the filename
    actual_session_id = metadata['session_id'] if metadata['session_id'] else session_info['session_id']
    export_dir = output_dir / f"{timestamp}_{actual_session_id[:8]}"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Save metadata
    metadata_path = export_dir / 'session_info.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Copy raw JSONL
    raw_path = export_dir / 'raw_messages.jsonl'
    shutil.copy2(session_info['path'], raw_path)
    
    # Generate output based on format
    if output_format in ['md', 'all']:
        # Generate markdown conversation
        md_path = export_dir / 'conversation_full.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Claude Code Session Export\n\n")
            f.write(f"**Session ID:** `{metadata['session_id']}`\n")
            f.write(f"**Project:** `{metadata['project_dir']}`\n")
            f.write(f"**Start Time:** {metadata['start_time']}\n")
            f.write(f"**End Time:** {metadata['end_time']}\n")
            f.write(f"**Total Messages:** {metadata['total_messages']}\n")
            f.write(f"**User Messages:** {metadata['user_messages']}\n")
            f.write(f"**Assistant Messages:** {metadata['assistant_messages']}\n")
            f.write(f"**Tool Uses:** {metadata['tool_uses']}\n")
            f.write(f"**Models Used:** {', '.join(metadata['models_used'])}\n\n")
            f.write("---\n\n")
            
            for msg in messages:
                formatted = format_message_markdown(msg)
                if formatted:
                    f.write(formatted)
                    f.write("\n\n---\n\n")
    
    if output_format in ['xml', 'all']:
        # Generate XML conversation
        root = ET.Element('claude-session')
        root.set('xmlns', 'https://claude.ai/session-export/v1')
        root.set('export-version', '1.0')
        
        # Add metadata
        meta_elem = ET.SubElement(root, 'metadata')
        ET.SubElement(meta_elem, 'session-id').text = metadata['session_id']
        ET.SubElement(meta_elem, 'version').text = messages[0].get('version', '') if messages else ''
        ET.SubElement(meta_elem, 'working-directory').text = metadata['project_dir']
        ET.SubElement(meta_elem, 'start-time').text = metadata['start_time']
        ET.SubElement(meta_elem, 'end-time').text = metadata['end_time']
        ET.SubElement(meta_elem, 'export-time').text = datetime.now().isoformat()
        
        # Add statistics
        stats_elem = ET.SubElement(meta_elem, 'statistics')
        ET.SubElement(stats_elem, 'total-messages').text = str(metadata['total_messages'])
        ET.SubElement(stats_elem, 'user-messages').text = str(metadata['user_messages'])
        ET.SubElement(stats_elem, 'assistant-messages').text = str(metadata['assistant_messages'])
        ET.SubElement(stats_elem, 'tool-uses').text = str(metadata['tool_uses'])
        
        models_elem = ET.SubElement(stats_elem, 'models-used')
        for model in metadata['models_used']:
            ET.SubElement(models_elem, 'model').text = model
        
        # Add messages
        messages_elem = ET.SubElement(root, 'messages')
        for msg in messages:
            format_message_xml(msg, messages_elem)
        
        # Write XML file
        xml_path = export_dir / 'conversation_full.xml'
        xml_string = prettify_xml(root)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
    
    # Generate summary
    summary_path = export_dir / 'summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Claude Code Session Summary\n")
        f.write(f"==========================\n\n")
        f.write(f"Session ID: {metadata['session_id']}\n")
        f.write(f"Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Project Directory: {metadata['project_dir']}\n")
        f.write(f"Duration: {metadata['start_time']} to {metadata['end_time']}\n")
        f.write(f"\nStatistics:\n")
        f.write(f"- Total Messages: {metadata['total_messages']}\n")
        f.write(f"- User Messages: {metadata['user_messages']}\n")
        f.write(f"- Assistant Messages: {metadata['assistant_messages']}\n")
        f.write(f"- Tool Uses: {metadata['tool_uses']}\n")
        f.write(f"- Models: {', '.join(metadata['models_used'])}\n")
        f.write(f"\nExported to: {export_dir}\n")
    
    # Check if we should copy to current working directory
    if copy_to_cwd is None:
        # Check environment variable (default: True unless explicitly disabled)
        copy_to_cwd = os.environ.get('CLAUDE_EXPORT_COPY_TO_CWD', 'true').lower() != 'false'
    
    if copy_to_cwd:
        # Copy export folder to current working directory
        cwd = Path.cwd()
        cwd_export_name = f"claude_export_{timestamp}_{actual_session_id[:8]}"
        cwd_export_path = cwd / cwd_export_name
        
        try:
            # Copy the entire export directory to CWD
            shutil.copytree(export_dir, cwd_export_path)
            print(f"\n📂 Export copied to current directory: {cwd_export_path}")
        except Exception as e:
            print(f"\n⚠️  Could not copy to current directory: {e}")
    
    return export_dir

def main():
    parser = argparse.ArgumentParser(description='Export Claude Code session')
    parser.add_argument('--session-id', help='Specific session ID to export')
    parser.add_argument('--output-dir', help='Custom output directory')
    parser.add_argument('--format', choices=['md', 'xml', 'all'], default='all',
                       help='Output format (default: all)')
    parser.add_argument('--max-age', type=int, default=300,
                       help='Max age in seconds for active session detection (default: 300)')
    parser.add_argument('--no-copy-to-cwd', action='store_true',
                       help='Do not copy export to current directory')

    # New enhanced export options
    parser.add_argument('--export-name', help='Name for the export folder (for enhanced export)')
    parser.add_argument('--in-repo', action='store_true',
                       help='Export to .claude-sessions/ in the project repo (enhanced export)')
    parser.add_argument('--anonymize', action='store_true',
                       help='Exclude user/machine info from export')
    parser.add_argument('--legacy', action='store_true',
                       help='Use legacy export format only (skip enhanced structure)')

    args = parser.parse_args()
    
    # Get current working directory
    cwd = os.getcwd()
    
    print(f"🔍 Looking for Claude Code sessions in: {cwd}")
    
    # Find all sessions for this project
    sessions = find_project_sessions(cwd)
    
    if not sessions:
        print("❌ No Claude Code sessions found for this project.")
        print("   Make sure you're running this from a project directory with active Claude Code sessions.")
        return 1
    
    print(f"📂 Found {len(sessions)} session(s) for this project")
    
    # Determine which session to export
    if args.session_id:
        # Find specific session
        session_to_export = None
        for session in sessions:
            if session['session_id'] == args.session_id:
                session_to_export = session
                break
        
        if not session_to_export:
            print(f"❌ Session ID {args.session_id} not found.")
            return 1
    else:
        # Find active session
        active_sessions = find_active_session(sessions, args.max_age)
        
        if not active_sessions:
            print(f"⚠️  No active sessions found (modified within {args.max_age} seconds).")
            print("\nAvailable sessions:")
            for i, session in enumerate(sessions[:5]):  # Show first 5
                age = int(time.time() - session['mtime'])
                print(f"  {i+1}. {session['session_id'][:8]}... (modified {age}s ago)")
            
            # Use most recent session
            print("\n🔄 Exporting most recent session...")
            session_to_export = sessions[0]
        elif len(active_sessions) == 1:
            session_to_export = active_sessions[0]
        else:
            # Multiple active sessions - try to identify current one
            print(f"🔍 Found {len(active_sessions)} active sessions:")
            for i, session in enumerate(active_sessions):
                age = int(time.time() - session['mtime'])
                print(f"  {i+1}. {session['session_id'][:8]}... (modified {age}s ago)")
            
            print("\n🎯 Attempting to identify current session...")
            
            # Try to identify the current session
            current_session = identify_current_session(sessions, cwd)
            
            if current_session:
                print(f"✅ Successfully identified current session: {current_session['session_id']}")
                session_to_export = current_session
            else:
                # Fallback: check if we're in Claude Code
                claude_pid = get_parent_claude_pid()
                if claude_pid:
                    print(f"🔍 Running in Claude Code (PID: {claude_pid})")
                    print("⚠️  Could not identify specific session via activity. Using most recent.")
                else:
                    print("⚠️  Not running inside Claude Code. Using most recent session.")
                
                session_to_export = active_sessions[0]
                print(f"📌 Defaulting to: {session_to_export['session_id']}")
    
    # Export the session
    print(f"\n📤 Exporting session file: {session_to_export['session_id'][:8]}...")

    # Determine export mode
    use_enhanced = args.in_repo and not args.legacy

    if use_enhanced:
        # Enhanced export to .claude-sessions/
        export_name = args.export_name
        if not export_name:
            # Generate default export name from timestamp
            export_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        output_dir = Path(args.output_dir) if args.output_dir else None
        export_path, manifest = export_session_enhanced(
            session_to_export,
            cwd,
            export_name,
            output_dir=output_dir,
            output_format=args.format,
            anonymized=args.anonymize,
            in_repo=True
        )

        print(f"\n✅ Enhanced export completed successfully!")
        print(f"📁 Export directory: {export_path}")
        print(f"\n📋 Export Summary:")
        print(f"   Session ID: {manifest['session_id']}")
        if manifest.get('session_slug'):
            print(f"   Session Name: {manifest['session_slug']}")
        print(f"   Messages: {manifest['statistics']['message_count']}")
        print(f"   Tool Uses: {manifest['statistics']['tool_uses']}")
        print(f"   Agent Sessions: {len(manifest['session_data']['agent_sessions'])}")
        print(f"   File History: {len(manifest['session_data']['file_history'])} snapshots")

        print(f"\nFiles created:")
        print(f"  Legacy files:")
        for name in ['raw_messages.jsonl', 'conversation_full.md', 'conversation_full.xml',
                     'session_info.json', 'summary.txt']:
            if (export_path / name).exists():
                print(f"    - {name}")

        print(f"  Enhanced structure:")
        print(f"    - session/main.jsonl")
        print(f"    - session/agents/")
        print(f"    - session/file-history/")
        print(f"    - session/plan.md")
        print(f"    - session/todos.json")
        print(f"    - config/")
        print(f"    - RENDERED.md")
        print(f"    - .cctrace-manifest.json")

        print(f"\n💡 Next steps:")
        print(f"   git add {export_path.relative_to(cwd)}")
        print(f"   git commit -m \"Export Claude Code session: {export_name}\"")

    else:
        # Legacy export
        output_dir = Path(args.output_dir) if args.output_dir else None
        # Pass copy_to_cwd as False if --no-copy-to-cwd is specified, otherwise None (use default)
        copy_to_cwd = False if args.no_copy_to_cwd else None
        export_path = export_session(session_to_export, output_dir, args.format, copy_to_cwd)

        # Check if actual session ID differs from filename
        session_info_file = export_path / 'session_info.json'
        if session_info_file.exists():
            with open(session_info_file, 'r') as f:
                actual_metadata = json.load(f)
                actual_session_id = actual_metadata.get('session_id', '')
                if actual_session_id and actual_session_id != session_to_export['session_id']:
                    print(f"ℹ️  Note: Actual session ID is {actual_session_id}")
                    print(f"   (File was named {session_to_export['session_id']})")

        print(f"\n✅ Session exported successfully!")
        print(f"📁 Output directory: {export_path}")
        print(f"\nFiles created:")
        for file in export_path.iterdir():
            print(f"  - {file.name}")

        # Show summary
        summary_file = export_path / 'summary.txt'
        if summary_file.exists():
            print(f"\n📋 Summary:")
            with open(summary_file, 'r') as f:
                print(f.read())

        # Hint about enhanced export
        print(f"\n💡 Tip: Use --in-repo for enhanced export with full session data")

    return 0

if __name__ == '__main__':
    sys.exit(main())