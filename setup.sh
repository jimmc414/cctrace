#!/bin/bash

# Claude Code Session Export - Installation Script
# This script installs the export tool and configures Claude Code

set -e

echo "🚀 Claude Code Session Export Installer"
echo "======================================"
echo ""

# Check if running in correct directory
if [ ! -f "export_claude_session.py" ]; then
    echo "❌ Error: Please run this script from the claude-code-session-export directory"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ~/claude_sessions/{exports,hooks}
mkdir -p ~/.claude/commands

# Copy main script
echo "📄 Installing export script..."
cp export_claude_session.py ~/claude_sessions/
chmod +x ~/claude_sessions/export_claude_session.py

# Copy hook scripts
echo "🔧 Installing hook scripts..."
cp -r hooks/* ~/claude_sessions/hooks/ 2>/dev/null || true
chmod +x ~/claude_sessions/hooks/*.sh 2>/dev/null || true

# Install slash command
echo "⚡ Installing Claude Code slash command..."
cat > ~/.claude/commands/export.md << 'EOF'
Export the current Claude Code session to a timestamped folder with full conversation history, metadata, and statistics.

!python3 ~/claude_sessions/export_claude_session.py
EOF

# Create README in export directory
echo "📝 Creating documentation..."
cp -r docs ~/claude_sessions/ 2>/dev/null || true

# Test the installation
echo ""
echo "🧪 Testing installation..."
if python3 ~/claude_sessions/export_claude_session.py --help > /dev/null 2>&1; then
    echo "✅ Export script installed successfully"
else
    echo "⚠️  Warning: Export script test failed"
fi

# Check for jq (optional dependency for hooks)
if command -v jq &> /dev/null; then
    echo "✅ jq is installed (required for hooks)"
else
    echo "⚠️  jq is not installed (required for hook scripts)"
    echo "   Install with: sudo apt-get install jq"
fi

# Display hook configuration instructions
echo ""
echo "🎉 Installation complete!"
echo ""
echo "📋 Quick Start:"
echo "   1. In any Claude Code session, type: /user:export"
echo "   2. Or run directly: python3 ~/claude_sessions/export_claude_session.py"
echo ""
echo "🔄 To enable automatic exports, add this to ~/.claude/settings.json:"
echo ""
echo '   {
     "model": "opus",
     "hooks": {
       "Stop": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "bash ~/claude_sessions/hooks/auto_export_hook.sh"
             }
           ]
         }
       ]
     }
   }'
echo ""
echo "📚 For more information, see ~/claude_sessions/docs/README.md"
echo ""