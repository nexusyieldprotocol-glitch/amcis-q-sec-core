#!/bin/bash
#
# AMCIS Git Hooks Installation Script
#
# This script installs the AMCIS pre-commit hook and other git hooks
# to automatically run documentation generation, linting, and tests.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "=============================================="
echo "AMCIS Git Hooks Installer"
echo "=============================================="
echo ""

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "Error: Not a git repository!"
    echo "Please run this script from within the AMCIS project."
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

echo "Installing hooks to: $HOOKS_DIR"
echo ""

# Function to install a hook
install_hook() {
    local hook_name=$1
    local source_file=$2
    local target_file="$HOOKS_DIR/$hook_name"
    
    if [ -f "$target_file" ]; then
        echo "Backing up existing $hook_name hook..."
        mv "$target_file" "$target_file.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    echo "Installing $hook_name hook..."
    cp "$source_file" "$target_file"
    chmod +x "$target_file"
    
    echo "✓ $hook_name installed"
}

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre_commit_hook.py" ]; then
    install_hook "pre-commit" "$SCRIPT_DIR/pre_commit_hook.py"
else
    echo "Warning: pre_commit_hook.py not found in scripts/"
fi

# Install prepare-commit-msg hook (for commit message templates)
cat > "$HOOKS_DIR/prepare-commit-msg" << 'EOF'
#!/bin/bash
#
# Prepare commit message hook
# Adds helpful reminders to commit messages
#

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only add template for regular commits (not merge, squash, etc.)
if [ -z "$COMMIT_SOURCE" ]; then
    # Read current message
    ORIGINAL_MSG=$(cat "$COMMIT_MSG_FILE")
    
    # Add template if message is empty or very short
    if [ ${#ORIGINAL_MSG} -lt 10 ]; then
        cat > "$COMMIT_MSG_FILE" << 'TEMPLATE'
# Commit message format:
# type(scope): description
#
# Types:
#   feat:     New feature
#   fix:      Bug fix
#   docs:     Documentation changes
#   style:    Code style changes (formatting, semicolons, etc)
#   refactor: Code refactoring
#   perf:     Performance improvements
#   test:     Adding or updating tests
#   chore:    Build process or auxiliary tool changes
#   ci:       CI/CD changes
#
# Example:
#   feat(crypto): add ML-KEM-768 key encapsulation
#
# Body (optional): Explain the "what" and "why", not the "how"
#
# Footer (optional): References to issues, breaking changes, etc.
#   Closes #123
#   BREAKING CHANGE: API signature changed

TEMPLATE
        echo "$ORIGINAL_MSG" >> "$COMMIT_MSG_FILE"
    fi
fi
EOF
chmod +x "$HOOKS_DIR/prepare-commit-msg"
echo "✓ prepare-commit-msg installed"

# Install post-commit hook (for notifications, etc.)
cat > "$HOOKS_DIR/post-commit" << 'EOF'
#!/bin/bash
#
# Post-commit hook
# Runs after a successful commit
#

# Get commit info
COMMIT_MSG=$(git log -1 --pretty=%B)
COMMIT_HASH=$(git log -1 --pretty=%h)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo ""
echo "✓ Commit $COMMIT_HASH created on branch $BRANCH"

# Remind about pushing
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "⚠ You're on the main branch. Consider creating a feature branch."
fi

# Check if documentation needs regeneration
if echo "$COMMIT_MSG" | grep -qE "(doc|api|document)"; then
    echo "📚 Documentation changes detected. Consider running:"
    echo "   python scripts/generate_docs.py"
fi

echo ""
EOF
chmod +x "$HOOKS_DIR/post-commit"
echo "✓ post-commit installed"

# Install post-merge hook (for dependency updates)
cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/bin/bash
#
# Post-merge hook
# Runs after a successful merge
#

echo ""
echo "Merge completed. Checking for updates..."

# Check if requirements changed
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep -q "requirements"; then
    echo "📦 Requirements changed! Run:"
    echo "   pip install -r requirements.txt"
fi

# Check if package.json changed (for Node components)
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep -q "package.json"; then
    echo "📦 Node dependencies changed! Run:"
    echo "   npm install"
fi

# Check if migrations needed
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep -q "migrations"; then
    echo "🗄️  Database migrations detected! Run:"
    echo "   alembic upgrade head"
fi

echo ""
EOF
chmod +x "$HOOKS_DIR/post-merge"
echo "✓ post-merge installed"

# Install pre-push hook
if [ -f "$SCRIPT_DIR/pre_push_hook.py" ]; then
    install_hook "pre-push" "$SCRIPT_DIR/pre_push_hook.py"
else
    # Create a basic pre-push hook
    cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
#
# Pre-push hook
# Runs before pushing to remote
#

echo "Running pre-push checks..."

# Get the current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Prevent direct pushes to main/master
case "$BRANCH" in
    main|master)
        echo "❌ Direct push to $BRANCH branch is not allowed!"
        echo "   Please create a pull request instead."
        exit 1
        ;;
esac

# Run tests if they exist
if [ -f "pytest.ini" ] || [ -d "tests" ]; then
    echo "Running tests..."
    if command -v pytest &> /dev/null; then
        pytest tests/ -x -q --tb=no
        if [ $? -ne 0 ]; then
            echo "❌ Tests failed! Push aborted."
            exit 1
        fi
    fi
fi

echo "✓ Pre-push checks passed"
exit 0
EOF
    chmod +x "$HOOKS_DIR/pre-push"
    echo "✓ pre-push installed"
fi

echo ""
echo "=============================================="
echo "Installation Complete!"
echo "=============================================="
echo ""
echo "Installed hooks:"
ls -1 "$HOOKS_DIR" | grep -v ".backup" | sed 's/^/  - /'
echo ""
echo "To bypass hooks temporarily:"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
echo "To uninstall hooks:"
echo "  rm -rf .git/hooks/*"
echo ""
