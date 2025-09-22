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
    # Claude normalizes project directories by replacing path separators AND dots
    # in the working directory path with hyphens (see issue #4).
    normalized_project_path = project_path.replace('\\', '/')
    project_dir_name = normalized_project_path.replace('/', '-').replace('.', '-')
    if project_dir_name.startswith('-'):
        project_dir_name = project_dir_name[1:]

    claude_project_dir = Path.home() / '.claude' / 'projects' / f'-{project_dir_name}'
    
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
    
    return 0

if __name__ == '__main__':
    sys.exit(main())