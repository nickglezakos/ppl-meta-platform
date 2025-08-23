# [Feature Name] - Implementation Document

**Status**: Active Implementation  
**Issue**: #[ISSUE_NUMBER]  
**Created**: [DATE]  
**Last Updated**: [DATE]  
**Location**: planning/ → current/ → [final_category]/  
**Implementation Progress**: [X]% Complete

---

## 📋 Implementation Overview

### Issue Reference

- **GitHub Issue**: #[ISSUE_NUMBER]
- **Planning Document**: `docs/planning/ISSUE-[NUMBER]-[name]-PLAN.md`
- **Implementation Start**: [DATE]
- **Target Completion**: [DATE]

### Current Status

- [ ] Research Complete
- [ ] Design Approved
- [ ] Implementation Started
- [ ] Testing In Progress
- [ ] Documentation Updated
- [ ] Ready for Review

## 🎯 Implementation Details

### Technical Approach

[Describe the specific technical implementation approach]

### Code Changes

#### Services Modified

- **Service Name**: [Description of changes]
  - Files modified: `path/to/file1.py`, `path/to/file2.py`
  - New functionality: [Description]
  - Breaking changes: [Yes/No - Description]

#### New Components

- **Component Name**: [Description]
  - Location: `path/to/component/`
  - Purpose: [Description]
  - Dependencies: [List]

### Database Changes

#### Schema Updates

```sql
-- Add any SQL schema changes here
ALTER TABLE table_name ADD COLUMN new_column VARCHAR(255);
```

#### Migration Scripts

- `migration_001_add_feature.sql` - [Description]
- `migration_002_update_indexes.sql` - [Description]

### Configuration Changes

#### Environment Variables

```bash
NEW_FEATURE_ENABLED=true
NEW_FEATURE_API_KEY=your_api_key_here
```

#### Service Configuration

- **Service Name**: Updated `config.yaml` to include [changes]
- **Docker**: Updated `docker-compose.yml` for [changes]

## 🧪 Testing Progress

### Test Implementation Status

- [ ] Unit Tests Written
- [ ] Integration Tests Written
- [ ] End-to-End Tests Written
- [ ] Performance Tests Written

### Test Results

#### Unit Tests

```bash
# Test command
pytest tests/unit/test_new_feature.py

# Results
Tests run: 15, Passed: 15, Failed: 0, Coverage: 95%
```

#### Integration Tests

```bash
# Test command
pytest tests/integration/test_feature_integration.py

# Results
Tests run: 8, Passed: 8, Failed: 0
```

### Test Coverage

- **Current Coverage**: [X]%
- **Target Coverage**: 80%+
- **Coverage Report**: [Link to coverage report]

## 🔧 Implementation Challenges

### Issues Encountered

1. **Challenge 1**: [Description]

   - **Solution**: [How it was resolved]
   - **Impact**: [Timeline/scope impact]

2. **Challenge 2**: [Description]
   - **Solution**: [How it was resolved]
   - **Impact**: [Timeline/scope impact]

### Outstanding Issues

- [ ] **Issue 1**: [Description] - [Assigned to] - [Due date]
- [ ] **Issue 2**: [Description] - [Assigned to] - [Due date]

## 📊 Performance Impact

### Metrics Measured

- **Response Time**: [Before] → [After]
- **Memory Usage**: [Before] → [After]
- **CPU Usage**: [Before] → [After]
- **Database Queries**: [Before] → [After]

### Performance Tests

```bash
# Load testing command
artillery run load-test.yml

# Results
Average response time: 150ms
95th percentile: 300ms
Error rate: 0.1%
```

## 🚀 Deployment Preparation

### Deployment Checklist

- [ ] Code review completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Configuration files updated
- [ ] Migration scripts tested
- [ ] Rollback plan prepared

### Deployment Steps

1. **Pre-deployment**:

   - [ ] Backup current state
   - [ ] Verify staging environment
   - [ ] Run migration scripts

2. **Deployment**:

   - [ ] Deploy new code
   - [ ] Apply configuration changes
   - [ ] Restart affected services

3. **Post-deployment**:
   - [ ] Verify all services healthy
   - [ ] Run smoke tests
   - [ ] Monitor error logs

### Rollback Plan

1. **If deployment fails**:

   - Revert to previous Docker images
   - Restore database from backup
   - Reset configuration files

2. **Rollback commands**:

```bash
# Commands to rollback if needed
docker-compose down
docker-compose up -d --scale service_name=previous_version
```

## 📚 Documentation Updates

### Documentation Modified

- [ ] API Documentation
- [ ] User Guide
- [ ] Architecture Documentation
- [ ] Deployment Guide
- [ ] Troubleshooting Guide

### New Documentation Created

- [ ] Feature Usage Guide
- [ ] Integration Examples
- [ ] Troubleshooting Section
- [ ] Performance Tuning Guide

## 🔍 Code Review

### Review Status

- [ ] **Self Review**: Complete
- [ ] **Peer Review**: [Reviewer Name] - [Status]
- [ ] **Architecture Review**: [Reviewer Name] - [Status]
- [ ] **Security Review**: [Reviewer Name] - [Status]

### Review Comments

- **Comment 1**: [Description] - [Status: Addressed/Pending]
- **Comment 2**: [Description] - [Status: Addressed/Pending]

## 📈 Success Metrics

### Acceptance Criteria

- [ ] Criteria 1: [Description] - [Status]
- [ ] Criteria 2: [Description] - [Status]
- [ ] Criteria 3: [Description] - [Status]

### Performance Targets

- [ ] Response time < 200ms
- [ ] Error rate < 0.1%
- [ ] Memory usage < 1GB
- [ ] CPU usage < 50%

## 🔗 Related Work

### Pull Requests

- [PR #123: Feature Implementation](link-to-pr)
- [PR #124: Documentation Updates](link-to-pr)

### Related Issues

- [Issue #456: Related feature](link-to-issue)
- [Issue #789: Dependency update](link-to-issue)

## 📝 Implementation Notes

### Key Decisions

1. **Decision 1**: [Description and rationale]
2. **Decision 2**: [Description and rationale]

### Lessons Learned

1. **Lesson 1**: [Description]
2. **Lesson 2**: [Description]

### Future Improvements

- [ ] Improvement 1: [Description]
- [ ] Improvement 2: [Description]

---

**Next Steps**:

1. Complete remaining implementation tasks
2. Finalize testing and documentation
3. Move to appropriate docs/ category when complete
4. Create reference documentation from REFERENCE_TEMPLATE.md

**Document Lifecycle**: This document will move to the appropriate category in `docs/` when implementation is complete and become the reference documentation.
