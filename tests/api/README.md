# Central API Tests

Test suite for the Central API Service endpoints, authentication, and business logic.

## Overview

This directory contains tests for:
- Project CRUD endpoints
- Command execution endpoints
- Git operation endpoints
- Health check endpoints
- Authentication and authorization
- Rate limiting
- Input validation

## Test Files

- `test_endpoints.py` - Main endpoint testing
- `test_auth.py` - Authentication and authorization
- `test_rate_limiting.py` - Rate limiter functionality
- `test_validation.py` - Input validation and sanitization
- `test_projects.py` - Project service logic
- `test_git.py` - Git operations

## Running API Tests

```bash
# Run all API tests
pytest tests/api/ -v

# Run specific test file
pytest tests/api/test_auth.py -v

# Run with coverage
pytest tests/api/ --cov=api/app --cov-report=html

# Run specific test
pytest tests/api/test_endpoints.py::test_create_project -v
```

## Test Coverage

API tests cover:

### 1. Project Management
- ✅ Project creation with valid data
- ✅ Project creation with invalid data
- ✅ Project listing for user
- ✅ Project info retrieval
- ✅ Project deletion
- ✅ Password rotation

### 2. Authentication
- ✅ Valid API key acceptance
- ✅ Invalid API key rejection
- ✅ Valid project password
- ✅ Invalid project password
- ✅ Missing credentials

### 3. Rate Limiting
- ✅ Within rate limit
- ✅ Rate limit exceeded (429 response)
- ✅ Rate limit per endpoint
- ✅ Rate limit per user/project

### 4. Command Execution
- ✅ Valid command execution
- ✅ Command timeout handling
- ✅ Output truncation
- ✅ Error output capture

### 5. Git Operations
- ✅ Git commit
- ✅ Git log
- ✅ Git reset
- ✅ Invalid git commands

### 6. Validation
- ✅ Username validation
- ✅ Project name validation
- ✅ Command sanitization
- ✅ SQL injection prevention

## Example Tests

### Testing Project Creation

```python
@pytest.mark.asyncio
async def test_create_project_success(test_client):
    """Test successful project creation"""
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={
            "username": "alice",
            "project_name": "my-app",
            "project_type": "python",
            "database": "none",
            "redis": False
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "alice-my-app"
    assert "password" in data
    assert "preview_url" in data
```

### Testing Authentication

```python
@pytest.mark.asyncio
async def test_invalid_api_key(test_client):
    """Test that invalid API key is rejected"""
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "wrong-key"},
        json={"username": "alice", "project_name": "app"}
    )

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]
```

### Testing Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limit_exceeded(test_client):
    """Test rate limit enforcement"""
    # Make requests up to limit
    for i in range(100):
        await test_client.get(
            "/projects/test-user",
            headers={"X-API-Key": "valid-key"}
        )

    # Next request should be rate limited
    response = await test_client.get(
        "/projects/test-user",
        headers={"X-API-Key": "valid-key"}
    )

    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
```

### Testing Command Execution

```python
@pytest.mark.asyncio
async def test_exec_command(test_client, test_project):
    """Test command execution in project"""
    response = await test_client.post(
        "/exec",
        json={
            "project_id": "alice-my-app",
            "password": "project-password",
            "cmd": "echo 'Hello World'"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["returncode"] == 0
    assert "Hello World" in data["stdout"]
```

## Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
async def test_client():
    """HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def test_project(redis_client):
    """Create a test project in Redis"""
    project_data = {
        "project_id": "alice-my-app",
        "username": "alice",
        "password_hash": hash_password("test-password")
    }
    redis_client.hset("project:alice-my-app", mapping=project_data)
    return project_data

@pytest.fixture
def valid_api_key():
    """Valid API key for testing"""
    return "test-api-key"
```

## Mocking

### Mocking Project Manager

```python
@pytest.fixture
def mock_project_manager(monkeypatch):
    """Mock ProjectManagerClient"""
    async def mock_create(self, data):
        return {
            "project_id": data["project_id"],
            "container_id": "mock-container-id",
            "status": "running"
        }

    monkeypatch.setattr(
        "app.services.project_manager.ProjectManagerClient.create_project",
        mock_create
    )
```

### Mocking Redis

```python
import fakeredis

@pytest.fixture
def redis_client():
    """Fake Redis client for testing"""
    return fakeredis.FakeRedis(decode_responses=True)
```

## Best Practices

1. **Use async tests** for async endpoints
2. **Clean up after tests** - delete created projects
3. **Mock external services** - Project Manager, Docker
4. **Test edge cases** - empty strings, special characters, SQL injection
5. **Test error handling** - network errors, timeouts, invalid responses
6. **Use descriptive test names** - `test_create_project_with_invalid_username`

## Debugging Failed Tests

### Enable verbose logging

```bash
pytest tests/api/ -v -s --log-cli-level=DEBUG
```

### Run single test with debugging

```bash
pytest tests/api/test_auth.py::test_invalid_api_key -v -s
```

### Check test output

```bash
pytest tests/api/ -v --tb=short  # Short traceback
pytest tests/api/ -v --tb=long   # Full traceback
```

## Documentation

For more information, see the main [tests README](../README.md)
