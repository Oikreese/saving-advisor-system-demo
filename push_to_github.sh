#!/bin/bash
# Script to push to existing GitHub repository

set -e

echo "🚀 Saving Advisor System - GitHub Push Script"
echo "=============================================="
echo ""

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    echo "⚠️  Remote 'origin' already exists:"
    git remote -v
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your GitHub username: " GITHUB_USER
        read -p "Use SSH? (y/n, default: n for HTTPS): " USE_SSH
        if [[ $USE_SSH =~ ^[Yy]$ ]]; then
            REPO_URL="git@github.com:${GITHUB_USER}/saving-advisor-system.git"
        else
            REPO_URL="https://github.com/${GITHUB_USER}/saving-advisor-system.git"
        fi
        git remote set-url origin "$REPO_URL"
        echo "✅ Remote URL updated"
    else
        echo "Using existing remote"
    fi
else
    echo "📝 Adding remote repository..."
    read -p "Enter your GitHub username: " GITHUB_USER
    read -p "Use SSH? (y/n, default: n for HTTPS): " USE_SSH
    if [[ $USE_SSH =~ ^[Yy]$ ]]; then
        REPO_URL="git@github.com:${GITHUB_USER}/saving-advisor-system.git"
    else
        REPO_URL="https://github.com/${GITHUB_USER}/saving-advisor-system.git"
    fi
    git remote add origin "$REPO_URL"
    echo "✅ Remote added: $REPO_URL"
fi

echo ""
echo "🔍 Checking remote repository status..."
echo ""

# Fetch to see what's on remote
if git fetch origin 2>&1 | grep -q "fatal"; then
    echo "⚠️  Cannot fetch from remote. The repository might be empty or you need authentication."
    echo "   Proceeding with push..."
    EMPTY_REPO=true
else
    EMPTY_REPO=false
    # Check if remote has any branches
    REMOTE_BRANCHES=$(git branch -r 2>/dev/null | wc -l | tr -d ' ')
    if [ "$REMOTE_BRANCHES" -eq 0 ]; then
        EMPTY_REPO=true
    fi
fi

echo ""
echo "📋 Current branch: $(git branch --show-current)"
echo ""

if [ "$EMPTY_REPO" = true ]; then
    echo "✅ Remote repository appears to be empty"
    echo "🚀 Pushing current branch..."
    git push -u origin $(git branch --show-current)
    echo ""
    echo "✅ Successfully pushed to GitHub!"
else
    echo "⚠️  Remote repository has content"
    echo ""
    echo "Options:"
    echo "1. Force push (overwrites remote) - USE WITH CAUTION"
    echo "2. Pull and merge first (recommended)"
    echo "3. Push to a different branch"
    echo ""
    read -p "Choose option (1/2/3): " OPTION
    
    case $OPTION in
        1)
            echo "⚠️  WARNING: This will overwrite remote repository!"
            read -p "Are you sure? (yes/no): " CONFIRM
            if [ "$CONFIRM" = "yes" ]; then
                git push -u origin $(git branch --show-current) --force
                echo "✅ Force pushed successfully"
            else
                echo "❌ Cancelled"
                exit 1
            fi
            ;;
        2)
            echo "📥 Pulling and merging..."
            git pull origin main --allow-unrelated-histories || git pull origin master --allow-unrelated-histories || true
            git push -u origin $(git branch --show-current)
            echo "✅ Merged and pushed successfully"
            ;;
        3)
            read -p "Enter branch name: " BRANCH_NAME
            git push -u origin $(git branch --show-current):$BRANCH_NAME
            echo "✅ Pushed to branch: $BRANCH_NAME"
            ;;
        *)
            echo "❌ Invalid option"
            exit 1
            ;;
    esac
fi

echo ""
echo "🎉 Done! Check your repository at:"
git remote get-url origin | sed 's/\.git$//'

