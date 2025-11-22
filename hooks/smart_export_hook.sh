#!/bin/bash

# Claude Code Smart Export Hook
# Conditionally exports sessions based on criteria
# Only exports sessions that are substantial and completed successfully

# Configuration
MIN_MESSAGES=10
MIN_DURATION_SECONDS=300  # 5 minutes

# Get context from Claude
CWD=$(jq -r '.cwd // "."' <<< "$CLAUDE_JSON" 2>/dev/null || pwd)
SESSION_ID=$(jq -r '.sessionId // ""' <<< "$CLAUDE_JSON" 2>/dev/null)

# Log file
LOG_FILE="/tmp/claude_smart_export_$(date +%Y%m%d_%H%M%S).log"

echo "=== Claude Code Smart Export Hook ===" >> "$LOG_FILE"
echo "Time: $(date)" >> "$LOG_FILE"
echo "Directory: $CWD" >> "$LOG_FILE"
echo "Session ID: $SESSION_ID" >> "$LOG_FILE"

# Change to project directory
cd "$CWD" || exit 1

# Run export and capture output
EXPORT_OUTPUT=$(python3 ~/claude_sessions/export_claude_session.py --max-age 3600 2>&1)
EXPORT_RESULT=$?

echo "" >> "$LOG_FILE"
echo "Export output:" >> "$LOG_FILE"
echo "$EXPORT_OUTPUT" >> "$LOG_FILE"

# Parse statistics from export output
if [ $EXPORT_RESULT -eq 0 ]; then
    # Extract message count from output (portable sed instead of grep -P)
    MESSAGE_COUNT=$(echo "$EXPORT_OUTPUT" | sed -n 's/.*Total Messages: \([0-9]*\).*/\1/p' | head -1 || echo "0")
    # Fallback to 0 if empty
    MESSAGE_COUNT=${MESSAGE_COUNT:-0}
    
    echo "" >> "$LOG_FILE"
    echo "Message count: $MESSAGE_COUNT" >> "$LOG_FILE"
    
    # Check if session meets criteria
    if [ "$MESSAGE_COUNT" -lt "$MIN_MESSAGES" ]; then
        echo "⚠️  Session too short ($MESSAGE_COUNT messages < $MIN_MESSAGES required)" >> "$LOG_FILE"
        echo "🗑️  Removing export..." >> "$LOG_FILE"

        # Find and remove the export directory (portable sed instead of grep -P)
        EXPORT_DIR=$(echo "$EXPORT_OUTPUT" | sed -n 's/.*Exported to: \(.*\)/\1/p' | head -1 || echo "")
        if [ -n "$EXPORT_DIR" ] && [ -d "$EXPORT_DIR" ]; then
            rm -rf "$EXPORT_DIR"
            echo "✅ Short session export removed" >> "$LOG_FILE"
        fi
    else
        echo "✅ Session exported successfully ($MESSAGE_COUNT messages)" >> "$LOG_FILE"
        
        # Send notification for substantial sessions
        if command -v notify-send &> /dev/null; then
            notify-send "Claude Session Exported" "Session with $MESSAGE_COUNT messages has been saved" -i dialog-information 2>/dev/null || true
        fi
        
        # Optional: Create a summary file in home directory for easy access
        SUMMARY_FILE="$HOME/claude_sessions/latest_export.txt"
        echo "Latest Claude Code Export" > "$SUMMARY_FILE"
        echo "========================" >> "$SUMMARY_FILE"
        echo "" >> "$SUMMARY_FILE"
        echo "$EXPORT_OUTPUT" | grep -A 20 "📋 Summary:" >> "$SUMMARY_FILE"
    fi
else
    echo "❌ Export failed with code $EXPORT_RESULT" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
echo "=== End of smart export ===" >> "$LOG_FILE"

# Always exit successfully
exit 0