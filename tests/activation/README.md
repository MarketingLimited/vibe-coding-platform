# Activation Flow Tests

End-to-end tests for project creation and activation workflows.

## Overview

This directory contains integration tests that verify the complete project lifecycle:
- Project creation flow from API to container
- Workspace setup and template copying
- Container startup and readiness
- Secret synchronization
- Git initialization
- First command execution
- Project deactivation and cleanup

## Test Files

- `test_project_creation.py` - Full project creation flow
- `test_project_lifecycle.py` - Complete lifecycle (create, use, delete)
- `test_activation.py` - Container activation and readiness
- `test_workspace_setup.py` - Workspace and template verification

## Running Activation Tests

```bash
# Run all activation tests
pytest tests/activation/ -v

# Run with Docker (requires Docker running)
pytest tests/activation/ -v --docker

# Run specific flow
pytest tests/activation/test_project_creation.py -v

# Run with detailed logging
pytest tests/activation/ -v -s --log-cli-level=INFO
```

## Test Coverage

Activation tests verify:

### 1. Project Creation Flow
- ✅ API receives create request
- ✅ Request forwarded to Project Manager
- ✅ Workspace directory created
- ✅ Template files copied
- ✅ Docker container created
- ✅ Container started successfully
- ✅ Secrets synced to container
- ✅ Redis state updated
- ✅ Response returned to client

### 2. Workspace Setup
- ✅ Directory permissions (755)
- ✅ Template files present
- ✅ Git repository initialized
- ✅ .gitignore configured
- ✅ README.md present

### 3. Container Activation
- ✅ Container running state
- ✅ Network connectivity
- ✅ Volume mounts correct
- ✅ Environment variables set
- ✅ User permissions correct

### 4. Secret Synchronization
- ✅ GitHub CLI config present
- ✅ Config file permissions (600)
- ✅ OAuth token set correctly

### 5. First Command Execution
- ✅ Shell access works
- ✅ Working directory correct
- ✅ Basic commands execute
- ✅ Output captured correctly

### 6. Project Deactivation
- ✅ Container stops gracefully
- ✅ Container removed
- ✅ Workspace preserved (or deleted)
- ✅ Redis state cleaned up

## Example Tests

### Testing Full Creation Flow

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_project_creation(test_client):
    """Test complete project creation flow"""
    # 1. Create project via API
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={
            "username": "alice",
            "project_name": "test-app",
            "project_type": "python",
            "github_api_key": "ghp_test123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    project_id = data["project_id"]
    password = data["password"]

    # 2. Verify workspace created
    workspace_path = f"/projects/{project_id}"
    assert os.path.exists(workspace_path)
    assert os.path.exists(f"{workspace_path}/README.md")
    assert os.path.exists(f"{workspace_path}/.gitignore")

    # 3. Verify container running
    container = docker_client.containers.get(f"vibe-{project_id}")
    assert container.status == "running"

    # 4. Verify first command works
    exec_response = await test_client.post(
        "/exec",
        json={
            "project_id": project_id,
            "password": password,
            "cmd": "python --version"
        }
    )

    assert exec_response.status_code == 200
    assert exec_response.json()["returncode"] == 0

    # Cleanup
    await test_client.delete(
        "/projects/delete",
        json={"project_id": project_id, "password": password}
    )
```

### Testing Workspace Setup

```python
@pytest.mark.asyncio
async def test_workspace_setup(test_client, docker_client):
    """Verify workspace is set up correctly"""
    # Create project
    response = await test_client.post("/projects/create", ...)
    project_id = response.json()["project_id"]

    workspace_path = f"/projects/{project_id}"

    # Check directory exists
    assert os.path.isdir(workspace_path)

    # Check permissions
    stat_info = os.stat(workspace_path)
    assert stat.S_IMODE(stat_info.st_mode) == 0o755

    # Check template files
    expected_files = ["README.md", ".gitignore", "setup.sh"]
    for file in expected_files:
        assert os.path.exists(f"{workspace_path}/{file}")

    # Check git initialized
    assert os.path.exists(f"{workspace_path}/.git")
```

### Testing Container Activation

```python
@pytest.mark.asyncio
async def test_container_activation(docker_client):
    """Test container starts and becomes ready"""
    # Create and start container
    container = docker_client.containers.create(
        image="vibe-project-python:latest",
        name="test-container"
    )
    container.start()

    # Wait for container to be ready
    for _ in range(10):
        container.reload()
        if container.status == "running":
            break
        await asyncio.sleep(1)

    assert container.status == "running"

    # Test command execution
    result = container.exec_run(["python", "--version"])
    assert result.exit_code == 0
    assert b"Python 3.11" in result.output

    # Cleanup
    container.stop()
    container.remove()
```

### Testing Secret Sync

```python
@pytest.mark.asyncio
async def test_secret_synchronization(test_client, docker_client):
    """Verify GitHub credentials are synced to container"""
    github_token = "ghp_test123456"

    # Create project with GitHub token
    response = await test_client.post(
        "/projects/create",
        headers={"X-API-Key": "valid-key"},
        json={
            "username": "alice",
            "project_name": "test",
            "project_type": "python",
            "github_api_key": github_token
        }
    )

    project_id = response.json()["project_id"]
    container = docker_client.containers.get(f"vibe-{project_id}")

    # Check GitHub CLI config exists
    result = container.exec_run(
        ["cat", "/home/coder/.config/gh/config.yml"]
    )
    assert result.exit_code == 0

    # Verify token in config
    config_content = result.output.decode()
    assert github_token in config_content

    # Check file permissions
    result = container.exec_run(
        ["stat", "-c", "%a", "/home/coder/.config/gh/config.yml"]
    )
    assert result.output.decode().strip() == "600"
```

## Test Requirements

### Docker
Activation tests require Docker to be running:

```bash
# Check Docker is running
docker ps

# Ensure test images are built
docker images | grep vibe-project
```

### Permissions
Tests need access to:
- Docker socket (`/var/run/docker.sock`)
- Projects directory (for workspace verification)
- Redis (for state verification)

### Environment Variables

```bash
export TEST_MODE=true
export DOCKER_NETWORK=vibe-network-test
export PROJECTS_DIR=/tmp/test-projects
export REDIS_HOST=localhost
```

## Fixtures

```python
@pytest.fixture(scope="module")
def docker_client():
    """Docker client for container testing"""
    import docker
    client = docker.from_env()
    yield client
    client.close()

@pytest.fixture
async def created_project(test_client):
    """Create a project for testing, cleanup after"""
    response = await test_client.post("/projects/create", ...)
    project_data = response.json()

    yield project_data

    # Cleanup
    await test_client.delete("/projects/delete", json={
        "project_id": project_data["project_id"],
        "password": project_data["password"]
    })
```

## Best Practices

1. **Clean up resources** - Always delete containers and workspaces after tests
2. **Use unique names** - Avoid naming conflicts with UUID or timestamp suffixes
3. **Wait for readiness** - Poll container status before asserting
4. **Test isolation** - Each test should be independent
5. **Mock external services** - Don't make real GitHub API calls

## Debugging

### View container logs

```bash
docker logs vibe-{project_id}
```

### Inspect workspace

```bash
ls -la /projects/{project_id}
```

### Check container state

```bash
docker inspect vibe-{project_id}
```

### Enable verbose output

```bash
pytest tests/activation/ -v -s --log-cli-level=DEBUG
```

## Documentation

For more information, see the main [tests README](../README.md)
