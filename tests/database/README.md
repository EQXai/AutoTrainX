# Database Tests

Comprehensive test suite for the AutoTrainX database module.

## Test Structure

```
tests/database/
├── unit/                    # Unit tests for individual components
│   ├── test_models.py      # Model tests
│   ├── test_batch_operations.py  # Batch operations tests
│   ├── test_query_cache.py       # Cache system tests
│   └── test_optimized_queries.py # Optimized query tests
├── integration/             # Integration tests
│   └── test_full_workflow.py     # Complete workflow tests
├── performance/             # Performance benchmarks
│   └── test_benchmarks.py        # Performance tests
└── conftest.py             # Pytest fixtures and configuration
```

## Running Tests

### Run all tests
```bash
pytest tests/database/
```

### Run specific test categories
```bash
# Unit tests only
pytest tests/database/unit/

# Integration tests
pytest tests/database/integration/

# Performance benchmarks
pytest tests/database/performance/ -m benchmark

# Exclude slow tests
pytest tests/database/ -m "not slow"

# PostgreSQL tests (requires PostgreSQL)
pytest tests/database/ -m postgresql
```

### Run with coverage
```bash
pytest tests/database/ --cov=src/database --cov-report=html
```

## Test Fixtures

### Database Managers
- `db_manager`: SQLite-based manager for fast unit tests
- `db_manager_postgresql`: PostgreSQL manager for integration tests

### Test Data
- `sample_execution_data`: Single execution test data
- `sample_variation_data`: Single variation test data
- `multiple_executions_data`: Batch test data

## Performance Benchmarks

The benchmark tests measure:
- Single vs batch operation performance
- Query optimization effectiveness
- Cache hit/miss performance
- Large dataset handling (10k+ records)

### Running benchmarks
```bash
# Quick benchmarks
pytest tests/database/performance/ -m benchmark

# Include large dataset tests
pytest tests/database/performance/ -m "benchmark" --run-slow
```

## Test Coverage Goals

- Unit tests: >90% coverage
- Integration tests: Key workflows covered
- Performance tests: Regression prevention

## Environment Variables

- `TEST_DATABASE_URL`: PostgreSQL connection for tests
- `PYTEST_SKIP_POSTGRESQL`: Skip PostgreSQL tests

## Common Issues

1. **PostgreSQL tests failing**: Ensure PostgreSQL is running and test database exists
2. **Slow tests**: Use `-m "not slow"` to skip time-consuming tests
3. **Coverage reports**: HTML report in `htmlcov/index.html`