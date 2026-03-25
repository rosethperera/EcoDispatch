#!/bin/bash
# Complete GitHub Setup Script for EcoDispatch
# This script will push your project to GitHub

echo "🚀 EcoDispatch GitHub Setup"
echo "=========================="
echo

# Check if we have a GitHub username
if [ -z "$1" ]; then
    echo "❌ Error: Please provide your GitHub username"
    echo "Usage: ./push_to_github.sh YOUR_GITHUB_USERNAME"
    echo "Example: ./push_to_github.sh johnsmith"
    echo
    echo "📋 Before running this script:"
    echo "1. Go to https://github.com"
    echo "2. Click 'New repository'"
    echo "3. Name: ecodispatch"
    echo "4. Description: Carbon-aware data center energy optimization system"
    echo "5. Make it PUBLIC"
    echo "6. DON'T initialize with README"
    echo "7. Click 'Create repository'"
    echo
    echo "Then run: ./push_to_github.sh YOUR_USERNAME"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_URL="https://github.com/$GITHUB_USERNAME/ecodispatch.git"

echo "👤 GitHub Username: $GITHUB_USERNAME"
echo "📦 Repository URL: $REPO_URL"
echo

# Confirm repository exists
echo "🔍 Checking if repository exists..."
if curl -s --head "$REPO_URL" | head -n 1 | grep -q "404"; then
    echo "❌ Repository not found at: $REPO_URL"
    echo "Please create the repository first, then run this script again."
    exit 1
else
    echo "✅ Repository found!"
fi

echo
echo "📤 Pushing to GitHub..."

# Add remote
echo "🔗 Adding GitHub remote..."
git remote add origin "$REPO_URL" 2>/dev/null || echo "Remote 'origin' already exists"

# Switch to main branch
echo "🌿 Switching to main branch..."
git branch -M main

# Push to GitHub
echo "🚀 Pushing code to GitHub..."
if git push -u origin main; then
    echo
    echo "🎉 SUCCESS! Your EcoDispatch is now on GitHub!"
    echo
    echo "🌐 Visit your repository:"
    echo "https://github.com/$GITHUB_USERNAME/ecodispatch"
    echo
    echo "🎯 Next steps:"
    echo "1. Add repository topics: python, optimization, sustainability, data-center"
    echo "2. Pin the repository on your GitHub profile"
    echo "3. Add a demo video or GIF showing 'python demo.py'"
    echo "4. Share on LinkedIn: 'Built a system that reduces data center emissions by 21%'"
    echo
    echo "📊 Your project demonstrates:"
    echo "• Advanced optimization algorithms"
    echo "• Sustainable engineering solutions"
    echo "• Full-stack development skills"
    echo "• Real-world impact (carbon reduction)"
else
    echo
    echo "❌ Push failed. Possible issues:"
    echo "• Wrong GitHub username?"
    echo "• Repository not created yet?"
    echo "• Authentication issues?"
    echo
    echo "Try running: git push -u origin main"
    echo "Or check: git remote -v"
fi