#!/bin/bash
# PPL Meta Platform - Automated Git Push & Release Script
# Prompts for version, commit message, and tag, then commits and pushes to GitHub.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ──────────────────────────────────────────────
# 1. CHECK PREREQUISITES
# ──────────────────────────────────────────────
print_status "Checking prerequisites..."

# Ensure we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not inside a Git repository."
    exit 1
fi

# Ensure git is available
if ! command -v git &> /dev/null; then
    print_error "git is required but not installed."
    exit 1
fi

# Ensure there's a remote configured
if ! git remote -v | grep -q 'origin'; then
    print_error "No remote 'origin' configured. Cannot push."
    exit 1
fi

# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_status "Current branch: ${YELLOW}${CURRENT_BRANCH}${NC}"

# Warn about uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes — they will be included in this commit."
fi

print_success "Prerequisites passed ✓"

# ──────────────────────────────────────────────
# 2. VERSION INPUT
# ──────────────────────────────────────────────
echo ""
CURRENT_VERSION=""
if [ -f VERSION ]; then
    CURRENT_VERSION=$(cat VERSION | tr -d '[:space:]')
    read -r -p "Current version: ${CURRENT_VERSION}. Enter new version (or press Enter to keep it): " NEW_VERSION
else
    print_warning "VERSION file not found. Starting from scratch."
    read -r -p "Enter initial version (e.g., 0.1.0): " NEW_VERSION
fi

if [ -z "$NEW_VERSION" ] && [ -n "$CURRENT_VERSION" ]; then
    NEW_VERSION="$CURRENT_VERSION"
    print_status "Keeping version ${YELLOW}${NEW_VERSION}${NC}"
elif [ -n "$NEW_VERSION" ]; then
    # Update VERSION file
    echo "$NEW_VERSION" > VERSION
    print_success "VERSION updated to ${YELLOW}${NEW_VERSION}${NC}"
fi

# ──────────────────────────────────────────────
# 3. COMMIT MESSAGE INPUT
# ──────────────────────────────────────────────
echo ""
read -r -p "Enter commit message: " COMMIT_MESSAGE
while [ -z "$COMMIT_MESSAGE" ]; do
    print_warning "Commit message cannot be empty."
    read -r -p "Enter commit message: " COMMIT_MESSAGE
done
print_success "Commit message set ✓"

# ──────────────────────────────────────────────
# 4. TAG INPUT
# ──────────────────────────────────────────────
echo ""
CREATE_TAG=false
read -r -p "Create a git tag? (y/n): " TAG_RESPONSE
if [[ "$TAG_RESPONSE" =~ ^[Yy]$ ]]; then
    CREATE_TAG=true
    TAG_NAME="v${NEW_VERSION}"
    read -r -p "Enter tag message (optional, press Enter for default): " TAG_MESSAGE
    if [ -z "$TAG_MESSAGE" ]; then
        TAG_MESSAGE="Release v${NEW_VERSION}"
    fi
    print_success "Tag ${YELLOW}${TAG_NAME}${NC} will be created ✓"
fi

# ──────────────────────────────────────────────
# 5. CONFIRMATION
# ──────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${BLUE}Ready to push to GitHub${NC}"
echo "═══════════════════════════════════════════"
echo -e "  Branch:        ${YELLOW}${CURRENT_BRANCH}${NC}"
echo -e "  Version:       ${YELLOW}${NEW_VERSION}${NC}"
if [ -n "$COMMIT_MESSAGE" ]; then
    echo -e "  Commit msg:    ${YELLOW}${COMMIT_MESSAGE}${NC}"
fi
if [ "$CREATE_TAG" = true ]; then
    echo -e "  Tag:           ${YELLOW}${TAG_NAME}${NC}"
    echo -e "  Tag message:   ${YELLOW}${TAG_MESSAGE}${NC}"
fi
echo "═══════════════════════════════════════════"

read -r -p "Proceed with push? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    print_warning "Aborted by user."
    exit 0
fi

# ──────────────────────────────────────────────
# 6. EXECUTE
# ──────────────────────────────────────────────
echo ""

# Stage all changes
print_status "Staging all changes..."
git add -A
print_success "All changes staged ✓"

# Commit
print_status "Committing..."
git commit -m "$COMMIT_MESSAGE"
print_success "Committed ✓"

# Tag
if [ "$CREATE_TAG" = true ]; then
    # Check if tag already exists
    if git tag | grep -q "^${TAG_NAME}$"; then
        print_warning "Tag ${TAG_NAME} already exists locally. Deleting and recreating..."
        git tag -d "$TAG_NAME"
    fi
    git tag -a "$TAG_NAME" -m "$TAG_MESSAGE"
    print_success "Tag ${YELLOW}${TAG_NAME}${NC} created ✓"
fi

# Push
print_status "Pushing to origin/${CURRENT_BRANCH}..."
git push origin "$CURRENT_BRANCH"
print_success "Pushed to ${YELLOW}origin/${CURRENT_BRANCH}${NC} ✓"

# Push tags
if [ "$CREATE_TAG" = true ]; then
    git push origin "$TAG_NAME"
    print_success "Tag ${YELLOW}${TAG_NAME}${NC} pushed ✓"
fi

# ──────────────────────────────────────────────
# 7. SUMMARY
# ──────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${GREEN}✓ Release complete${NC}"
echo "═══════════════════════════════════════════"
echo -e "  Version:   ${YELLOW}${NEW_VERSION}${NC}"
echo -e "  Branch:    ${YELLOW}${CURRENT_BRANCH}${NC}"
echo -e "  Commit:    ${YELLOW}$COMMIT_MESSAGE${NC}"
if [ "$CREATE_TAG" = true ]; then
    echo -e "  Tag:       ${YELLOW}${TAG_NAME}${NC}"
fi
echo "═══════════════════════════════════════════"