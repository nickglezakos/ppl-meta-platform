# 🌐 Project Management Web-First Workflow

## 🎯 **Overview**

This workflow leverages GitHub's native web interface for project management while using minimal console commands for document lifecycle management. Perfect for teams who want visual project management with structured documentation.

## 🔑 **Core Principle**

**Separation of Concerns:**
- 🌐 **GitHub Web Interface**: Project management, milestones, labels, team collaboration
- 💻 **Console Commands**: Document creation and content synchronization only

## 📋 **The Two Essential Commands**

### **Command 1: Document Creation**
```bash
./scripts/docs-lifecycle-enhanced.sh create [ISSUE_NUMBER] "[brief-name]" --link-issue
```

**Purpose**: Create a planning document linked to an existing GitHub issue

**Example**:
```bash
./scripts/docs-lifecycle-enhanced.sh create 123 "api-enhancement" --link-issue
```

**What it creates**:
- `docs/planning/ISSUE-123-api-enhancement-PLAN.md`
- Pre-filled with issue number and GitHub links
- Ready for planning content

### **Command 2: Content Generation**
```bash
./scripts/docs-lifecycle-enhanced.sh generate-issue-content [DOCUMENT_PATH]
```

**Purpose**: Extract document content formatted for GitHub issue description

**Example**:
```bash
./scripts/docs-lifecycle-enhanced.sh generate-issue-content docs/planning/ISSUE-123-api-enhancement-PLAN.md
```

**What it provides**:
- Clean, GitHub-ready content
- Removes internal document metadata
- Copy-paste ready format

## 🌐 **GitHub Web Interface Workflow**

### **1. Issue Creation & Management**

**Create New Issue:**
1. Go to GitHub Issues tab
2. Click "New issue"
3. Set title and description
4. Add initial labels as needed

**Milestone Assignment:**
1. Use sprint milestones as primary milestones
2. Example: `Sprint 6`, `Sprint 7`, etc.
3. Leverage GitHub's visual progress tracking

**Label Management:**
1. Create version labels: `version:v2.14.0`
2. Create feature labels: `feature:api-enhancement`
3. Create generic labels: `generic:q4-goals`
4. Apply multiple labels to single issue

### **2. Project Board Management**

**GitHub Projects Setup:**
- **📋 Planned**: Issues with planning documents
- **🔄 In Progress**: Active development work
- **🔍 Review**: Completed work pending review
- **✅ Done**: Completed and documented features

**Daily Management:**
1. **Drag & Drop**: Move issues between columns
2. **Visual Progress**: Monitor sprint milestone progress bars
3. **Filtering**: Use milestone and label filters
4. **Team Updates**: Comments and status updates

### **3. Sprint Management**

**Sprint Planning:**
1. Create sprint milestone in GitHub
2. Set due date for sprint end
3. Assign issues to sprint milestone
4. Use project board for sprint backlog

**Sprint Execution:**
1. Move issues through project columns
2. Update issue status and comments
3. Track progress via milestone progress bar
4. Review sprint burndown visually

## 💻 **Console Document Workflow**

### **Phase 1: Planning**
```bash
# 1. Create document for existing GitHub issue
./scripts/docs-lifecycle-enhanced.sh create 123 "mobile-integration" --link-issue

# 2. Edit the planning document
# Fill out problem statement, objectives, solution approach

# 3. Generate content for GitHub issue
./scripts/docs-lifecycle-enhanced.sh generate-issue-content docs/planning/ISSUE-123-mobile-integration-PLAN.md

# 4. Copy-paste content to GitHub issue description
```

### **Phase 2: Development**
```bash
# Move document to active development
./scripts/docs-lifecycle-enhanced.sh activate 123 "mobile-integration"

# Update document as development progresses
# Sync major updates back to GitHub issue
./scripts/docs-lifecycle-enhanced.sh generate-issue-content docs/current/ISSUE-123-mobile-integration-ACTIVE.md
```

### **Phase 3: Completion**
```bash
# Complete document and move to reference
./scripts/docs-lifecycle-enhanced.sh complete ISSUE-123-mobile-integration-ACTIVE.md development

# Close issue in GitHub web interface
# Update project board status
```

## 🔄 **Document-Issue Synchronization**

### **When to Sync Document → Issue**

**Major Updates:**
- ✅ Significant changes to approach or solution
- ✅ New technical decisions or architecture changes
- ✅ Updated timelines or scope modifications

**Minor Updates:**
- ⭕ Daily progress updates (use GitHub comments instead)
- ⭕ Small status changes (use project board instead)
- ⭕ Quick notes or observations

### **Sync Process**
1. **Generate Content**: Run `generate-issue-content` command
2. **Copy Content**: Copy the formatted output
3. **Update Issue**: Paste into GitHub issue description
4. **Update Document**: Note sync date in document header
5. **Notify Team**: Add comment about major updates

## 📊 **Filtering & Reporting**

### **GitHub Native Filtering**

**By Sprint:**
```
milestone:"Sprint 6"
```

**By Version:**
```
label:version:v2.14.0
```

**By Feature:**
```
label:feature:mobile-integration
```

**Combined Filtering:**
```
milestone:"Sprint 6" label:version:v2.14.0 is:open
```

### **Progress Tracking**

**Sprint Progress:**
- Use GitHub milestone progress bars
- Visual completion percentage
- Remaining issues count

**Feature Progress:**
- Filter by feature labels
- Track across multiple sprints
- Cross-reference with version labels

## 👥 **Team Collaboration**

### **For Team Members**

**GitHub Web Interface:**
- ✅ Create and manage issues
- ✅ Update project board status
- ✅ Add comments and feedback
- ✅ Review and assign issues
- ✅ Track sprint progress

**No Console Required:**
- ❌ No need to learn command-line tools
- ❌ No need for local repository access
- ❌ No scripting knowledge needed

### **For Project Lead**

**Console Commands:**
- ✅ Create structured documentation
- ✅ Maintain document lifecycle
- ✅ Sync detailed content to issues

**GitHub Web Interface:**
- ✅ Overall project management
- ✅ Sprint planning and tracking
- ✅ Team coordination

## 🔧 **Setup Requirements**

### **GitHub Repository Setup**
1. **Enable Issues**: Repository settings → Features → Issues
2. **Create Project**: Repository → Projects → New project
3. **Setup Columns**: Planned, In Progress, Review, Done
4. **Create Labels**: version, feature, generic patterns (simplified format)

### **Local Console Setup**
1. **Clone Repository**: For document management
2. **Script Access**: Ensure scripts are executable
3. **GitHub CLI** (Optional): For enhanced integration if needed

### **Team Member Setup**
1. **GitHub Account**: Access to repository
2. **Project Access**: Added to GitHub project
3. **Notification Settings**: Configure for updates

## 📱 **Mobile & Remote Work**

### **GitHub Mobile App**
- ✅ **Issue Management**: Create, update, close issues
- ✅ **Project Boards**: Move cards, update status
- ✅ **Comments**: Add updates and feedback
- ✅ **Notifications**: Stay updated on progress

### **Web Browser**
- ✅ **Full Functionality**: Complete project management
- ✅ **Keyboard Shortcuts**: Efficient navigation
- ✅ **Bookmarks**: Save filtered views

## 💡 **Best Practices**

### **Issue Management**
1. **Clear Titles**: Descriptive and actionable
2. **Consistent Labels**: Follow naming conventions
3. **Regular Updates**: Keep status current
4. **Link Related Issues**: Use GitHub's linking features

### **Document Sync**
1. **Sync Early**: Don't wait until completion
2. **Major Changes Only**: Avoid sync fatigue
3. **Clear Sync Notes**: Document what changed
4. **Regular Cadence**: Establish sync rhythm

### **Sprint Management**
1. **Realistic Scope**: Don't overcommit sprints
2. **Visual Tracking**: Use progress bars effectively
3. **Regular Reviews**: Sprint retrospectives
4. **Continuous Improvement**: Adapt workflow as needed

## 🚀 **Quick Reference**

### **Essential Commands**
```bash
# Create document for issue
./scripts/docs-lifecycle-enhanced.sh create [ISSUE] "[name]" --link-issue

# Generate GitHub-ready content
./scripts/docs-lifecycle-enhanced.sh generate-issue-content [DOCUMENT_PATH]
```

### **GitHub Web Actions**
- **Issues**: Create, label, milestone, comment, close
- **Projects**: Move cards, filter, track progress
- **Milestones**: Create sprints, set dates, monitor progress
- **Labels**: Create simplified patterns (version:, feature:, generic:), apply to issues

### **Workflow Steps**
1. **GitHub**: Create issue, set milestone, add labels
2. **Console**: Create document, fill content
3. **Console**: Generate issue content
4. **GitHub**: Paste content, update project board
5. **Repeat**: Sync when major changes occur

---

**This workflow gives you the best of both worlds**: professional project management through GitHub's interface + structured documentation through console commands! 🎯
