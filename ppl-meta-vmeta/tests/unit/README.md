# Event Subscription Unit Tests

This directory contains comprehensive unit tests for the event subscription system.

## Test Suites

### 1. `test_event_router.py`
Tests for the EventRouter component:
- ✅ Basic initialization and lifecycle
- ✅ Event routing and processing
- ✅ Event filtering (by type and collection)
- ✅ Retry logic with exponential backoff
- ✅ Dead letter queue functionality
- ✅ Backpressure handling
- ✅ Statistics tracking
- ✅ Health checks
- ✅ Graceful shutdown

**Coverage**: ~200 tests across 10 test classes

### 2. `test_websocket_subscriber.py`
Tests for the WebSocketEventSubscriber:
- ✅ Initialization and configuration
- ✅ WebSocket connection/disconnection
- ✅ Message handling (TEXT, CLOSED, ERROR, PING, PONG)
- ✅ Event filtering by type
- ✅ Heartbeat monitoring
- ✅ Reconnection with exponential backoff
- ✅ Health checks
- ✅ Lifecycle management

**Coverage**: ~170 tests across 8 test classes

### 3. `test_polling_subscriber.py`
Tests for the PollingEventSubscriber:
- ✅ Initialization and configuration
- ✅ HTTP connection management
- ✅ Polling for completed sessions
- ✅ Session processing
- ✅ Session-to-event conversion
- ✅ Deduplication logic
- ✅ Collection filtering
- ✅ Health checks
- ✅ Lifecycle management
- ✅ Error handling

**Coverage**: ~160 tests across 9 test classes

### 4. `test_subscription_manager.py`
Tests for the SubscriptionManager:
- ✅ Initialization and setup
- ✅ Lifecycle management (start/stop)
- ✅ WebSocket-only mode
- ✅ Polling-only mode
- ✅ Dual mode (both subscribers)
- ✅ Automatic failover
- ✅ Health monitoring
- ✅ Status reporting
- ✅ Manual subscriber restart
- ✅ Statistics tracking

**Coverage**: ~140 tests across 9 test classes

## Running Tests

### Run All Tests
```bash
cd ppl-meta-vmeta
source venv/bin/activate
./scripts/run_event_subscription_tests.sh
```

### Run Individual Test Suite
```bash
# Event Router tests
pytest tests/unit/test_event_router.py -v

# WebSocket Subscriber tests
pytest tests/unit/test_websocket_subscriber.py -v

# Polling Subscriber tests
pytest tests/unit/test_polling_subscriber.py -v

# Subscription Manager tests
pytest tests/unit/test_subscription_manager.py -v
```

### Run Specific Test Class
```bash
pytest tests/unit/test_event_router.py::TestEventRouting -v
```

### Run Specific Test
```bash
pytest tests/unit/test_event_router.py::TestEventRouting::test_route_event_success -v
```

### Run with Coverage
```bash
pytest tests/unit/ --cov=src/services --cov-report=term-missing
```

### Run with Coverage HTML Report
```bash
pytest tests/unit/ --cov=src/services --cov-report=html
open htmlcov/index.html
```

## Test Structure

Each test file follows a consistent structure:

1. **Fixtures**: Reusable test components
   - Configuration objects
   - Mock objects
   - Sample data

2. **Test Classes**: Grouped by functionality
   - Basics: Initialization, configuration
   - Core functionality: Main features
   - Error handling: Edge cases and failures
   - Health checks: Status monitoring
   - Lifecycle: Start/stop behavior

3. **Test Methods**: Individual test cases
   - Clear naming: `test_<feature>_<scenario>`
   - Async where needed: `@pytest.mark.asyncio`
   - Proper setup/teardown via fixtures

## Mock Strategy

All tests use mocking to avoid external dependencies:

- **WebSocket connections**: Mocked `aiohttp.ClientSession`
- **HTTP requests**: Mocked responses
- **Event handlers**: `AsyncMock` for callbacks
- **Time delays**: Fast intervals for testing

## Test Coverage Goals

- ✅ **Line coverage**: > 90%
- ✅ **Branch coverage**: > 85%
- ✅ **Function coverage**: > 95%

## Adding New Tests

When adding new functionality:

1. Create test fixtures for new configuration
2. Add test class for new feature area
3. Test happy path first
4. Add error handling tests
5. Test edge cases
6. Update this README

## Common Test Patterns

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_function(self, fixture):
    result = await async_function()
    assert result is True
```

### Mocking Async Methods
```python
mock_method = AsyncMock()
mock_method.return_value = "result"
```

### Testing Retries
```python
mock_handler.side_effect = [
    Exception("Fail 1"),
    Exception("Fail 2"),
    None  # Success on third try
]
```

### Testing Timeouts
```python
with pytest.raises(asyncio.TimeoutError):
    await asyncio.wait_for(long_operation(), timeout=0.1)
```

## Troubleshooting

### ImportError
Make sure PYTHONPATH is set:
```bash
export PYTHONPATH=/path/to/ppl-meta-vmeta
```

### Async Warnings
Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

### Mock Not Working
Verify the import path in `@patch`:
```python
@patch('src.services.module.ClassName')
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Unit Tests
  run: |
    source venv/bin/activate
    pytest tests/unit/ -v --cov=src/services
```

## Performance

Tests are optimized for speed:
- Short polling intervals (0.1-1.0s)
- Fast retry delays (0.1s)
- Minimal async waits
- Parallel execution safe

Typical run time: **< 30 seconds** for all test suites
