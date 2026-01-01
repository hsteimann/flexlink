#!/bin/bash
# FlexLink Development Cleanup Script
# Removes temporary files, generated outputs, and Python cache

set -e  # Exit on error

echo "🧹 FlexLink Repository Cleanup"
echo "================================"
echo ""

# Track space saved
SPACE_SAVED=0

# 1. Remove temp directory
if [ -d "temp/" ]; then
    echo "📁 Removing temp/ directory..."
    TEMP_SIZE=$(du -sk temp/ | cut -f1)
    rm -rf temp/
    SPACE_SAVED=$((SPACE_SAVED + TEMP_SIZE))
    echo "   ✓ Removed temp/ (${TEMP_SIZE} KB)"
else
    echo "📁 temp/ directory not found (already clean)"
fi

# 2. Clean generated downloads (keep .gitkeep)
if [ -d "data/downloads/" ]; then
    echo "📁 Cleaning data/downloads/..."
    DOWNLOADS_SIZE=$(du -sk data/downloads/ | cut -f1)
    # Count files before deletion
    FILE_COUNT=$(find data/downloads -type f ! -name '.gitkeep' | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -gt "0" ]; then
        find data/downloads -type f ! -name '.gitkeep' -delete
        echo "   ✓ Removed $FILE_COUNT generated file(s) (~${DOWNLOADS_SIZE} KB)"
        SPACE_SAVED=$((SPACE_SAVED + DOWNLOADS_SIZE))
    else
        echo "   ✓ Already clean (no generated files)"
    fi
else
    echo "📁 data/downloads/ not found"
fi

# 3. Remove run_history.db from git (if tracked)
if git ls-files --error-unmatch data/run_history.db > /dev/null 2>&1; then
    echo "📁 Removing run_history.db from git tracking..."
    git rm --cached data/run_history.db
    echo "   ✓ Removed from git (file kept locally)"
    echo "   ℹ️  run_history.db is now in .gitignore"
else
    echo "📁 run_history.db already untracked"
fi

# 4. Clean Python cache
echo "🐍 Cleaning Python cache..."
CACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$CACHE_COUNT" -gt "0" ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "   ✓ Removed $CACHE_COUNT __pycache__ directories"
else
    echo "   ✓ No Python cache found"
fi

# 5. Clean test coverage files
echo "📊 Cleaning coverage files..."
COVERAGE_FILES=0
[ -d "htmlcov/" ] && COVERAGE_FILES=$((COVERAGE_FILES + 1)) && rm -rf htmlcov/
[ -f ".coverage" ] && COVERAGE_FILES=$((COVERAGE_FILES + 1)) && rm -f .coverage
find . -name ".coverage.*" -type f -delete 2>/dev/null || true
if [ "$COVERAGE_FILES" -gt "0" ]; then
    echo "   ✓ Removed coverage files"
else
    echo "   ✓ No coverage files found"
fi

# 6. Clean pytest cache
echo "🧪 Cleaning pytest cache..."
if [ -d ".pytest_cache/" ]; then
    rm -rf .pytest_cache/
    echo "   ✓ Removed .pytest_cache/"
else
    echo "   ✓ No pytest cache found"
fi

# 7. Clean ruff cache
echo "🔍 Cleaning ruff cache..."
if [ -d ".ruff_cache/" ]; then
    rm -rf .ruff_cache/
    echo "   ✓ Removed .ruff_cache/"
else
    echo "   ✓ No ruff cache found"
fi

echo ""
echo "✅ Cleanup complete!"
if [ "$SPACE_SAVED" -gt "0" ]; then
    echo "   💾 Space saved: ~${SPACE_SAVED} KB"
fi
echo ""
echo "📝 Next steps:"
echo "   1. Review changes: git status"
echo "   2. Commit .gitignore updates if needed"
echo "   3. Run tests to ensure nothing broke: pytest src/tests/"
echo ""
