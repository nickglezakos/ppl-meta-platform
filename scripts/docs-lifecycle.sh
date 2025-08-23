#!/bin/bash

# PPL Meta Platform - Document Lifecycle Management Script
# This script helps move documents through the lifecycle: planning → current → final

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base directory
DOCS_DIR="docs"

# Usage function
usage() {
    echo -e "${BLUE}PPL Meta Platform - Document Lifecycle Management${NC}"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  activate <issue-number> <description>  - Move document from planning to current"
    echo "  complete <document-name> <category>    - Move document from current to final category"
    echo "  create <issue-number> <description>    - Create new planning document from template"
    echo "  list <stage>                           - List documents in specific stage"
    echo "  status                                 - Show status of all documents"
    echo ""
    echo "Stages: planning, current, architecture, development, deployment, api, troubleshooting, research"
    echo ""
    echo "Examples:"
    echo "  $0 create 123 \"network-discovery-enhancement\""
    echo "  $0 activate 123 \"network-discovery-enhancement\""
    echo "  $0 complete ISSUE-123-network-discovery-ACTIVE.md architecture"
    echo "  $0 list current"
    echo "  $0 status"
}

# Create new planning document
create_planning_doc() {
    local issue_number=$1
    local description=$2
    
    if [[ -z "$issue_number" || -z "$description" ]]; then
        echo -e "${RED}Error: Issue number and description required${NC}"
        echo "Usage: $0 create <issue-number> <description>"
        exit 1
    fi
    
    local filename="ISSUE-${issue_number}-${description}-PLAN.md"
    local planning_path="${DOCS_DIR}/planning/${filename}"
    local template_path="${DOCS_DIR}/templates/PLANNING_TEMPLATE.md"
    
    if [[ ! -f "$template_path" ]]; then
        echo -e "${RED}Error: Planning template not found at $template_path${NC}"
        exit 1
    fi
    
    if [[ -f "$planning_path" ]]; then
        echo -e "${YELLOW}Warning: Document already exists at $planning_path${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 1
        fi
    fi
    
    # Copy template and customize
    cp "$template_path" "$planning_path"
    
    # Replace placeholders
    local current_date=$(date +"%Y-%m-%d")
    sed -i.bak "s/\[Issue Title\]/Issue #${issue_number}: ${description}/g" "$planning_path"
    sed -i.bak "s/\[ISSUE_NUMBER\]/${issue_number}/g" "$planning_path"
    sed -i.bak "s/\[DATE\]/${current_date}/g" "$planning_path"
    rm "${planning_path}.bak"
    
    echo -e "${GREEN}✅ Created planning document: $planning_path${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Edit the document with your specific requirements"
    echo "2. When ready to start implementation, run: $0 activate $issue_number \"$description\""
}

# Move document from planning to current
activate_document() {
    local issue_number=$1
    local description=$2
    
    if [[ -z "$issue_number" || -z "$description" ]]; then
        echo -e "${RED}Error: Issue number and description required${NC}"
        echo "Usage: $0 activate <issue-number> <description>"
        exit 1
    fi
    
    local plan_filename="ISSUE-${issue_number}-${description}-PLAN.md"
    local active_filename="ISSUE-${issue_number}-${description}-ACTIVE.md"
    local plan_path="${DOCS_DIR}/planning/${plan_filename}"
    local active_path="${DOCS_DIR}/current/${active_filename}"
    local template_path="${DOCS_DIR}/templates/IMPLEMENTATION_TEMPLATE.md"
    
    if [[ ! -f "$plan_path" ]]; then
        echo -e "${RED}Error: Planning document not found at $plan_path${NC}"
        echo "Available planning documents:"
        ls -1 "${DOCS_DIR}/planning/" | grep "\.md$" || echo "None"
        exit 1
    fi
    
    if [[ -f "$active_path" ]]; then
        echo -e "${YELLOW}Warning: Active document already exists at $active_path${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 1
        fi
    fi
    
    # Create implementation document from template
    cp "$template_path" "$active_path"
    
    # Replace placeholders
    local current_date=$(date +"%Y-%m-%d")
    local feature_name=$(echo "$description" | sed 's/-/ /g' | sed 's/\b\w/\U&/g')
    
    sed -i.bak "s/\[Feature Name\]/${feature_name}/g" "$active_path"
    sed -i.bak "s/\[ISSUE_NUMBER\]/${issue_number}/g" "$active_path"
    sed -i.bak "s/\[DATE\]/${current_date}/g" "$active_path"
    sed -i.bak "s/\[X\]/0/g" "$active_path"
    rm "${active_path}.bak"
    
    # Move planning document to archive or keep as reference
    local archive_path="${DOCS_DIR}/planning/archive/"
    mkdir -p "$archive_path"
    mv "$plan_path" "${archive_path}${plan_filename}"
    
    echo -e "${GREEN}✅ Activated document: $active_path${NC}"
    echo -e "${GREEN}📋 Archived planning document: ${archive_path}${plan_filename}${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Update the implementation document with progress"
    echo "2. When complete, run: $0 complete $active_filename <category>"
}

# Move document from current to final category
complete_document() {
    local document_name=$1
    local category=$2
    
    if [[ -z "$document_name" || -z "$category" ]]; then
        echo -e "${RED}Error: Document name and category required${NC}"
        echo "Usage: $0 complete <document-name> <category>"
        echo "Categories: architecture, development, deployment, api, troubleshooting, research"
        exit 1
    fi
    
    local active_path="${DOCS_DIR}/current/${document_name}"
    local category_dir="${DOCS_DIR}/${category}"
    
    # Validate category
    local valid_categories=("architecture" "development" "deployment" "api" "troubleshooting" "research")
    if [[ ! " ${valid_categories[@]} " =~ " ${category} " ]]; then
        echo -e "${RED}Error: Invalid category '$category'${NC}"
        echo "Valid categories: ${valid_categories[*]}"
        exit 1
    fi
    
    if [[ ! -f "$active_path" ]]; then
        echo -e "${RED}Error: Active document not found at $active_path${NC}"
        echo "Available active documents:"
        ls -1 "${DOCS_DIR}/current/" | grep "\.md$" || echo "None"
        exit 1
    fi
    
    if [[ ! -d "$category_dir" ]]; then
        echo -e "${RED}Error: Category directory not found at $category_dir${NC}"
        exit 1
    fi
    
    # Generate reference document name
    local ref_name=$(echo "$document_name" | sed 's/ISSUE-[0-9]*-//' | sed 's/-ACTIVE\.md/-REFERENCE.md/')
    local ref_path="${category_dir}/${ref_name}"
    
    if [[ -f "$ref_path" ]]; then
        echo -e "${YELLOW}Warning: Reference document already exists at $ref_path${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 1
        fi
    fi
    
    # Move and rename document
    mv "$active_path" "$ref_path"
    
    # Update document status
    sed -i.bak 's/Status.*: Active Implementation/Status**: Complete/' "$ref_path"
    sed -i.bak "s/Category.*: \[.*\]/Category**: ${category}/" "$ref_path"
    rm "${ref_path}.bak"
    
    echo -e "${GREEN}✅ Completed document: $ref_path${NC}"
    echo -e "${BLUE}Document moved from current to ${category} category${NC}"
}

# List documents in specific stage
list_documents() {
    local stage=$1
    
    if [[ -z "$stage" ]]; then
        echo -e "${RED}Error: Stage required${NC}"
        echo "Usage: $0 list <stage>"
        echo "Stages: planning, current, architecture, development, deployment, api, troubleshooting, research"
        exit 1
    fi
    
    local stage_dir="${DOCS_DIR}/${stage}"
    
    if [[ ! -d "$stage_dir" ]]; then
        echo -e "${RED}Error: Stage directory not found at $stage_dir${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Documents in ${stage} stage:${NC}"
    echo "=================================="
    
    local count=0
    for file in "${stage_dir}"/*.md; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file")
            local modified=$(stat -f "%Sm" -t "%Y-%m-%d" "$file" 2>/dev/null || echo "Unknown")
            echo -e "${GREEN}📄 $basename${NC} (modified: $modified)"
            ((count++))
        fi
    done
    
    if [[ $count -eq 0 ]]; then
        echo -e "${YELLOW}No documents found in $stage stage${NC}"
    else
        echo ""
        echo -e "${BLUE}Total: $count documents${NC}"
    fi
}

# Show status of all documents
show_status() {
    echo -e "${BLUE}PPL Meta Platform - Document Status Overview${NC}"
    echo "=============================================="
    echo ""
    
    local stages=("planning" "current" "architecture" "development" "deployment" "api" "troubleshooting" "research")
    
    for stage in "${stages[@]}"; do
        local stage_dir="${DOCS_DIR}/${stage}"
        if [[ -d "$stage_dir" ]]; then
            local count=$(find "$stage_dir" -name "*.md" -type f | wc -l | tr -d ' ')
            if [[ $count -gt 0 ]]; then
                echo -e "${GREEN}📁 ${stage}: $count documents${NC}"
                find "$stage_dir" -name "*.md" -type f -exec basename {} \; | sed 's/^/  - /'
                echo ""
            else
                echo -e "${YELLOW}📁 ${stage}: 0 documents${NC}"
                echo ""
            fi
        fi
    done
}

# Main script logic
main() {
    local command=$1
    
    if [[ -z "$command" ]]; then
        usage
        exit 1
    fi
    
    # Change to repository root if we're not already there
    if [[ ! -d "$DOCS_DIR" ]]; then
        echo -e "${RED}Error: Must be run from repository root (docs/ directory not found)${NC}"
        exit 1
    fi
    
    case "$command" in
        "create")
            create_planning_doc "$2" "$3"
            ;;
        "activate")
            activate_document "$2" "$3"
            ;;
        "complete")
            complete_document "$2" "$3"
            ;;
        "list")
            list_documents "$2"
            ;;
        "status")
            show_status
            ;;
        "help"|"--help"|"-h")
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$command'${NC}"
            echo ""
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
