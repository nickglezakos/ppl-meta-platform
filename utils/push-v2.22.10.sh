#!/bin/bash

echo "🚀 Pushing v2.22.10 to GitHub..."
echo ""

cd /Users/nickgklezakos/Documents/ppl-meta-code

# Check current status
echo "📊 Current git status:"
git status
echo ""

# Check if we're in a rebase
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    echo "⚠️  Rebase in progress - aborting it first..."
    git rebase --abort
    echo ""
fi

# Check status again
echo "📊 Git status after cleanup:"
git status
echo ""

# Pull with merge strategy
echo "⬇️  Pulling latest changes from origin/main..."
git pull origin main
echo ""

# Check if there are conflicts
if git diff --name-only --diff-filter=U | grep -q .; then
    echo "❌ Merge conflicts detected. Please resolve manually:"
    git diff --name-only --diff-filter=U
    exit 1
fi

# Push to remote
echo "⬆️  Pushing to origin/main..."
git push origin main
echo ""

# Create and push tag
echo "🏷️  Creating tag v2.22.10..."
git tag -a v2.22.10 -m 'v2.22.10: Fix trigger evaluation integration with instant detection - Complete end-to-end trigger flow'
echo ""

echo "⬆️  Pushing tag to origin..."
git push origin v2.22.10
echo ""

echo "✅ Successfully pushed v2.22.10 to GitHub!"
echo ""
echo "📝 Changes included:"
echo "   - Fixed instant detection → trigger evaluation integration"
echo "   - Fixed payload format (CounterDataRequest with total_count)"
echo "   - Fixed Media Service endpoint variable references"
echo "   - Removed obsolete enable_demographic_conditions filter"
echo "   - Refactored Redis subscriber for new action architecture"
echo "   - Fixed timezone-aware datetime comparisons"
