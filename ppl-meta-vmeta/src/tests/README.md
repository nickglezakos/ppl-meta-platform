# MVR-People Phase 3 Test Suite

Comprehensive test suite for all Phase 3 components of the MVR-People feature.

## Test Coverage

### 1. test_mvr_repository.py
Tests for the database access layer (`MVRRepository`):

- ✅ Create MVR-People records
- ✅ Retrieve MVR-People by UUID
- ✅ Find similar MVR-People (pgvector similarity search)
- ✅ Link Individual to MVR-People
- ✅ Merge MVR-People records
- ✅ Search by demographics (age, gender)
- ✅ Get/update matching configuration
- ✅ Get orphaned MVR-People

**Total Tests:** 10

### 2. test_mvr_service.py
Tests for the service layer (`MVRService`):

- ✅ Get MVR-People via service
- ✅ Search similar MVR-People
- ✅ Search by demographics
- ✅ Get matching configuration
- ✅ Update matching configuration
- ✅ Create MVR from Individual (mocked)

**Total Tests:** 6

### 3. test_mvr_matcher.py
Tests for matching and merging (`MVRMatcher`):

- ✅ Find matching MVR - no match scenario
- ✅ Find matching MVR - with match scenario
- ✅ Determine merge winner (quality-based)
- ✅ Complete merge workflow - success
- ✅ Complete merge workflow - no match

**Total Tests:** 5

### 4. test_mvr_background_processor.py
Tests for background processing (`MVRBackgroundProcessor`, `MVRIntegrationHook`):

- ✅ Process new Individual (mocked)
- ✅ Get statistics
- ✅ Get all pending tasks
- ✅ Cleanup old tasks
- ✅ Integration hook enable/disable
- ✅ On Individual created hook (mocked)
- ✅ Hook disabled behavior

**Total Tests:** 7

## Running Tests

### Run All Tests
```bash
cd ppl-meta-vmeta/src
source ../venv/bin/activate
python tests/run_all_phase3_tests.py
```

### Run Quick Smoke Test
```bash
python tests/run_all_phase3_tests.py --smoke
```

### Run Individual Test Suites
```bash
# Repository tests
python tests/test_mvr_repository.py

# Service tests
python tests/test_mvr_service.py

# Matcher tests
python tests/test_mvr_matcher.py

# Background processor tests
python tests/test_mvr_background_processor.py
```

### Run with pytest (if installed)
```bash
pytest tests/ -v
```

## Prerequisites

### Database Setup
Tests require a PostgreSQL database with:
- pgvector extension installed
- MVR-People schema migrated (run `002_mvr_people_schema.sql`)
- Environment variables set:
  ```bash
  export DB_HOST=localhost
  export DB_PORT=5432
  export DB_USER=ppl_user
  export DB_PASSWORD=ppl_password
  export DB_NAME=ppl_meta
  ```

### Python Dependencies
```bash
pip install asyncpg numpy pytest pytest-asyncio
```

### ML Models
DeepFace models will be downloaded automatically on first run:
- FaceNet512 (~95MB)
- Age estimation model
- Gender classification model

## Test Structure

Each test suite follows this pattern:

```python
class TestComponentName:
    """Test suite for ComponentName."""
    
    @pytest.fixture
    async def db_pool(self):
        """Create database connection pool."""
        # Setup code
        yield pool
        # Teardown code
    
    @pytest.fixture
    async def component(self, db_pool):
        """Create component instance."""
        return Component(...)
    
    async def test_feature_name(self, component):
        """Test specific feature."""
        # Arrange
        # Act
        # Assert
        logger.info("✅ Test passed")
```

## Expected Output

### Successful Run
```
======================================================================
MVR-PEOPLE PHASE 3 - COMPREHENSIVE TEST SUITE
======================================================================
Testing all Phase 3 components:
  - Phase 3.1: MVRRepository (Database Layer)
  - Phase 3.2: MVRService (Service Layer)
  - Phase 3.3-3.4: MVRMatcher (Matching & Merging)
  - Phase 3.5: MVRBackgroundProcessor (Background Tasks)
======================================================================

🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
TEST SUITE 1: MVRRepository
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵

... tests running ...

✅ MVRRepository tests: PASSED

... (more test suites) ...

======================================================================
FINAL TEST RESULTS
======================================================================

Total Test Suites: 4
✅ Passed: 4
❌ Failed: 0

✅ PASSED SUITES:
   - MVRRepository
   - MVRService
   - MVRMatcher
   - MVRBackgroundProcessor

======================================================================
🎉 ALL TESTS PASSED! Phase 3 is ready for Phase 4!
======================================================================
```

## Troubleshooting

### Database Connection Errors
```
Error: could not connect to server
```
**Solution:** Ensure PostgreSQL is running and environment variables are set correctly.

### pgvector Extension Missing
```
Error: extension "vector" is not available
```
**Solution:** Install pgvector extension:
```bash
# macOS with Homebrew
brew install pgvector

# Then in PostgreSQL:
CREATE EXTENSION vector;
```

### Migration Not Run
```
Error: relation "mvr_people" does not exist
```
**Solution:** Run migration:
```bash
python run_mvr_migration.py --apply
```

### DeepFace Model Download Fails
```
Error: Failed to download FaceNet model
```
**Solution:** Ensure internet connection and try again. Models are cached after first download.

## Test Data

Tests use randomly generated data:
- Face embeddings: 512D normalized numpy arrays
- UUIDs: Generated with `uuid4()`
- Quality scores: Random floats 0.7-1.0
- Demographics: Random age ranges and genders

No real person data is used in tests.

## Coverage Report

Generate coverage report (requires `pytest-cov`):
```bash
pytest tests/ --cov=database --cov=services --cov=background --cov-report=html
```

View report:
```bash
open htmlcov/index.html
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:
```yaml
# .github/workflows/test.yml
- name: Run Phase 3 Tests
  run: |
    source venv/bin/activate
    python tests/run_all_phase3_tests.py
```

## Performance Notes

- **Repository tests:** ~10-15 seconds (database I/O)
- **Service tests:** ~8-12 seconds (includes ML processing)
- **Matcher tests:** ~15-20 seconds (multiple embeddings + searches)
- **Background processor tests:** ~10-15 seconds (async task processing)

**Total suite runtime:** ~60-90 seconds

## Next Steps

After all Phase 3 tests pass:
1. ✅ Phase 3 complete
2. ➡️ Proceed to Phase 4: API Implementation
3. Create REST API endpoints for MVR-People
4. Add API tests to this suite

---

**Last Updated:** October 31, 2025  
**Test Suite Version:** 1.0.0  
**Total Tests:** 28 tests across 4 suites
