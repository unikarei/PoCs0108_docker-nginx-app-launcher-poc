# ========================================================================
# Git Commit Script (run03_commit.ps1)
#
# Purpose:
#   Stage all current changes, create a single commit, and push it to the
#   current remote branch. This script does not create or push a tag.
#
# Workflow:
#   1. Verify that Git is installed and that the current directory is a repo.
#   2. Detect the current branch and latest tag for display only.
#   3. Prompt the user for a commit message.
#   4. Stage all files with git add -A.
#   5. Create the commit and push it to origin/<branch>.
#   6. If the push is rejected because the branch has diverged, offer an
#      explicit force-push option after confirmation.
#
# Notes:
#   - This is an interactive release helper, not a non-interactive CI script.
#   - Tagging is intentionally separated into run04_tag.sh.
# ========================================================================

# Move to script directory (project root)
Set-Location $PSScriptRoot

# Check Git availability
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[Error] Git is not installed or not in PATH." -ForegroundColor Red
    pause
    exit 1
}

# Check inside a Git repository
try {
    git rev-parse --is-inside-work-tree 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw
    }
} catch {
    Write-Host "[Error] This directory is not a Git repository." -ForegroundColor Red
    pause
    exit 1
}

# Detect current branch
$CUR_BRANCH = git rev-parse --abbrev-ref HEAD 2>$null
if ([string]::IsNullOrEmpty($CUR_BRANCH)) {
    $CUR_BRANCH = "main"
}

# Get latest tag as reference
$LATEST_TAG = git tag --sort=-version:refname 2>$null | Select-Object -First 1
if ([string]::IsNullOrEmpty($LATEST_TAG)) {
    $LATEST_TAG = "v0.0.0"
}

Write-Host "========================================"
Write-Host "         Git Commit Script"
Write-Host "========================================"
Write-Host "Current branch : $CUR_BRANCH"
Write-Host "Latest tag     : $LATEST_TAG"
Write-Host ""

# Ask user to input commit message (interactive)
$COMMIT_MSG = Read-Host "Enter commit message"
if ([string]::IsNullOrEmpty($COMMIT_MSG)) {
    Write-Host "[Error] Commit message cannot be empty." -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Staging changes..."
# Stage all changes
git add -A

# Check if there are staged changes
$STATUS = git status --porcelain
if ([string]::IsNullOrEmpty($STATUS)) {
    Write-Host "[Info] No changes to commit." -ForegroundColor Yellow
    pause
    exit 0
}

Write-Host "Creating commit with message:"
Write-Host "  $COMMIT_MSG"
git commit -m "$COMMIT_MSG"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] Commit failed." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Pushing to origin/$CUR_BRANCH ..."
git push origin $CUR_BRANCH
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[Error] Push failed." -ForegroundColor Red
    Write-Host "Remote may have commits that are not present locally (non-fast-forward)."
    $FORCE_PUSH = Read-Host "Force push to overwrite remote history? [y/N]"
    if ($FORCE_PUSH -eq "Y" -or $FORCE_PUSH -eq "y") {
        Write-Host "Force pushing to origin/$CUR_BRANCH ..."
        git push -f origin $CUR_BRANCH
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[Error] Force push failed." -ForegroundColor Red
            Write-Host "[Info] Try: git pull --rebase origin $CUR_BRANCH then push again."
            pause
            exit 1
        } else {
            Write-Host ""
            Write-Host "[Success] Force push completed on branch $CUR_BRANCH." -ForegroundColor Green
        }
    } else {
        Write-Host "[Info] Cancelled. Try: git pull --rebase origin $CUR_BRANCH then push again."
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "[Success] Commit and push completed on branch $CUR_BRANCH." -ForegroundColor Green
Write-Host "(Tagging is now separated. Use run04_tag.ps1 to create/push a tag.)"
Write-Host ""
pause
