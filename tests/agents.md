# Tests Module - دليل الـAgent

## Purpose

الـ**Tests Module** يحتوي على جميع الاختبارات للمنصة. يُدير:
- **Unit Tests**: اختبار الوحدات الفردية (functions، classes)
- **Integration Tests**: اختبار التفاعل بين المكونات
- **End-to-End Tests**: اختبار سيناريوهات المستخدم الكاملة
- **API Tests**: اختبار endpoints الـCentral API
- **Container Tests**: اختبار عمليات الـProject Manager

**Technology**: pytest + pytest-asyncio + fakeredis

**Test Coverage Goal**: > 80% overall, > 90% for critical paths

---

## Owned Scope

هذا الmodule يملك:

### Test Directories
- `/tests/api/` - Central API endpoint tests
- `/tests/activation/` - E2E project activation flow tests
- `/tests/project_manager/` - Project Manager service tests

### Unit Test Files
- `/tests/test_repository.py` - Database repository tests
- `/tests/test_rate_limiter.py` - Rate limiting logic tests
- `/tests/test_cleanup_service.py` - Cleanup service tests

### Test Configuration
- `/tests/conftest.py` - Pytest fixtures and configuration
- `/tests/__init__.py` - Test package marker

---

## Key Files & Entry Points

### Test Configuration

```python
# /tests/conftest.py
import pytest
from httpx import AsyncClient
from app.main import app
import fakeredis

@pytest.fixture
async def test_client():
    """HTTP client for API testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def redis_client():
    """Fake Redis client for unit tests"""
    return fakeredis.FakeRedis(decode_responses=True)

@pytest.fixture
def test_project():
    """Sample project data for testing"""
    return {
        "project_id": "test-user-test-app",
        "username": "test-user",
        "project_name": "test-app",
        "project_type": "python"
    }
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific directory
pytest tests/api/ -v

# Specific file
pytest tests/test_repository.py -v

# Specific test
pytest tests/api/test_auth.py::test_valid_api_key -v

# With coverage
pytest tests/ --cov=api --cov=cleanup --cov=project-manager --cov-report=html

# Parallel execution
pytest -n auto
```

---

## Test Categories

### 1. Unit Tests

Test individual functions and classes in isolation:

**Files**:
- `test_repository.py` - ProjectRepository database operations
- `test_rate_limiter.py` - RateLimiter logic
- `test_cleanup_service.py` - CleanupService operations

**Example**:
```python
def test_create_project(repository):
    """Test project creation in database"""
    project = repository.create_project({
        "project_id": "test-project",
        "username": "alice"
    })

    assert project.project_id == "test-project"
    assert project.username == "alice"

    # Verify in database
    found = repository.get_project("test-project")
    assert found is not None
```

### 2. Integration Tests

Test interactions between components:

**Location**: `/tests/api/`

**Coverage**:
- API endpoint integration
- Service layer interaction
- Redis caching behavior
- Database operations through API

**Example**:
```python
@pytest.mark.asyncio
async def test_project_creation_flow(test_client, redis_client):
    """Test project creation through API"""
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={
            "username": "alice",
            "project_name": "my-app",
            "project_type": "python"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify in Redis
    project_data = redis_client.hgetall(f"project:{data['project_id']}")
    assert project_data is not None
```

### 3. End-to-End Tests

Test complete user workflows:

**Location**: `/tests/activation/`

**Coverage**:
- Full project creation flow (API → Project Manager → Container)
- Workspace setup and template copying
- Container activation and readiness
- First command execution
- Project deletion and cleanup

**Example**:
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_project_lifecycle(test_client, docker_client):
    """Test complete project lifecycle"""
    # Create project
    create_response = await test_client.post("/projects/create", ...)
    project_id = create_response.json()["project_id"]
    password = create_response.json()["password"]

    # Verify workspace exists
    assert os.path.exists(f"/projects/{project_id}")

    # Verify container running
    container = docker_client.containers.get(f"vibe-{project_id}")
    assert container.status == "running"

    # Execute command
    exec_response = await test_client.post(
        "/exec",
        json={"project_id": project_id, "password": password, "cmd": "ls"}
    )
    assert exec_response.status_code == 200

    # Delete project
    delete_response = await test_client.delete(
        "/projects/delete",
        json={"project_id": project_id, "password": password}
    )
    assert delete_response.status_code == 200
```

---

## Test Organization

### Test Naming Convention

```python
# Unit tests: test_{function_name}
def test_hash_password():
    """Test password hashing function"""
    pass

# Integration tests: test_{component}_integration
def test_api_redis_integration():
    """Test API integration with Redis"""
    pass

# E2E tests: test_{workflow}_flow
async def test_project_creation_flow():
    """Test complete project creation workflow"""
    pass
```

### Test Markers

```python
import pytest

# Async test
@pytest.mark.asyncio
async def test_async_operation():
    pass

# Integration test (requires Docker)
@pytest.mark.integration
def test_container_creation():
    pass

# Slow test
@pytest.mark.slow
def test_long_running():
    pass

# Skip test
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass
```

### Running by Markers

```bash
# Run only async tests
pytest -m asyncio

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run specific markers
pytest -m "asyncio and not slow"
```

---

## Common Test Patterns

### 1. Testing API Endpoints

```python
@pytest.mark.asyncio
async def test_create_project_success(test_client):
    """Test successful project creation"""
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={"username": "alice", "project_name": "app"}
    )

    assert response.status_code == 200
    assert "project_id" in response.json()
    assert "password" in response.json()

@pytest.mark.asyncio
async def test_create_project_invalid_key(test_client):
    """Test project creation with invalid API key"""
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "invalid-key"},
        json={"username": "alice", "project_name": "app"}
    )

    assert response.status_code == 401
```

### 2. Testing Authentication

```python
@pytest.mark.asyncio
async def test_valid_api_key(test_client):
    """Test valid API key is accepted"""
    response = await test_client.get(
        "/projects/test-user",
        headers={"X-API-Key": "valid-key"}
    )
    assert response.status_code != 401

@pytest.mark.asyncio
async def test_missing_api_key(test_client):
    """Test missing API key is rejected"""
    response = await test_client.get("/projects/test-user")
    assert response.status_code == 401
```

### 3. Testing Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limit_enforcement(test_client, rate_limiter):
    """Test rate limit is enforced"""
    scope = "test:endpoint"
    limit = 5

    # Make requests up to limit
    for i in range(limit):
        await rate_limiter.check(scope, limit, window=60)

    # Next request should be rate limited
    with pytest.raises(HTTPException) as exc:
        await rate_limiter.check(scope, limit, window=60)

    assert exc.value.status_code == 429
```

### 4. Testing Database Operations

```python
def test_project_crud(repository):
    """Test complete CRUD operations"""
    # Create
    project = repository.create_project({"project_id": "test", "username": "alice"})
    assert project is not None

    # Read
    found = repository.get_project("test")
    assert found.project_id == "test"

    # Update
    repository.update_project("test", {"status": "active"})
    updated = repository.get_project("test")
    assert updated.status == "active"

    # Delete
    repository.delete_project("test")
    deleted = repository.get_project("test")
    assert deleted is None
```

### 5. Testing with Mocks

```python
@pytest.mark.asyncio
async def test_project_manager_integration(test_client, monkeypatch):
    """Test API integration with Project Manager"""
    # Mock ProjectManagerClient
    async def mock_create_project(self, data):
        return {
            "project_id": data["project_id"],
            "container_id": "mock-container-id",
            "status": "running"
        }

    monkeypatch.setattr(
        "app.services.project_manager.ProjectManagerClient.create_project",
        mock_create_project
    )

    # Test API endpoint
    response = await test_client.post("/projects/create", ...)
    assert response.status_code == 200
```

---

## Test Fixtures

### Common Fixtures

Located in `/tests/conftest.py`:

```python
@pytest.fixture(scope="session")
def docker_client():
    """Docker client for container testing"""
    import docker
    client = docker.from_env()
    yield client
    client.close()

@pytest.fixture
def db_session():
    """Database session for testing"""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()

@pytest.fixture
async def created_project(test_client):
    """Create a test project, cleanup after"""
    response = await test_client.post("/projects/create", ...)
    project = response.json()

    yield project

    # Cleanup
    await test_client.delete("/projects/delete", json={
        "project_id": project["project_id"],
        "password": project["password"]
    })
```

---

## Test Coverage

### Measuring Coverage

```bash
# Run with coverage
pytest tests/ --cov=api/app --cov=cleanup/app --cov=project-manager/app

# Generate HTML report
pytest tests/ --cov=api --cov-report=html

# View report
open htmlcov/index.html

# Coverage with missing lines
pytest tests/ --cov=api --cov-report=term-missing
```

### Coverage Goals

- **Overall**: > 80%
- **API Services**: > 90%
- **Critical Paths**: 100%
  - Authentication
  - Rate limiting
  - Container creation
  - Command execution
  - Data validation

---

## Best Practices

### 1. Test Isolation

Each test should be independent:
- ✅ Don't rely on test execution order
- ✅ Clean up resources after each test
- ✅ Use fixtures for setup and teardown
- ❌ Share state between tests

### 2. Descriptive Names

```python
# Good
def test_create_project_with_invalid_username_returns_400():
    pass

# Bad
def test_project():
    pass
```

### 3. One Assertion per Test (when possible)

```python
# Good
def test_project_id_format():
    project = create_project("alice", "my-app")
    assert project.project_id == "alice-my-app"

def test_project_status_after_creation():
    project = create_project("alice", "my-app")
    assert project.status == "active"

# Less ideal (but sometimes necessary)
def test_project_creation():
    project = create_project("alice", "my-app")
    assert project.project_id == "alice-my-app"
    assert project.status == "active"
    assert project.username == "alice"
```

### 4. Use Mocks for External Services

```python
# Good - Mock Docker
@pytest.fixture
def mock_docker(monkeypatch):
    def mock_create_container(*args, **kwargs):
        return Mock(id="mock-id", status="running")
    monkeypatch.setattr("docker.containers.create", mock_create_container)

# Bad - Use real Docker (for unit tests)
def test_container_creation():
    docker_client = docker.from_env()  # Real Docker connection
    container = docker_client.containers.create(...)
```

### 5. Test Edge Cases

```python
def test_username_validation():
    # Valid
    assert validate_username("alice") == True

    # Edge cases
    assert validate_username("") == False           # Empty
    assert validate_username("ab") == False         # Too short
    assert validate_username("a" * 51) == False     # Too long
    assert validate_username("alice@123") == False  # Invalid chars
    assert validate_username("ALICE") == False      # Uppercase
```

---

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main
- Manual workflow dispatch

Configuration: `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/ -v --cov=api --cov=cleanup --cov=project-manager
```

---

## Troubleshooting

### Tests Fail Locally but Pass in CI

Check:
- Environment variables set correctly
- Database state (use in-memory for tests)
- Redis connection (use fakeredis)
- Docker availability
- File permissions

### Redis Connection Error

Use fakeredis for unit tests:
```python
import fakeredis
redis_client = fakeredis.FakeRedis()
```

### Docker Permission Denied

Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Slow Test Execution

- Run specific tests: `pytest tests/test_repository.py`
- Use parallel execution: `pytest -n auto`
- Mock external services
- Skip integration tests: `pytest -m "not integration"`

---

## Common Tasks for Agents

### مهمة: إضافة test جديد

1. **Create test file** في المجلد المناسب:
```python
# tests/api/test_new_feature.py
import pytest

@pytest.mark.asyncio
async def test_new_feature(test_client):
    """Test new feature functionality"""
    response = await test_client.post("/new-endpoint", ...)
    assert response.status_code == 200
```

2. **Run test**:
```bash
pytest tests/api/test_new_feature.py -v
```

3. **Add to CI** (automatic if في tests/)

### مهمة: Debug failed test

```bash
# Run with verbose output
pytest tests/api/test_auth.py::test_invalid_key -v -s

# Show full traceback
pytest tests/api/test_auth.py -v --tb=long

# Enable debug logging
pytest tests/api/ -v --log-cli-level=DEBUG

# Drop into debugger on failure
pytest tests/api/ --pdb
```

### مهمة: Improve test coverage

1. **Check coverage report**:
```bash
pytest tests/ --cov=api/app --cov-report=term-missing
```

2. **Identify uncovered lines**

3. **Add tests for uncovered code**

4. **Verify improvement**:
```bash
pytest tests/ --cov=api/app --cov-report=html
```

---

## Documentation

For specific test suites:
- [API Tests README](./api/README.md)
- [Activation Tests README](./activation/README.md)
- [Project Manager Tests README](./project_manager/README.md)
