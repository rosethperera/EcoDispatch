#!/bin/bash
# GitHub Setup Script for EcoDispatch
# Run this to initialize your GitHub repository

echo "🚀 Setting up EcoDispatch for GitHub..."
echo

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: EcoDispatch carbon-aware data center optimizer"
else
    echo "✅ Git repository already initialized"
fi

echo
echo "📋 Next steps for GitHub:"
echo "1. Create a new repository on GitHub.com"
echo "2. Run these commands:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/ecodispatch.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo
echo "3. Enable GitHub Pages for the README"
echo "4. Add topics: python, optimization, sustainability, data-center, carbon-aware"
echo
echo "🎯 Repository Description:"
echo "\"Carbon-aware data center energy optimization prototype with simulation, workload shifting, and hardware integration concepts.\""
