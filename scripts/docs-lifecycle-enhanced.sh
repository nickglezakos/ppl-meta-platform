#!/bin/bash

# PPL Meta Platform - Document Lifecycle Management Script with GitHub Projects Integration
# This script helps move documents through the lifecycle: planning → current → final
# Now with GitHub Projects integration support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCS_DIR="docs"
PROJECT_URL="https://github.com/users/nickglezakos/projects/1"
PROJECT_ID="PVT_kwHOAHCOYs4AfGfN"
REPO_OWNER="nickglezakos"
REPO_NAME="ppl-meta-platform"

# Version and release management functions
bump_version() {
    local bump_type=$1  # major, minor, or patch
    local update_file=${2:-false}
    
    if [[ -z "$bump_type" ]]; then
        echo -e "${RED}Error: Version bump type required (major, minor, or patch)${NC}"
        echo "Usage: $0 bump-version [major|minor|patch] [--update-file]"
        exit 1
    fi
    
    # Validate bump type
    if [[ ! "$bump_type" =~ ^(major|minor|patch)$ ]]; then
        echo -e "${RED}Error: Invalid bump type '$bump_type'. Use: major, minor, or patch${NC}"
        exit 1
    fi
    
    # Read current version from VERSION file
    local version_file="VERSION"
    if [[ ! -f "$version_file" ]]; then
        echo -e "${RED}Error: VERSION file not found${NC}"
        echo "Creating VERSION file with initial version 1.0.0"
        echo "1.0.0" > "$version_file"
    fi
    
    local current_version=$(cat "$version_file" | tr -d '[:space:]')
    
    # Validate current version format
    if [[ ! "$current_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${RED}Error: Invalid version format in VERSION file: '$current_version'${NC}"
        echo "Expected format: X.Y.Z (e.g., 2.13.0)"
        exit 1
    fi
    
    # Parse version components
    IFS='.' read -r major minor patch <<< "$current_version"
    
    # Calculate new version based on bump type
    case "$bump_type" in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    
    echo -e "${CYAN}🔄 Version Bump: $bump_type${NC}"
    echo -e "${BLUE}Current Version: $current_version${NC}"
    echo -e "${GREEN}New Version: $new_version${NC}"
    echo ""
    
    # Update VERSION file if requested
    if [[ "$update_file" == "true" ]]; then
        echo "$new_version" > "$version_file"
        echo -e "${GREEN}✅ VERSION file updated: $current_version → $new_version${NC}"
        
        # Add to git if in a git repository
        if git rev-parse --git-dir >/dev/null 2>&1; then
            git add "$version_file" 2>/dev/null || true
            echo -e "${CYAN}📝 VERSION file staged for commit${NC}"
        fi
    else
        echo -e "${YELLOW}💡 Add --update-file to update the VERSION file${NC}"
    fi
    
    echo ""
    echo -e "${PURPLE}🎯 Next Steps:${NC}"
    echo -e "${CYAN}1. Create version milestone:${NC}"
    echo "   ./scripts/docs-lifecycle-enhanced.sh create-version-milestone v$new_version \"YYYY-MM-DD\" \"Release description\""
    echo -e "${CYAN}2. Plan features for this version${NC}"
    echo -e "${CYAN}3. When ready, create release:${NC}"
    echo "   ./scripts/docs-lifecycle-enhanced.sh create-release v$new_version --auto-notes"
    echo ""
    
    return 0
}

create_version_milestone() {
    local version=$1
    local due_date=$2
    local description=$3
    
    if [[ -z "$version" || -z "$due_date" ]]; then
        echo -e "${RED}Error: Version and due date required${NC}"
        echo "Usage: $0 create-version \"v1.2.0\" \"YYYY-MM-DD\" \"Release description\""
        exit 1
    fi
    
    # Validate semantic version format
    if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${YELLOW}⚠️  Warning: Version '$version' doesn't follow semantic versioning (vX.Y.Z)${NC}"
    fi
    
    local milestone_title="$version Release"
    local full_description="🚀 Release $version

$description

## 📋 Release Scope
- [ ] All planned features implemented
- [ ] Documentation updated
- [ ] Testing completed
- [ ] Security review passed
- [ ] Performance benchmarks met

## 🏁 Release Checklist
- [ ] Version bumped in all relevant files
- [ ] Changelog updated
- [ ] Release notes prepared
- [ ] Tag created: $version
- [ ] GitHub Release published"
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🚀 Creating release milestone: $version${NC}"
        
        # Convert date to ISO format
        local iso_date="${due_date}T23:59:59Z"
        
        if gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --method POST \
           --field title="$milestone_title" \
           --field description="$full_description" \
           --field due_on="$iso_date" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Release milestone created successfully${NC}"
            echo -e "${BLUE}📅 Target release date: $due_date${NC}"
            echo -e "${BLUE}🏷️  Version: $version${NC}"
        else
            echo -e "${RED}❌ Failed to create release milestone${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for milestone creation${NC}"
    fi
}

create_release_auto() {
    local version=$1
    
    if [[ -z "$version" ]]; then
        echo -e "${RED}Error: Version required${NC}"
        echo "Usage: $0 create-release v1.2.0 --auto-notes"
        exit 1
    fi
    
    # Ensure version starts with 'v'
    if [[ ! "$version" =~ ^v ]]; then
        version="v$version"
    fi
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🚀 Creating GitHub release with auto-generated notes${NC}"
        
        # Get the last tag for comparison
        local last_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        local compare_ref=""
        if [[ -n "$last_tag" ]]; then
            compare_ref="$last_tag.."
        fi
        
        # Generate release notes
        local release_notes="# $version Release

🚀 **New version released!**

## 📈 Changes Since Last Release

$(if [[ -n "$last_tag" ]]; then
    echo "### 📋 Commits"
    git log --oneline --pretty="- %s (%h)" "$compare_ref"HEAD 2>/dev/null | head -20
    echo ""
    echo "### 📊 Stats"
    echo "- **Commits**: $(git rev-list --count "$compare_ref"HEAD 2>/dev/null || echo "N/A")"
    echo "- **Files Changed**: $(git diff --name-only "$last_tag" HEAD 2>/dev/null | wc -l | tr -d ' ' || echo "N/A")"
else
    echo "Initial release"
fi)

## 🔗 Links

- **Full Changelog**: [Compare changes](https://github.com/$REPO_OWNER/$REPO_NAME/compare/${last_tag:-$(git rev-list --max-parents=0 HEAD)}...$version)
- **Repository**: https://github.com/$REPO_OWNER/$REPO_NAME

---
*Release generated automatically by docs-lifecycle-enhanced.sh*"
        
        # Create the GitHub release
        if gh release create "$version" --title "$version" --notes "$release_notes" --target main; then
            echo -e "${GREEN}✅ GitHub release created successfully${NC}"
            echo -e "${BLUE}🔗 Release URL: https://github.com/$REPO_OWNER/$REPO_NAME/releases/tag/$version${NC}"
            
            # Tag locally if not already tagged
            if ! git tag -l | grep -q "^${version}$"; then
                git tag "$version" 2>/dev/null || true
                echo -e "${GREEN}✅ Local tag created: $version${NC}"
            fi
        else
            echo -e "${RED}❌ Failed to create GitHub release${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for release creation${NC}"
        echo -e "${CYAN}Manual release steps:${NC}"
        echo "1. Create and push tag: git tag $version && git push origin $version"
        echo "2. Create release at: https://github.com/$REPO_OWNER/$REPO_NAME/releases/new"
    fi
}

create_release_from_milestone() {
    local milestone_number=$1
    local version=$2
    
    if [[ -z "$milestone_number" || -z "$version" ]]; then
        echo -e "${RED}Error: Milestone number and version required${NC}"
        echo "Usage: $0 create-release <milestone-number> \"v1.2.0\""
        exit 1
    fi
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🚀 Creating GitHub release from milestone${NC}"
        
        # Get milestone details
        local milestone_info=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones/"$milestone_number" 2>/dev/null)
        local milestone_title=$(echo "$milestone_info" | jq -r '.title')
        local milestone_desc=$(echo "$milestone_info" | jq -r '.description')
        
        # Generate release notes from closed issues in milestone
        local release_notes="# $version Release

$milestone_desc

## 🆕 What's New

$(gh issue list --milestone "$milestone_number" --state closed --json title,number --jq '.[] | "- #\(.number): \(.title)"' | head -20)

## 📊 Release Stats

- **Issues Resolved**: $(gh issue list --milestone "$milestone_number" --state closed --json number | jq length)
- **Milestone**: $milestone_title
- **Release Date**: $(date '+%Y-%m-%d')

## 🔗 Full Changelog

View all changes: [Compare $version](https://github.com/$REPO_OWNER/$REPO_NAME/compare/$(git describe --tags --abbrev=0 2>/dev/null || echo 'HEAD^')...$version)"
        
        # Create the GitHub release
        if gh release create "$version" --title "$version Release" --notes "$release_notes" --target main; then
            echo -e "${GREEN}✅ GitHub release created successfully${NC}"
            echo -e "${BLUE}🔗 Release URL: https://github.com/$REPO_OWNER/$REPO_NAME/releases/tag/$version${NC}"
            
            # Close the milestone
            gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones/"$milestone_number" --method PATCH --field state="closed" >/dev/null 2>&1
            echo -e "${GREEN}✅ Milestone closed${NC}"
        else
            echo -e "${RED}❌ Failed to create GitHub release${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for release creation${NC}"
    fi
}

show_version_status() {
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}🚀 Version & Release Status${NC}"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        
        # Get current version from git tags
        local current_version=$(git describe --tags --abbrev=0 2>/dev/null || echo "No releases yet")
        echo -e "${CYAN}Current Released Version: ${GREEN}$current_version${NC}"
        echo ""
        
        # Show active release milestones (version-based)
        echo -e "${CYAN}🎯 Upcoming Releases:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.state == "open") | select(.title | contains("Release") or contains("v")) | "  🚀 \(.title) - Due: \(.due_on // "No due date") - Progress: \(.closed_issues)/\(.open_issues + .closed_issues)"' 2>/dev/null || echo -e "${YELLOW}  No active release milestones${NC}"
        
        echo ""
        echo -e "${CYAN}✅ Recent Releases:${NC}"
        gh release list --limit 5 --json tagName,name,publishedAt --jq '.[] | "  🏷️  \(.tagName) - \(.name) - \(.publishedAt[:10])"' 2>/dev/null || echo -e "${YELLOW}  No releases found${NC}"
        
        echo ""
        echo -e "${CYAN}📋 Release Milestones:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones?state=closed --jq '.[] | select(.title | contains("Release") or contains("v")) | "  ✅ \(.title) - Completed: \(.closed_at[:10]) - Issues: \(.closed_issues)"' 2>/dev/null || echo -e "${YELLOW}  No completed release milestones${NC}"
        
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for version status${NC}"
    fi
}

# Sprint management functions
# Version management functions
get_current_version() {
    if [[ -f "VERSION" ]]; then
        cat VERSION | tr -d '\n'
    else
        echo "0.0.0"
    fi
}

update_version_file() {
    local new_version=$1
    echo "$new_version" > VERSION
    echo -e "${GREEN}✅ VERSION file updated to: $new_version${NC}"
}

suggest_next_version() {
    local current_version=$(get_current_version)
    local major=$(echo "$current_version" | cut -d. -f1)
    local minor=$(echo "$current_version" | cut -d. -f2)
    local patch=$(echo "$current_version" | cut -d. -f3)
    
    echo -e "${CYAN}Current version: $current_version${NC}"
    echo -e "${BLUE}Suggested next versions:${NC}"
    echo -e "  🔧 Patch: $major.$minor.$((patch + 1)) (bug fixes)"
    echo -e "  ⚡ Minor: $major.$((minor + 1)).0 (new features)"
    echo -e "  🚀 Major: $((major + 1)).0.0 (breaking changes)"
}

create_version_milestone() {
    local version=$1
    local due_date=$2
    local description=${3:-"Release $version"}
    local update_version_file=${4:-false}
    
    if [[ -z "$version" || -z "$due_date" ]]; then
        echo -e "${RED}Error: Version and due date required${NC}"
        suggest_next_version
        echo ""
        echo "Usage: $0 create-version \"v1.0.0\" \"YYYY-MM-DD\" \"Description\" [--update-file]"
        exit 1
    fi
    
    # Validate version format
    if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${RED}Error: Version must be in format v1.2.3${NC}"
        exit 1
    fi
    
    # Extract numeric version (remove 'v' prefix)
    local numeric_version=$(echo "$version" | sed 's/^v//')
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🚀 Creating version milestone: $version${NC}"
        
        # Convert date to ISO format
        local iso_date="${due_date}T23:59:59Z"
        
        # Create milestone with version-aware title
        local milestone_title="$version - $(echo "$description" | sed "s/Release $version//" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
        if [[ "$milestone_title" == "$version -" ]]; then
            milestone_title="$version"
        fi
        
        if gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --method POST \
           --field title="$milestone_title" \
           --field description="$description" \
           --field due_on="$iso_date" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Version milestone created successfully${NC}"
            echo -e "${BLUE}📅 Due date: $due_date${NC}"
            echo -e "${BLUE}🎯 Target version: $version${NC}"
            
            # Update VERSION file if requested
            if [[ "$update_version_file" == "true" ]]; then
                update_version_file "$numeric_version"
                echo -e "${BLUE}📄 VERSION file updated${NC}"
            fi
            
            echo ""
            echo -e "${CYAN}Next steps:${NC}"
            echo -e "  1. Assign issues to this version milestone"
            echo -e "  2. Track progress until release date"
            echo -e "  3. Create GitHub release when complete"
            
        else
            echo -e "${RED}❌ Failed to create version milestone${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for milestone creation${NC}"
    fi
}

assign_issue_to_sprint() {
    local issue_number=$1
    local milestone_number=$2
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🏃 Assigning issue #$issue_number to sprint (milestone #$milestone_number)${NC}"
        
        if gh issue edit "$issue_number" --milestone "$milestone_number" --repo "$REPO_OWNER/$REPO_NAME" 2>/dev/null; then
            echo -e "${GREEN}✅ Issue assigned to sprint successfully${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not assign issue to sprint${NC}"
        fi
    fi
}

show_sprint_status() {
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}🏃 Sprint Status${NC}"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        
        # Get current milestones
        echo -e "${CYAN}Active Sprints (Milestones):${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.state == "open") | "  🏃 \(.title) - Due: \(.due_on // "No due date") - Issues: \(.open_issues)/\(.open_issues + .closed_issues)"' 2>/dev/null || echo -e "${YELLOW}  No active sprints found${NC}"
        
        echo ""
        echo -e "${CYAN}Completed Sprints:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones?state=closed --jq '.[] | "  ✅ \(.title) - Completed: \(.closed_at // "Unknown") - Issues: \(.closed_issues)/\(.open_issues + .closed_issues)"' 2>/dev/null || echo -e "${YELLOW}  No completed sprints found${NC}"
        
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for sprint status${NC}"
    fi
}

# Enhanced Milestone Management Functions
assign_multiple_milestones() {
    local issue_number=$1
    local version_milestone=""
    local sprint_milestone=""
    local feature_milestone=""
    local generic_milestone=""
    
    if [[ -z "$issue_number" ]]; then
        echo -e "${RED}Error: Issue number required${NC}"
        echo "Usage: $0 assign-milestones <issue-number> [--version <milestone>] [--sprint <milestone>] [--feature <milestone>] [--generic <milestone>]"
        exit 1
    fi
    
    # Parse milestone arguments
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                version_milestone="$2"
                shift 2
                ;;
            --sprint)
                sprint_milestone="$2"
                shift 2
                ;;
            --feature)
                feature_milestone="$2"
                shift 2
                ;;
            --generic)
                generic_milestone="$2"
                shift 2
                ;;
            *)
                echo -e "${YELLOW}⚠️  Unknown option: $1${NC}"
                shift
                ;;
        esac
    done
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🎯 Assigning multiple milestone types to issue #$issue_number${NC}"
        
        # Primary milestone assignment (GitHub native - priority: version > generic > sprint > feature)
        local primary_milestone=""
        local primary_type=""
        
        if [[ -n "$version_milestone" ]]; then
            primary_milestone="$version_milestone"
            primary_type="version"
        elif [[ -n "$generic_milestone" ]]; then
            primary_milestone="$generic_milestone"
            primary_type="generic"
        elif [[ -n "$sprint_milestone" ]]; then
            primary_milestone="$sprint_milestone"
            primary_type="sprint"
        elif [[ -n "$feature_milestone" ]]; then
            primary_milestone="$feature_milestone"
            primary_type="feature"
        fi
        
        # Assign primary milestone
        if [[ -n "$primary_milestone" ]]; then
            if gh issue edit "$issue_number" --milestone "$primary_milestone" 2>/dev/null; then
                echo -e "${GREEN}✅ Primary milestone assigned: $primary_milestone ($primary_type)${NC}"
            else
                echo -e "${YELLOW}⚠️  Primary milestone '$primary_milestone' may not exist, creating it...${NC}"
                # Try to create milestone if it doesn't exist
                create_milestone_if_not_exists "$primary_milestone"
                gh issue edit "$issue_number" --milestone "$primary_milestone" 2>/dev/null || echo -e "${RED}❌ Failed to assign primary milestone${NC}"
            fi
        fi
        
        # Assign secondary milestones as labels
        local labels_to_add=()
        
        if [[ -n "$sprint_milestone" && "$primary_type" != "sprint" ]]; then
            local sprint_label="sprint:$(echo "$sprint_milestone" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
            labels_to_add+=("$sprint_label")
        fi
        
        if [[ -n "$feature_milestone" && "$primary_type" != "feature" ]]; then
            local feature_label="feature:$(echo "$feature_milestone" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
            labels_to_add+=("$feature_label")
        fi
        
        if [[ -n "$version_milestone" && "$primary_type" != "version" ]]; then
            local version_label="version:$(echo "$version_milestone" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
            labels_to_add+=("$version_label")
        fi
        
        if [[ -n "$generic_milestone" && "$primary_type" != "generic" ]]; then
            local generic_label="generic:$(echo "$generic_milestone" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
            labels_to_add+=("$generic_label")
        fi
        
        # Add labels for secondary milestones
        for label in "${labels_to_add[@]}"; do
            if gh issue edit "$issue_number" --add-label "$label" 2>/dev/null; then
                echo -e "${GREEN}✅ Secondary milestone label added: $label${NC}"
            else
                echo -e "${YELLOW}⚠️  Failed to add label: $label${NC}"
            fi
        done
        
        echo -e "${CYAN}📊 Milestone assignment summary for issue #$issue_number:${NC}"
        [[ -n "$version_milestone" ]] && echo -e "  🔖 Version: $version_milestone"
        [[ -n "$sprint_milestone" ]] && echo -e "  🏃 Sprint: $sprint_milestone"
        [[ -n "$feature_milestone" ]] && echo -e "  ⚡ Feature: $feature_milestone"
        [[ -n "$generic_milestone" ]] && echo -e "  📋 Generic: $generic_milestone"
        
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for milestone assignment${NC}"
    fi
}

create_milestone_if_not_exists() {
    local milestone_title=$1
    local due_date=${2:-""}
    local description=${3:-"Auto-created milestone"}
    
    # Check if milestone exists
    local exists=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq ".[] | select(.title == \"$milestone_title\") | .title" 2>/dev/null)
    
    if [[ -z "$exists" ]]; then
        echo -e "${CYAN}📝 Creating milestone: $milestone_title${NC}"
        local milestone_data="{\"title\":\"$milestone_title\",\"description\":\"$description\""
        
        if [[ -n "$due_date" ]]; then
            milestone_data+=",\"due_on\":\"${due_date}T23:59:59Z\""
        fi
        milestone_data+="}"
        
        if gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --method POST --input - <<< "$milestone_data" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Milestone created: $milestone_title${NC}"
        else
            echo -e "${RED}❌ Failed to create milestone: $milestone_title${NC}"
        fi
    fi
}

list_milestone_types() {
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}🎯 Milestone Types Overview${NC}"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        
        echo -e "${CYAN}🔖 Version Milestones (Primary):${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.title | test("^v[0-9]")) | "  📦 \(.title) - Issues: \(.open_issues + .closed_issues) - Due: \(.due_on // "No date")"' 2>/dev/null || echo -e "${YELLOW}  No version milestones${NC}"
        
        echo ""
        echo -e "${CYAN}🏃 Sprint Milestones:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.title | test("(?i)sprint")) | "  🏃 \(.title) - Issues: \(.open_issues + .closed_issues) - Due: \(.due_on // "No date")"' 2>/dev/null || echo -e "${YELLOW}  No sprint milestones${NC}"
        
        echo ""
        echo -e "${CYAN}📋 Generic Milestones:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.title | test("^v[0-9]|(?i)sprint") | not) | "  📋 \(.title) - Issues: \(.open_issues + .closed_issues) - Due: \(.due_on // "No date")"' 2>/dev/null || echo -e "${YELLOW}  No generic milestones${NC}"
        
        echo ""
        echo -e "${CYAN}🏷️  Secondary Milestone Labels:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/labels --jq '.[] | select(.name | test("^(version|feature|generic|sprint):")) | "  🏷️  \(.name) - \(.description // "No description")"' 2>/dev/null || echo -e "${YELLOW}  No secondary milestone labels${NC}"
        
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for milestone listing${NC}"
    fi
}

milestone_report() {
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}📊 Milestone Distribution Report${NC}"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        
        # Get all issues with milestones
        echo -e "${CYAN}📈 Issues by Primary Milestone:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/issues --paginate --jq '.[] | select(.milestone != null) | .milestone.title' 2>/dev/null | sort | uniq -c | sort -nr | while read count milestone; do
            echo -e "  📌 $milestone: ${GREEN}$count issues${NC}"
        done
        
        echo ""
        echo -e "${CYAN}🏷️  Issues by Secondary Milestone Labels:${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/issues --paginate --jq '.[] | .labels[] | select(.name | test("^(version|feature|generic|sprint):")) | .name' 2>/dev/null | sort | uniq -c | sort -nr | while read count label; do
            echo -e "  🏷️  $label: ${GREEN}$count issues${NC}"
        done
        
        echo ""
        echo -e "${CYAN}📊 Summary Statistics:${NC}"
        local total_issues=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/issues --paginate --jq 'length' 2>/dev/null)
        local issues_with_milestones=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/issues --paginate --jq '.[] | select(.milestone != null) | 1' 2>/dev/null | wc -l | tr -d ' ')
        local issues_with_secondary=$(gh api repos/"$REPO_OWNER"/"$REPO_NAME"/issues --paginate --jq '.[] | select(.labels[] | .name | test("^(version|feature|generic|sprint):")) | 1' 2>/dev/null | wc -l | tr -d ' ')
        
        echo -e "  📋 Total Issues: ${BLUE}$total_issues${NC}"
        echo -e "  🎯 Issues with Primary Milestone: ${GREEN}$issues_with_milestones${NC}"
        echo -e "  🏷️  Issues with Secondary Milestones: ${GREEN}$issues_with_secondary${NC}"
        
        if [[ "$total_issues" -gt 0 ]]; then
            local primary_percentage=$((issues_with_milestones * 100 / total_issues))
            local secondary_percentage=$((issues_with_secondary * 100 / total_issues))
            echo -e "  📊 Primary Milestone Coverage: ${GREEN}${primary_percentage}%${NC}"
            echo -e "  📊 Secondary Milestone Coverage: ${GREEN}${secondary_percentage}%${NC}"
        fi
        
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for milestone report${NC}"
    fi
}

show_version_status() {
    local current_version=$(get_current_version)
    
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}🚀 Version & Release Status${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Current Project Version:${NC}"
    echo -e "  📄 VERSION file: ${GREEN}$current_version${NC}"
    echo ""
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}Version Milestones (Planned Releases):${NC}"
        gh api repos/"$REPO_OWNER"/"$REPO_NAME"/milestones --jq '.[] | select(.state == "open") | select(.title | test("^v[0-9]+\\.[0-9]+\\.[0-9]+")) | "  🎯 \(.title) - Due: \(.due_on // "No due date") - Progress: \(.closed_issues)/\(.open_issues + .closed_issues)"' 2>/dev/null || echo -e "${YELLOW}  No version milestones found${NC}"
        
        echo ""
        echo -e "${CYAN}Published Releases:${NC}"
        gh release list --limit 5 --json tagName,name,publishedAt,isLatest --template '{{range .}}  🚀 {{.tagName}} - {{.name}} - {{.publishedAt}}{{if .isLatest}} (Latest){{end}}
{{end}}' 2>/dev/null || echo -e "${YELLOW}  No releases found${NC}"
        
        echo ""
        suggest_next_version
        
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available for release status${NC}"
    fi
    
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
}

# GitHub CLI automation functions
create_project_item() {
    local issue_number=$1
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🔄 Adding issue #$issue_number to project...${NC}"
        if gh project item-add "$PROJECT_ID" --owner "$REPO_OWNER" --url "https://github.com/$REPO_OWNER/$REPO_NAME/issues/$issue_number" 2>/dev/null; then
            echo -e "${GREEN}✅ Issue added to project successfully${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not add to project (issue may not exist or already added)${NC}"
        fi
    fi
}

update_project_status() {
    local issue_number=$1
    local status=$2
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🔄 Updating project status to: $status${NC}"
        # Map internal status to your exact column names
        case $status in
            "Planned"|"Planning")
                local column_name="Planned"
                ;;
            "In Progress"|"Active"|"Development")
                local column_name="In progress"
                ;;
            "Review"|"Under Review"|"Pending Review")
                local column_name="Review"
                ;;
            "Done"|"Complete"|"Completed")
                local column_name="Done"
                ;;
            *)
                local column_name="$status"
                ;;
        esac
        
        # Note: GitHub CLI project status updates require specific field configuration
        # This is a placeholder for when project fields are configured
        echo -e "${BLUE}💡 Manually move project card to '$column_name' column${NC}"
        
        # Future enhancement: When GitHub CLI supports direct column updates
        # gh project item-edit --project-id "$PROJECT_ID" --field "Status" --value "$column_name"
    fi
}

close_github_issue() {
    local issue_number=$1
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🔄 Closing issue #$issue_number...${NC}"
        if gh issue close "$issue_number" --repo "$REPO_OWNER/$REPO_NAME" 2>/dev/null; then
            echo -e "${GREEN}✅ Issue #$issue_number closed successfully${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not close issue #$issue_number${NC}"
        fi
    fi
}

# GitHub CLI check
check_gh_cli() {
    if command -v gh &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Usage function
usage() {
    echo -e "${BLUE}PPL Meta Platform - Document Lifecycle Management${NC}"
    echo -e "${CYAN}With GitHub Projects Integration & Enhanced Milestone Management${NC}"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "📋 Document Lifecycle Commands:"
    echo "  create <issue-number> <description>       - Create new planning document from template"
    echo "  activate <issue-number> <description>     - Move document from planning to current"
    echo "  review <document-name>                    - Mark document as ready for review"
    echo "  complete <document-name> <category>       - Move document from current to final category"
    echo "  list <stage>                              - List documents in specific stage"
    echo ""
    echo "🚀 Version Management Commands:"
    echo "  bump-version <major|minor|patch>          - Bump version in VERSION file"
    echo "  create-version-milestone <ver> <date> <desc> - Create release milestone"
    echo "  create-release <version> --auto-notes     - Create GitHub release with auto-generated notes"
    echo "  version-status                            - Show version and release status"
    echo ""
    echo "🎯 Enhanced Milestone Management Commands:"
    echo "  assign-milestones <issue> [--version <v>] [--sprint <s>] [--feature <f>] [--generic <g>]"
    echo "                                            - Assign multiple milestone types to issue"
    echo "  assign-sprint <issue> <sprint> [--version <v>] [--feature <f>] [--generic <g>]"
    echo "                                            - Sprint-optimized assignment (NEW!)"
    echo "  list-milestone-types                      - Show all milestone types and their issues"
    echo "  milestone-report                          - Generate comprehensive milestone distribution report"
    echo ""
    echo "🏃 Sprint Management Commands:"
    echo "  create-sprint <name> <due-date> <desc>    - Create new sprint milestone"
    echo "  sprint-status                             - Show current sprint status"
    echo "  sprint-progress <milestone-name>          - Show progress for specific sprint"
    echo ""
    echo "📋 Document-Issue Sync Commands (NEW!):"
    echo "  generate-issue-content <document-path>    - Generate GitHub-ready content from document"
    echo ""
    echo "📊 Status & Integration Commands:"
    echo "  status                                    - Show status of all documents"
    echo "  project-sync                              - Show GitHub Projects integration status"
    echo ""
    echo "🔧 Options:"
    echo "  --link-issue                              - Include GitHub issue linking"
    echo "  --update-project                          - Update GitHub Project (requires gh CLI)"
    echo "  --close-issue                             - Close GitHub issue when completing"
    echo "  --update-file                             - Update VERSION file during bump-version"
    echo "  --sprint <milestone-name>                 - Assign issue to specific sprint milestone"
    echo "  --version <milestone-name>                - Assign issue to specific version milestone"
    echo "  --feature <milestone-name>                - Assign issue to specific feature milestone"
    echo "  --generic <milestone-name>                - Assign issue to specific generic milestone"
    echo ""
    echo "📁 Available Stages:"
    echo "  planning, current, architecture, development, deployment, api, troubleshooting, research"
    echo ""
    echo "💡 Examples:"
    echo "  # Sprint-Optimized Workflow (NEW!)"
    echo "  $0 assign-sprint 5 \"Sprint 6\" --version \"v2.14.0\" --feature \"API Enhancement\""
    echo "  $0 generate-issue-content docs/planning/ISSUE-5-api-enhancement-PLAN.md"
    echo ""
    echo "  # Enhanced Milestone Management"
    echo "  $0 assign-milestones 5 --version \"v2.14.0\" --sprint \"Sprint 5\" --feature \"API Enhancement\""
    echo "  $0 list-milestone-types"
    echo "  $0 milestone-report"
    echo ""
    echo "  # Version Management"
    echo "  $0 bump-version minor --update-file       # 2.13.0 → 2.14.0"
    echo "  $0 bump-version patch --update-file       # 2.13.0 → 2.13.1"
    echo "  $0 bump-version major --update-file       # 2.13.0 → 3.0.0"
    echo "  $0 create-version-milestone v2.14.0 \"2025-12-31\" \"API enhancements\""
    echo "  $0 create-release v2.14.0 --auto-notes"
    echo ""
    echo "  # Document Lifecycle with Multiple Milestones"
    echo "  $0 create 123 \"network-discovery\" --link-issue --version \"v2.14.0\" --sprint \"Sprint 5\""
    echo "  $0 activate 123 \"network-discovery\" --update-project"
    echo "  $0 review ISSUE-123-network-discovery-ACTIVE.md"
    echo "  $0 complete ISSUE-123-network-discovery-ACTIVE.md development --close-issue"
    echo ""
    echo "  # Sprint Management"
    echo "  $0 create-sprint \"Sprint 5\" \"2025-10-31\" \"Frontend improvements\""
    echo "  $0 sprint-progress \"Sprint 5\""
    echo ""
    echo "  # Status & Monitoring"
    echo "  $0 version-status"
    echo "  $0 sprint-status"
    echo "  $0 project-sync"
}

# GitHub Projects integration info
show_project_integration() {
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}📊 GitHub Projects Integration Status${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Project Configuration:${NC}"
    echo -e "  🔗 Project URL: ${BLUE}$PROJECT_URL${NC}"
    echo -e "  📁 Repository: ${BLUE}$REPO_OWNER/$REPO_NAME${NC}"
    echo ""
    
    if check_gh_cli; then
        echo -e "${GREEN}✅ GitHub CLI Available${NC}"
        if gh auth status &>/dev/null; then
            echo -e "${GREEN}✅ GitHub CLI Authenticated${NC}"
            echo ""
            echo -e "${CYAN}Available GitHub CLI Features:${NC}"
            echo -e "  • Automatic project card creation"
            echo -e "  • Issue status synchronization" 
            echo -e "  • Project column updates"
            echo -e "  • Issue closing automation"
            echo -e "  • Sprint management (milestones)"
            echo -e "  • Sprint assignment and tracking"
        else
            echo -e "${YELLOW}⚠️  GitHub CLI Not Authenticated${NC}"
            echo -e "  Run: ${BLUE}gh auth login${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  GitHub CLI Not Installed${NC}"
        echo -e "  Install: ${BLUE}brew install gh${NC}"
        echo ""
        echo -e "${CYAN}Manual Integration Available:${NC}"
        echo -e "  • Issue linking in documents"
        echo -e "  • Project URL references"
        echo -e "  • Manual project card updates"
    fi
    
    echo ""
    echo -e "${CYAN}Current Project Columns:${NC}"
    echo -e "  📋 Planned      - Issues with planning documents"
    echo -e "  🔄 In progress  - Issues with active documents"
    echo -e "  🔍 Review       - Completed work pending review"
    echo -e "  ✅ Done         - Completed and documented features"
    echo ""
    echo -e "${CYAN}Integration Workflow:${NC}"
    echo -e "  1. Create GitHub issue"
    echo -e "  2. Add issue to project (📋 Planned)"
    echo -e "  3. Create planning document with issue link"
    echo -e "  4. Move to 🔄 In progress when activating"
    echo -e "  5. Move to 🔍 Review when ready for review"
    echo -e "  6. Move to ✅ Done when completing"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
}

# GitHub integration helper
github_integration_notice() {
    local action=$1
    local issue_number=$2
    
    echo ""
    echo -e "${CYAN}🔗 GitHub Projects Integration${NC}"
    case $action in
        "create")
            echo -e "  📋 Suggested Actions:"
            echo -e "     1. Ensure issue #$issue_number exists"
            echo -e "     2. Add issue to project: ${BLUE}$PROJECT_URL${NC}"
            echo -e "     3. Move card to '📋 Planned' column"
            ;;
        "activate")
            echo -e "  🔄 Suggested Actions:"
            echo -e "     1. Move project card to 'In progress'"
            echo -e "     2. Update issue #$issue_number with progress"
            echo -e "     3. Link any related PRs"
            ;;
        "complete")
            echo -e "  ✅ Suggested Actions:"
            echo -e "     1. Move project card to 'Review' for review"
            echo -e "     2. Move to 'Done' when approved"
            echo -e "     3. Close issue #$issue_number if fully complete"
            ;;
        "review")
            echo -e "  🔍 Suggested Actions:"
            echo -e "     1. Move project card to 'Review'"
            echo -e "     2. Request stakeholder review"
            echo -e "     3. Address any feedback"
            ;;
        "done")
            echo -e "  ✅ Suggested Actions:"
            echo -e "     1. Move project card to 'Done'"
            echo -e "     2. Close issue #$issue_number"
            echo -e "     3. Update project with final status"
            ;;
    esac
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${GREEN}💡 Tip: Use --update-project flag for automatic updates${NC}"
    else
        echo -e "${YELLOW}💡 Tip: Install and authenticate GitHub CLI for automation${NC}"
    fi
}

# Enhanced create function with GitHub integration
create_planning_doc() {
    local issue_number=$1
    local description=$2
    local link_issue=${3:-false}
    
    if [[ -z "$issue_number" || -z "$description" ]]; then
        echo -e "${RED}Error: Issue number and description required${NC}"
        echo "Usage: $0 create <issue-number> <description> [--link-issue]"
        exit 1
    fi
    
    # Sanitize description for filename
    local clean_description=$(echo "$description" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')
    local filename="ISSUE-${issue_number}-${clean_description}-PLAN.md"
    local filepath="$DOCS_DIR/planning/$filename"
    
    # Check if file already exists
    if [[ -f "$filepath" ]]; then
        echo -e "${YELLOW}Warning: Planning document already exists: $filename${NC}"
        exit 1
    fi
    
    # Create planning document from template
    if [[ -f "$DOCS_DIR/templates/PLANNING_TEMPLATE.md" ]]; then
        cp "$DOCS_DIR/templates/PLANNING_TEMPLATE.md" "$filepath"
        
        # Update template placeholders
        local current_date=$(date '+%Y-%m-%d')
        sed -i '' "s/\[Issue Title\]/$description/g" "$filepath"
        sed -i '' "s/\[ISSUE_NUMBER\]/$issue_number/g" "$filepath"
        sed -i '' "s/\[DATE\]/$current_date/g" "$filepath"
        
        # Add GitHub Projects integration
        if [[ "$link_issue" == "true" ]]; then
            sed -i '' "s|Location\*\*:|Project**: $PROJECT_URL\\
Location**:|g" "$filepath"
        fi
        
        echo -e "${GREEN}✅ Planning document created: $filename${NC}"
        echo -e "${BLUE}📁 Location: $filepath${NC}"
        
        # GitHub CLI automation
        if [[ "$link_issue" == "true" ]] && check_gh_cli && gh auth status &>/dev/null; then
            create_project_item "$issue_number"
            
            # Assign to sprint if specified
            if [[ -n "$SPRINT_NUMBER" ]]; then
                assign_issue_to_sprint "$issue_number" "$SPRINT_NUMBER"
            fi
        fi
        
        # Show GitHub integration suggestions
        github_integration_notice "create" "$issue_number"
        
    else
        echo -e "${RED}Error: Planning template not found${NC}"
        exit 1
    fi
}

# Enhanced activate function
activate_document() {
    local issue_number=$1
    local description=$2
    local update_project=${3:-false}
    
    if [[ -z "$issue_number" || -z "$description" ]]; then
        echo -e "${RED}Error: Issue number and description required${NC}"
        exit 1
    fi
    
    local clean_description=$(echo "$description" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')
    local planning_file="ISSUE-${issue_number}-${clean_description}-PLAN.md"
    local planning_path="$DOCS_DIR/planning/$planning_file"
    local active_file="ISSUE-${issue_number}-${clean_description}-ACTIVE.md"
    local active_path="$DOCS_DIR/current/$active_file"
    
    if [[ ! -f "$planning_path" ]]; then
        echo -e "${RED}Error: Planning document not found: $planning_file${NC}"
        exit 1
    fi
    
    # Copy to current and update from implementation template
    if [[ -f "$DOCS_DIR/templates/IMPLEMENTATION_TEMPLATE.md" ]]; then
        # Create implementation document with planning content as reference
        cp "$DOCS_DIR/templates/IMPLEMENTATION_TEMPLATE.md" "$active_path"
        
        # Update template placeholders
        local current_date=$(date '+%Y-%m-%d')
        sed -i '' "s/\[Issue Title\]/$description/g" "$active_path"
        sed -i '' "s/\[ISSUE_NUMBER\]/$issue_number/g" "$active_path"
        sed -i '' "s/\[DATE\]/$current_date/g" "$active_path"
        
        # Add reference to planning document
        echo "" >> "$active_path"
        echo "## 📋 Planning Reference" >> "$active_path"
        echo "" >> "$active_path"
        echo "Original planning document: \`planning/$planning_file\`" >> "$active_path"
        
        # Remove from planning
        rm "$planning_path"
        
        echo -e "${GREEN}✅ Document activated: $active_file${NC}"
        echo -e "${BLUE}📁 Location: $active_path${NC}"
        
        # GitHub CLI automation
        if [[ "$update_project" == "true" ]] && check_gh_cli && gh auth status &>/dev/null; then
            update_project_status "$issue_number" "In Progress"
        fi
        
        # Show GitHub integration suggestions
        github_integration_notice "activate" "$issue_number"
        
    else
        echo -e "${RED}Error: Implementation template not found${NC}"
        exit 1
    fi
}

# Mark document as ready for review
review_document() {
    local document_name=$1
    
    if [[ -z "$document_name" ]]; then
        echo -e "${RED}Error: Document name required${NC}"
        echo "Usage: $0 review <document-name>"
        exit 1
    fi
    
    local current_path="$DOCS_DIR/current/$document_name"
    
    if [[ ! -f "$current_path" ]]; then
        echo -e "${RED}Error: Active document not found: $document_name${NC}"
        exit 1
    fi
    
    # Extract issue number for GitHub integration
    local issue_number=$(echo "$document_name" | grep -o 'ISSUE-[0-9]*' | grep -o '[0-9]*')
    
    # Update status in document
    sed -i '' 's/Status\*\*: In Progress/Status**: Under Review/g' "$current_path"
    
    echo -e "${GREEN}✅ Document marked for review: $document_name${NC}"
    echo -e "${BLUE}📁 Location: $current_path${NC}"
    echo -e "${PURPLE}🔍 Status: Under Review${NC}"
    
    # GitHub CLI automation
    if [[ -n "$issue_number" ]]; then
        if check_gh_cli && gh auth status &>/dev/null; then
            update_project_status "$issue_number" "Review"
        fi
        
        # Show GitHub integration suggestions
        github_integration_notice "review" "$issue_number"
    fi
}

# Enhanced complete function
complete_document() {
    local document_name=$1
    local category=$2
    local close_issue=${3:-false}
    
    if [[ -z "$document_name" || -z "$category" ]]; then
        echo -e "${RED}Error: Document name and category required${NC}"
        exit 1
    fi
    
    local current_path="$DOCS_DIR/current/$document_name"
    
    if [[ ! -f "$current_path" ]]; then
        echo -e "${RED}Error: Active document not found: $document_name${NC}"
        exit 1
    fi
    
    # Valid categories
    local valid_categories=("architecture" "development" "deployment" "api" "troubleshooting" "research")
    if [[ ! " ${valid_categories[@]} " =~ " ${category} " ]]; then
        echo -e "${RED}Error: Invalid category. Valid categories: ${valid_categories[*]}${NC}"
        exit 1
    fi
    
    # Extract issue number for GitHub integration
    local issue_number=$(echo "$document_name" | grep -o 'ISSUE-[0-9]*' | grep -o '[0-9]*')
    
    # Create final document name
    local final_name=$(echo "$document_name" | sed 's/-ACTIVE\.md/-REFERENCE.md/')
    local final_path="$DOCS_DIR/$category/$final_name"
    
    # Ensure category directory exists
    mkdir -p "$DOCS_DIR/$category"
    
    # Move and update document
    mv "$current_path" "$final_path"
    
    # Update status in document
    sed -i '' 's/Status\*\*: In Progress/Status**: Complete/g' "$final_path"
    sed -i '' "s|current/|$category/|g" "$final_path"
    
    echo -e "${GREEN}✅ Document completed: $final_name${NC}"
    echo -e "${BLUE}📁 Location: $final_path${NC}"
    echo -e "${BLUE}📂 Category: $category${NC}"
    
    # GitHub CLI automation
    if [[ -n "$issue_number" ]]; then
        if [[ "$close_issue" == "true" ]] && check_gh_cli && gh auth status &>/dev/null; then
            close_github_issue "$issue_number"
            update_project_status "$issue_number" "Done"
        fi
        
        # Show GitHub integration suggestions
        github_integration_notice "complete" "$issue_number"
    fi
}

# Rest of the script (list, status functions remain the same)
list_documents() {
    local stage=$1
    
    if [[ -z "$stage" ]]; then
        echo -e "${RED}Error: Stage required${NC}"
        echo "Valid stages: planning, current, architecture, development, deployment, api, troubleshooting, research"
        exit 1
    fi
    
    echo -e "${BLUE}Documents in $stage:${NC}"
    
    if [[ -d "$DOCS_DIR/$stage" ]]; then
        local count=0
        for file in "$DOCS_DIR/$stage"/*.md; do
            if [[ -f "$file" ]]; then
                local basename=$(basename "$file")
                echo -e "  📄 $basename"
                ((count++))
            fi
        done
        
        if [[ $count -eq 0 ]]; then
            echo -e "${YELLOW}  No documents found${NC}"
        else
            echo -e "${GREEN}  Total: $count documents${NC}"
        fi
    else
        echo -e "${YELLOW}  Directory not found: $DOCS_DIR/$stage${NC}"
    fi
}

# Sprint-optimized milestone assignment (new workflow)
assign_sprint_optimized() {
    local issue_number=$1
    local sprint_milestone=$2
    local additional_labels=()
    
    # Parse additional labels (version, feature, generic)
    shift 2
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                additional_labels+=("version:$(echo "$2" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')")
                shift 2
                ;;
            --feature)
                additional_labels+=("feature:$(echo "$2" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')")
                shift 2
                ;;
            --generic)
                additional_labels+=("generic:$(echo "$2" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')")
                shift 2
                ;;
            *)
                echo -e "${YELLOW}⚠️  Unknown option: $1${NC}"
                shift
                ;;
        esac
    done
    
    if [[ -z "$issue_number" || -z "$sprint_milestone" ]]; then
        echo -e "${RED}Error: Issue number and sprint milestone required${NC}"
        echo "Usage: $0 assign-sprint <issue-number> <sprint-milestone> [--version <v>] [--feature <f>] [--generic <g>]"
        exit 1
    fi
    
    if check_gh_cli && gh auth status &>/dev/null; then
        echo -e "${CYAN}🏃 Sprint-Optimized Assignment for Issue #$issue_number${NC}"
        
        # Assign sprint as primary milestone
        if gh issue edit "$issue_number" --milestone "$sprint_milestone" 2>/dev/null; then
            echo -e "${GREEN}✅ Sprint milestone assigned: $sprint_milestone${NC}"
        else
            echo -e "${YELLOW}⚠️  Sprint milestone '$sprint_milestone' may not exist, creating it...${NC}"
            create_milestone_if_not_exists "$sprint_milestone"
            gh issue edit "$issue_number" --milestone "$sprint_milestone" 2>/dev/null || echo -e "${RED}❌ Failed to assign sprint milestone${NC}"
        fi
        
        # Add additional labels
        for label in "${additional_labels[@]}"; do
            if gh issue edit "$issue_number" --add-label "$label" 2>/dev/null; then
                echo -e "${GREEN}✅ Label added: $label${NC}"
            else
                echo -e "${YELLOW}⚠️  Failed to add label: $label${NC}"
            fi
        done
        
        echo ""
        echo -e "${PURPLE}📊 Summary for Issue #$issue_number:${NC}"
        echo -e "  🏃 Primary Sprint: $sprint_milestone"
        for label in "${additional_labels[@]}"; do
            echo -e "  🏷️  Label: $label"
        done
        
        echo ""
        echo -e "${CYAN}💡 Next Steps:${NC}"
        echo -e "  1. Copy document content to GitHub issue description"
        echo -e "  2. Move issue to appropriate project column"
        echo -e "  3. Update document sync status"
        
    else
        echo -e "${YELLOW}⚠️  GitHub CLI not available${NC}"
    fi
}

# Generate GitHub-ready issue content from document
generate_issue_content() {
    local document_path=$1
    
    if [[ -z "$document_path" || ! -f "$document_path" ]]; then
        echo -e "${RED}Error: Document file not found: $document_path${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}📋 Generating GitHub Issue Content${NC}"
    echo -e "${BLUE}Source: $document_path${NC}"
    echo ""
    
    # Extract content suitable for GitHub issue
    echo -e "${YELLOW}═══ COPY BELOW FOR GITHUB ISSUE ═══${NC}"
    echo ""
    
    # Skip the header and GitHub sync sections, extract main content
    awk '
    BEGIN { in_content = 0; skip_sync = 0 }
    /^## 📋 GitHub Issue Sync Status/ { skip_sync = 1; next }
    /^---$/ && skip_sync { skip_sync = 0; next }
    /^## 🔗 Project Integration/ { in_content = 1; next }
    in_content && !skip_sync { print }
    ' "$document_path"
    
    echo ""
    echo -e "${YELLOW}═══ END COPY SECTION ═══${NC}"
    
    echo ""
    echo -e "${CYAN}💡 Usage Tips:${NC}"
    echo -e "  1. Copy the content above"
    echo -e "  2. Paste into GitHub issue description"
    echo -e "  3. Update document sync status"
    echo -e "  4. Add milestone and labels as needed"
}

show_status() {
    echo -e "${BLUE}PPL Meta Platform - Document Lifecycle Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    
    local stages=("planning" "current" "architecture" "development" "deployment" "api" "troubleshooting" "research")
    local total=0
    
    for stage in "${stages[@]}"; do
        if [[ -d "$DOCS_DIR/$stage" ]]; then
            local count=$(find "$DOCS_DIR/$stage" -name "*.md" -type f | wc -l | tr -d ' ')
            total=$((total + count))
            
            case $stage in
                "planning")
                    echo -e "${YELLOW}📋 $stage: $count documents${NC}"
                    ;;
                "current")
                    echo -e "${CYAN}🔄 $stage: $count documents${NC}"
                    ;;
                *)
                    echo -e "${GREEN}📁 $stage: $count documents${NC}"
                    ;;
            esac
        fi
    done
    
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}📊 Total: $total documents${NC}"
}

# Parse command line arguments
LINK_ISSUE=false
UPDATE_PROJECT=false
CLOSE_ISSUE=false
UPDATE_VERSION_FILE=false
SPRINT_NUMBER=""
COMMAND=""
ARG1=""
ARG2=""
ARG3=""

# Parse all arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --link-issue)
            LINK_ISSUE=true
            shift
            ;;
        --update-project)
            UPDATE_PROJECT=true
            shift
            ;;
        --close-issue)
            CLOSE_ISSUE=true
            shift
            ;;
        --update-file)
            UPDATE_VERSION_FILE=true
            shift
            ;;
        --sprint)
            SPRINT_NUMBER="$2"
            shift 2
            ;;
        --version)
            VERSION_MILESTONE="$2"
            shift 2
            ;;
        --feature)
            FEATURE_MILESTONE="$2"
            shift 2
            ;;
        --generic)
            GENERIC_MILESTONE="$2"
            shift 2
            ;;
        *)
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            elif [[ -z "$ARG1" ]]; then
                ARG1="$1"
            elif [[ -z "$ARG2" ]]; then
                ARG2="$1"
            elif [[ -z "$ARG3" ]]; then
                ARG3="$1"
            fi
            shift
            ;;
    esac
done

# Main command handling
case "${COMMAND:-}" in
    "create")
        create_planning_doc "$ARG1" "$ARG2" "$LINK_ISSUE"
        ;;
    "activate")
        activate_document "$ARG1" "$ARG2" "$UPDATE_PROJECT"
        ;;
    "review")
        review_document "$ARG1"
        ;;
    "complete")
        complete_document "$ARG1" "$ARG2" "$CLOSE_ISSUE"
        ;;
    "bump-version")
        bump_version "$ARG1" "$UPDATE_VERSION_FILE"
        ;;
    "assign-milestones")
        # Handle milestone assignment with proper argument parsing
        if [[ -n "$ARG1" ]]; then
            issue_num="$ARG1"
            
            # Build the milestone assignment command
            version_arg=""
            sprint_arg="" 
            feature_arg=""
            generic_arg=""
            
            [[ -n "$VERSION_MILESTONE" ]] && version_arg="--version \"$VERSION_MILESTONE\""
            [[ -n "$SPRINT_NUMBER" ]] && sprint_arg="--sprint \"$SPRINT_NUMBER\""
            [[ -n "$FEATURE_MILESTONE" ]] && feature_arg="--feature \"$FEATURE_MILESTONE\""
            [[ -n "$GENERIC_MILESTONE" ]] && generic_arg="--generic \"$GENERIC_MILESTONE\""
            
            # Call the function with parsed arguments
            eval "assign_multiple_milestones '$issue_num' $version_arg $sprint_arg $feature_arg $generic_arg"
        else
            echo -e "${RED}Error: Issue number required${NC}"
            echo "Usage: $0 assign-milestones <issue-number> [--version <v>] [--sprint <s>] [--feature <f>] [--generic <g>]"
            exit 1
        fi
        ;;
    "assign-sprint")
        # Sprint-optimized assignment
        if [[ -n "$ARG1" && -n "$ARG2" ]]; then
            assign_sprint_optimized "$@"
        else
            echo -e "${RED}Error: Issue number and sprint milestone required${NC}"
            echo "Usage: $0 assign-sprint <issue-number> <sprint-milestone> [--version <v>] [--feature <f>] [--generic <g>]"
            exit 1
        fi
        ;;
    "generate-issue-content")
        if [[ -n "$ARG1" ]]; then
            generate_issue_content "$ARG1"
        else
            echo -e "${RED}Error: Document path required${NC}"
            echo "Usage: $0 generate-issue-content <document-path>"
            exit 1
        fi
        ;;
    "list-milestone-types")
        list_milestone_types
        ;;
    "milestone-report")
        milestone_report
        ;;
    "create-sprint")
        create_sprint_milestone "$ARG1" "$ARG2" "$ARG3"
        ;;
    "create-version-milestone")
        create_version_milestone "$ARG1" "$ARG2" "$ARG3"
        ;;
    "create-release")
        if [[ "$ARG2" == "--auto-notes" ]]; then
            create_release_auto "$ARG1"
        else
            create_release_from_milestone "$ARG1" "$ARG2"
        fi
        ;;
    "next-version")
        suggest_next_version
        ;;
    "version-status")
        show_version_status
        ;;
    "sprint-status")
        show_sprint_status
        ;;
    "sprint-progress")
        show_sprint_progress "$ARG1"
        ;;
    "list")
        list_documents "$ARG1"
        ;;
    "status")
        show_status
        ;;
    "project-sync")
        show_project_integration
        ;;
    *)
        usage
        exit 1
        ;;
esac
