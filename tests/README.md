# Tests

Comprehensive test suite for the VIBE Coding Platform.

## Overview

This directory contains all tests for the platform components:
- **API Tests**: Central API endpoint testing
- **Activation Tests**: End-to-end project creation and activation flows
- **Project Manager Tests**: Container orchestration testing
- **Unit Tests**: Individual service and utility testing

## Test Structure

```
tests/
├── api/                    # Central API tests
│   ├── test_endpoints.py
│   ├── test_auth.py
│   └── test_rate_limiting.py
├── activation/             # E2E activation flow tests
│   ├── test_project_creation.py
│   └── test_project_lifecycle.py
├── project_manager/        # Project Manager tests
│   ├── test_container_ops.py
│   └── test_exec.py
├── test_repository.py      # Database repository tests
├── test_rate_limiter.py    # Rate limiting tests
└── conftest.py             # Pytest fixtures and configuration
```

## Running Tests

### All Tests

```bash
cd /home/user/vibe-coding-platform

# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov=cleanup --cov=project-manager --cov-report=html
```

### Specific Test Suites

```bash
# API tests only
pytest tests/api/ -v

# Activation flow tests only
pytest tests/activation/ -v

# Project Manager tests only
pytest tests/project_manager/ -v

# Single test file
pytest tests/test_repository.py -v

# Single test function
pytest tests/api/test_auth.py::test_valid_api_key -v
```

### With Coverage

```bash
# Generate coverage report
pytest --cov=api/app --cov=cleanup/app --cov=project-manager/app \
       --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Test Requirements

### Dependencies

All test dependencies are in `requirements-dev.txt`:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `httpx` - HTTP client for API testing
- `fakeredis` - Redis mocking
- `pytest-docker` - Docker container testing

### Environment Setup

Tests require:
- **Redis**: Running on localhost:6379 (or use fakeredis)
- **Docker**: For integration tests (optional)
- **Test Database**: SQLite in-memory or `/tmp/test.db`

Set test environment variables:

```bash
export TEST_MODE=true
export REDIS_HOST=localhost
export DB_PATH=/tmp/test-projects.db
export API_KEY=test-api-key
```

## Test Categories

### 1. Unit Tests
Test individual functions and classes in isolation:
- `test_repository.py` - Database operations
- `test_rate_limiter.py` - Rate limiting logic
- `test_security.py` - Password hashing and validation

### 2. Integration Tests
Test interactions between components:
- `tests/api/` - API endpoint integration
- `tests/project_manager/` - Container operations

### 3. End-to-End Tests
Test complete user workflows:
- `tests/activation/` - Full project creation and activation flow

## Writing New Tests

### Test File Template

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_example():
    """Test description"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/endpoint")
        assert response.status_code == 200
```

### Using Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
async def test_client():
    """Async HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def redis_client():
    """Redis client (fakeredis for testing)"""
    import fakeredis
    return fakeredis.FakeRedis()

@pytest.fixture
def test_project():
    """Sample project data"""
    return {
        "project_id": "test-user-test-project",
        "username": "test-user",
        "project_type": "python"
    }
```

## Continuous Integration

Tests run automatically on:
- Pull requests to main branch
- Commits to main branch
- Manual workflow dispatch

See `.github/workflows/tests.yml` for CI configuration.

## Test Coverage Goals

- **Overall**: > 80% coverage
- **API Services**: > 90% coverage
- **Critical Paths**: 100% coverage (auth, rate limiting, container creation)

## Common Test Patterns

### Testing Authentication

```python
async def test_valid_api_key(test_client):
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={"username": "test", "project_name": "app"}
    )
    assert response.status_code == 200

async def test_invalid_api_key(test_client):
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "invalid-key"},
        json={"username": "test", "project_name": "app"}
    )
    assert response.status_code == 401
```

### Testing Rate Limiting

```python
async def test_rate_limit_exceeded(test_client, redis_client):
    # Make requests up to limit
    for _ in range(100):
        await test_client.get("/endpoint")

    # Next request should be rate limited
    response = await test_client.get("/endpoint")
    assert response.status_code == 429
```

### Testing Database Operations

```python
def test_create_project(repository):
    project = repository.create_project({
        "project_id": "test-project",
        "username": "test-user"
    })
    assert project.project_id == "test-project"

    # Verify in database
    found = repository.get_project("test-project")
    assert found is not None
```

## Troubleshooting

### Tests Fail Due to Redis Connection

Use fakeredis for unit tests:

```python
import fakeredis
redis_client = fakeredis.FakeRedis()
```

### Tests Fail Due to Docker Permission

Ensure your user is in the docker group:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Slow Test Execution

Run specific test files instead of full suite:

```bash
pytest tests/test_repository.py -v
```

Use pytest-xdist for parallel execution:

```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

## Documentation

For more details on testing strategy and organization, see [agents.md](./agents.md)
