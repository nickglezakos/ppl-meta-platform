# MVR-People Performance Benchmarks

## Overview

This directory contains comprehensive performance benchmarking and load testing tools for the MVR-People system.

## Files

### 1. `performance_benchmarks.py` (~600 lines)
Comprehensive benchmark suite testing 4 critical performance areas:

- **Benchmark 1: MVR Creation Performance**
  - Target: <2 seconds per Individual
  - Tests: ML model inference, database operations, quality scoring
  - Status: Ready for real Individual data

- **Benchmark 2: Similarity Search Performance**
  - Target: <100ms for 10K embeddings
  - Tests: pgvector performance, query optimization, index efficiency
  - Scalability: Tests with 100, 1K, 5K, 10K embeddings
  - Status: Ready (requires MVR data in database)

- **Benchmark 3: Background Processing Throughput**
  - Target: 50-100 MVR/minute
  - Tests: Queue processing, retry logic, concurrent execution
  - Status: Implemented (commented out for quick testing)

- **Benchmark 4: Merge Operation Performance**
  - Target: <5 seconds per merge
  - Tests: 5-stage merge workflow timing
  - **Status: ✅ PASSED** (1.105s < 5s target)

### 2. `load_testing.py` (~450 lines)
Load and stress testing suite:

- **Load Test 1: Concurrent MVR Creation**
  - Tests: 50 concurrent operations in batches
  - Validates: Throughput under load, resource utilization

- **Load Test 2: High-Volume Similarity Searches**
  - Tests: 100 concurrent searches, 10 iterations
  - Validates: Database performance, connection pooling

- **Load Test 3: Connection Pool Stress**
  - Tests: 50 concurrent connections for 30 seconds
  - Validates: Pool saturation, query performance

- **Load Test 4: Memory and CPU Profiling**
  - Tests: Resource usage during 100 operations
  - Validates: Memory leaks, CPU utilization

### 3. `benchmark_results.json`
Machine-readable benchmark results for CI/CD integration.

### 4. `load_test_results.json`
Machine-readable load test results.

## Running Benchmarks

### Quick Test (Simulated Data)
```bash
cd ppl-meta-vmeta
python tests/performance_benchmarks.py
```

### Full Benchmarks (Requires Real Data)
1. Ensure vmeta service is running
2. Ensure database has MVR-People records
3. Run benchmarks:
```bash
python tests/performance_benchmarks.py
```

### Load Testing
```bash
python tests/load_testing.py
```

## Initial Results

### Merge Operations ✅
```
Target: <5 seconds
Result: 1.105 seconds average
Status: PASSED (78% faster than target)

Details:
  • Average: 1.105s
  • Median: 1.105s
  • Min: 1.104s
  • Max: 1.105s
  • Std Dev: 0.000s
  • Success Rate: 100%
```

### Next Steps
1. Populate database with real MVR-People records
2. Run full similarity search benchmarks
3. Test MVR creation with real Individual data
4. Execute load tests with production-like data
5. Update PERFORMANCE_REPORT.md with results

## Performance Targets Summary

| Metric | Target | Status |
|--------|--------|--------|
| MVR Creation | <2s | ⏳ Pending real data |
| Similarity Search | <100ms | ⏳ Pending MVR data |
| Background Processing | 50-100/min | ⏳ Pending testing |
| Merge Operations | <5s | ✅ PASSED (1.1s) |

## Integration with CI/CD

Benchmarks can be automated in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Performance Benchmarks
  run: |
    cd ppl-meta-vmeta
    python tests/performance_benchmarks.py
    
- name: Check Performance Regression
  run: |
    python scripts/check_performance_regression.py \
      --results tests/benchmark_results.json \
      --baseline benchmarks/baseline.json \
      --threshold 10
```

## Monitoring

Benchmark results should be tracked over time:
- Grafana dashboards for visualization
- Prometheus metrics for alerting
- Weekly automated benchmark runs
- Performance regression detection

## Documentation

See `/Users/nickgklezakos/Documents/ppl-meta-code/docs/vision-vmeta/PERFORMANCE_REPORT.md` for detailed performance analysis and recommendations.
