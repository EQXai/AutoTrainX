"""Pytest configuration and fixtures for database tests."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Generator

from src.database import EnhancedDatabaseManager, ExecutionStatus, PipelineMode
from src.database.factory import DatabaseConfig
from src.database.models import Base, Execution, Variation


@pytest.fixture(scope="function")
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        os.unlink(db_path)


@pytest.fixture(scope="function")
def sqlite_config(temp_db_path: Path) -> DatabaseConfig:
    """Create SQLite database configuration for testing."""
    return DatabaseConfig(
        db_type="sqlite",
        db_path=temp_db_path,
        echo=False,
        pool_config={"size": 1, "max_overflow": 0}
    )


@pytest.fixture(scope="function")
def postgresql_config() -> DatabaseConfig:
    """Create PostgreSQL database configuration for testing.
    
    Note: Requires PostgreSQL to be running and test database to exist.
    Set TEST_DATABASE_URL environment variable to override.
    """
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://autotrainx:testpass@localhost:5432/autotrainx_test"
    )
    
    return DatabaseConfig(
        db_type="postgresql",
        db_url=test_db_url,
        echo=False,
        pool_config={"size": 5, "max_overflow": 10}
    )


@pytest.fixture(scope="function")
def db_manager(sqlite_config: DatabaseConfig) -> Generator[EnhancedDatabaseManager, None, None]:
    """Create database manager with SQLite for testing."""
    manager = EnhancedDatabaseManager(config=sqlite_config, enable_monitoring=False)
    yield manager
    
    # Cleanup
    if hasattr(manager, "engine"):
        manager.engine.dispose()


@pytest.fixture(scope="function")
def db_manager_postgresql(postgresql_config: DatabaseConfig) -> Generator[EnhancedDatabaseManager, None, None]:
    """Create database manager with PostgreSQL for testing.
    
    Skip if PostgreSQL is not available.
    """
    pytest.importorskip("psycopg2")
    
    try:
        manager = EnhancedDatabaseManager(config=postgresql_config, enable_monitoring=False)
        
        # Clean up any existing test data
        with manager.engine.connect() as conn:
            conn.execute("TRUNCATE executions, variations, job_summary_cache CASCADE")
            conn.commit()
        
        yield manager
        
        # Cleanup
        with manager.engine.connect() as conn:
            conn.execute("TRUNCATE executions, variations, job_summary_cache CASCADE")
            conn.commit()
        
        manager.engine.dispose()
        
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing."""
    return {
        "job_id": "test-job-001",
        "pipeline_mode": PipelineMode.SINGLE.value,
        "dataset_name": "test_dataset",
        "preset": "test_preset",
        "total_steps": 100
    }


@pytest.fixture
def sample_variation_data():
    """Sample variation data for testing."""
    return {
        "job_id": "test-var-001",
        "parent_job_id": "test-job-001",
        "experiment_name": "test_experiment",
        "variation_id": "var_1",
        "dataset_name": "test_dataset",
        "preset": "test_preset",
        "varied_parameters": {"learning_rate": 0.001},
        "parameter_values": {"batch_size": 32}
    }


@pytest.fixture
def multiple_executions_data():
    """Multiple execution records for batch testing."""
    return [
        {
            "job_id": f"batch-job-{i:03d}",
            "pipeline_mode": PipelineMode.SINGLE.value,
            "dataset_name": f"dataset_{i % 3}",
            "preset": f"preset_{i % 2}",
            "total_steps": 100 + i * 10
        }
        for i in range(10)
    ]


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset any global caches between tests."""
    # This will be called before each test
    yield
    # Cleanup after test if needed


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "postgresql: marks tests that require PostgreSQL"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks performance benchmark tests"
    )