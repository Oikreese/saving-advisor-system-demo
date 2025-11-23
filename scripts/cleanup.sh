#!/bin/bash
# Clean temporary files and caches in the project

echo "🧹 Starting project cleanup..."
echo ""

# Delete Python cache
echo "1️⃣  Deleting Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "✅ Python cache cleanup completed"

# Delete temporary files
echo ""
echo "2️⃣  Deleting temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null
find . -type f -name "*.temp" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
echo "✅ Temporary files cleanup completed"

# Delete log files
echo ""
echo "3️⃣  Cleaning log files..."
find . -type f -name "*.log" -delete 2>/dev/null
rm -rf logs/ 2>/dev/null
echo "✅ Log files cleanup completed"

# Delete test coverage files
echo ""
echo "4️⃣  Cleaning test coverage files..."
rm -rf .coverage 2>/dev/null
rm -rf htmlcov/ 2>/dev/null
rm -rf .pytest_cache/ 2>/dev/null
rm -rf coverage.out coverage.html 2>/dev/null
echo "✅ Test coverage files cleanup completed"

# Delete build files
echo ""
echo "5️⃣  Cleaning build files..."
rm -rf build/ dist/ *.egg-info/ 2>/dev/null
echo "✅ Build files cleanup completed"

# Go cleanup
echo ""
echo "6️⃣  Cleaning Go build files..."
rm -f go/bin/server go/server 2>/dev/null
rm -f go/*.test go/*.out 2>/dev/null
echo "✅ Go build files cleanup completed"

# SQLite database (optional)
echo ""
echo "7️⃣  Cleaning SQLite database (development environment)..."
read -p "Do you want to delete SQLite database files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find . -name "*.db" -type f -delete 2>/dev/null
    find . -name "*.sqlite*" -type f -delete 2>/dev/null
    echo "✅ SQLite database deleted"
else
    echo "⏭️  Skipping SQLite database cleanup"
fi

echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "📊 Current disk usage:"
du -sh . 2>/dev/null
