@echo off
REM Complete GitHub Setup Script for EcoDispatch (Windows)
REM This script will push your project to GitHub

echo 🚀 EcoDispatch GitHub Setup
echo ==========================
echo.

REM Check if we have a GitHub username
if "%1"=="" (
    echo ❌ Error: Please provide your GitHub username
    echo Usage: push_to_github.bat YOUR_GITHUB_USERNAME
    echo Example: push_to_github.bat johnsmith
    echo.
    echo 📋 Before running this script:
    echo 1. Go to https://github.com
    echo 2. Click 'New repository'
    echo 3. Name: ecodispatch
    echo 4. Description: Carbon-aware data center energy optimization system
    echo 5. Make it PUBLIC
    echo 6. DON'T initialize with README
    echo 7. Click 'Create repository'
    echo.
    echo Then run: push_to_github.bat YOUR_USERNAME
    goto :eof
)

set GITHUB_USERNAME=%1
set REPO_URL=https://github.com/%GITHUB_USERNAME%/ecodispatch.git

echo 👤 GitHub Username: %GITHUB_USERNAME%
echo 📦 Repository URL: %REPO_URL%
echo.

echo 🔍 Checking if repository exists...
REM Note: Windows curl might not be available, so we'll skip this check
echo ⚠️  Skipping repository check (curl not available in Windows)
echo Assuming repository exists...
echo.

echo 📤 Pushing to GitHub...

REM Add remote
echo 🔗 Adding GitHub remote...
git remote add origin "%REPO_URL%" 2>nul || echo Remote 'origin' already exists

REM Switch to main branch
echo 🌿 Switching to main branch...
git branch -M main

REM Push to GitHub
echo 🚀 Pushing code to GitHub...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo 🎉 SUCCESS! Your EcoDispatch is now on GitHub!
    echo.
    echo 🌐 Visit your repository:
    echo https://github.com/%GITHUB_USERNAME%/ecodispatch
    echo.
    echo 🎯 Next steps:
    echo 1. Add repository topics: python, optimization, sustainability, data-center
    echo 2. Pin the repository on your GitHub profile
    echo 3. Add a demo video or GIF showing 'python demo.py'
    echo 4. Share on LinkedIn: 'Built a simulation prototype for carbon-aware data center energy optimization'
    echo.
    echo 📊 Your project demonstrates:
    echo • Advanced optimization algorithms
    echo • Sustainable engineering solutions
    echo • Full-stack development skills
    echo • Real-world impact (carbon reduction)
) else (
    echo.
    echo ❌ Push failed. Possible issues:
    echo • Wrong GitHub username?
    echo • Repository not created yet?
    echo • Authentication issues?
    echo.
    echo Try these commands manually:
    echo git remote add origin "%REPO_URL%"
    echo git branch -M main
    echo git push -u origin main
    echo.
    echo Or check: git remote -v
)
