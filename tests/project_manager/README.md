# Project Manager Tests

Test suite for the Project Manager service functionality, including container operations, command execution, and git operations.

## Overview

This directory contains tests for:
- Container lifecycle operations (create, start, stop, delete)
- Command execution within containers
- Git operations (commit, log, reset)
- Workspace management
- Secret synchronization
- State synchronization with Redis

## Test Files

- `test_container_ops.py` - Container lifecycle testing
- `test_exec.py` - Command execution testing
- `test_git.py` - Git operations testing
- `test_workspace.py` - Workspace management testing
- `test_secret_sync.py` - Secret synchronization testing

## Running Project Manager Tests

```bash
# Run all Project Manager tests
pytest tests/project_manager/ -v

# Run specific test file
pytest tests/project_manager/test_container_ops.py -v

# Run with Docker (requires Docker running)
pytest tests/project_manager/ -v --docker

# Run with coverage
pytest tests/project_manager/ --cov=project-manager/app
```

## Test Coverage

Project Manager tests verify:

### 1. Container Operations
- ✅ Container creation with correct image
- ✅ Container naming (vibe-{project_id})
- ✅ Network attachment (vibe-network)
- ✅ Volume mounts (/workspace)
- ✅ Resource limits (CPU, memory)
- ✅ Container labels
- ✅ Container start/stop/restart
- ✅ Container removal

### 2. Command Execution
- ✅ Execute shell commands
- ✅ Working directory specification
- ✅ Command timeout handling
- ✅ Output capture (stdout/stderr)
- ✅ Output truncation (MAX_OUTPUT_SIZE)
- ✅ Exit code capture
- ✅ Container auto-start if stopped

### 3. Git Operations
- ✅ Git commit (with add_all)
- ✅ Git log retrieval
- ✅ Git reset (soft, hard)
- ✅ Workspace backup creation
- ✅ Error handling

### 4. Workspace Management
- ✅ Directory creation
- ✅ Template file copying
- ✅ Permission setting (755)
- ✅ Git initialization

### 5. Secret Synchronization
- ✅ GitHub CLI config creation
- ✅ OAuth token setting
- ✅ File permissions (600)
- ✅ Config directory creation

### 6. State Synchronization
- ✅ Redis state updates
- ✅ Container status sync
- ✅ Last seen timestamp updates
- ✅ Monitor loop functionality

## Example Tests

### Testing Container Creation

```python
@pytest.mark.asyncio
async def test_create_container(project_manager, docker_client):
    """Test container creation with correct configuration"""
    request = ProjectRequest(
        project_id="alice-test",
        username="alice",
        project_type="python",
        database="none",
        redis=False
    )

    result = await project_manager.create_project(request)

    assert result["project_id"] == "alice-test"
    assert "container_id" in result
    assert result["status"] == "running"

    # Verify container exists
    container = docker_client.containers.get(f"vibe-alice-test")
    assert container.status == "running"

    # Verify network
    assert "vibe-network" in [net.name for net in container.attrs["NetworkSettings"]["Networks"]]

    # Cleanup
    container.stop()
    container.remove()
```

### Testing Command Execution

```python
@pytest.mark.asyncio
async def test_exec_command(project_manager):
    """Test command execution in container"""
    # Assume container already created
    project_id = "alice-test"

    command = ExecCommand(
        cmd="echo 'Hello World'",
        cwd="/workspace",
        timeout=30
    )

    result = await project_manager.exec_in_project(project_id, command)

    assert result["returncode"] == 0
    assert "Hello World" in result["stdout"]
    assert result["stderr"] == ""
```

### Testing Git Operations

```python
@pytest.mark.asyncio
async def test_git_commit(project_manager, test_container):
    """Test git commit in project container"""
    project_id = "alice-test"

    # Create a test file
    await project_manager.exec_in_project(
        project_id,
        ExecCommand(cmd="echo 'test' > test.txt", cwd="/workspace")
    )

    # Commit
    commit_data = {
        "message": "Test commit",
        "add_all": True
    }

    result = await project_manager.git_commit(project_id, commit_data)

    assert result["returncode"] == 0
    assert "backup_path" in result  # Backup created

    # Verify commit exists
    log_result = await project_manager.git_log(project_id, {"max_count": 1})
    assert "Test commit" in log_result["stdout"]
```

### Testing Workspace Setup

```python
def test_workspace_preparation(project_manager, tmp_path):
    """Test workspace directory preparation"""
    project_id = "alice-test"

    workspace_path = project_manager._prepare_workspace(project_id)

    # Check directory exists
    assert os.path.exists(workspace_path)
    assert os.path.isdir(workspace_path)

    # Check permissions
    stat_info = os.stat(workspace_path)
    assert stat.S_IMODE(stat_info.st_mode) == 0o755

    # Cleanup
    shutil.rmtree(workspace_path)
```

### Testing Secret Sync

```python
@pytest.mark.asyncio
async def test_secret_sync(secret_sync_service, docker_client):
    """Test GitHub CLI secret synchronization"""
    # Create test container
    container = docker_client.containers.create(
        image="vibe-project-python:latest",
        name="test-secret-sync"
    )
    container.start()

    secrets = {
        "github_api_key": "ghp_test123",
        "github_username": "testuser"
    }

    await secret_sync_service.sync_to_container(container.id, secrets)

    # Verify config file created
    result = container.exec_run(
        ["cat", "/home/coder/.config/gh/config.yml"]
    )
    assert result.exit_code == 0
    assert b"ghp_test123" in result.output

    # Verify permissions
    result = container.exec_run(
        ["stat", "-c", "%a", "/home/coder/.config/gh/config.yml"]
    )
    assert result.output.decode().strip() == "600"

    # Cleanup
    container.stop()
    container.remove()
```

### Testing Container Monitoring

```python
@pytest.mark.asyncio
async def test_container_monitoring(project_manager, redis_client):
    """Test container state sync to Redis"""
    project_id = "alice-test"

    # Run one monitor cycle
    await project_manager.monitor_containers()

    # Check Redis updated
    status = redis_client.hget(f"project:{project_id}", "status")
    assert status in ["running", "stopped", "exited"]

    last_seen = redis_client.hget(f"project:{project_id}", "last_seen")
    assert last_seen is not None
```

## Test Fixtures

```python
@pytest.fixture
def docker_client():
    """Docker client for testing"""
    import docker
    client = docker.from_env()
    yield client
    client.close()

@pytest.fixture
def project_manager():
    """ProjectManager instance"""
    from app.services import ProjectManager
    pm = ProjectManager()
    yield pm

@pytest.fixture
async def test_container(docker_client):
    """Create test container, cleanup after"""
    container = docker_client.containers.create(
        image="vibe-project-python:latest",
        name="test-container",
        detach=True
    )
    container.start()

    yield container

    container.stop()
    container.remove()

@pytest.fixture
def redis_client():
    """Redis client for testing"""
    import fakeredis
    return fakeredis.FakeRedis(decode_responses=True)
```

## Best Practices

1. **Clean up containers** - Always stop and remove test containers
2. **Use unique names** - Avoid naming conflicts
3. **Test resource limits** - Verify CPU and memory constraints
4. **Test error cases** - Invalid images, network errors, timeouts
5. **Mock Docker when possible** - Use docker-py-test for unit tests

## Debugging

### Check container logs

```bash
docker logs vibe-{project_id}
```

### Inspect container

```bash
docker inspect vibe-{project_id}
```

### Execute commands manually

```bash
docker exec -it vibe-{project_id} /bin/bash
```

### Check Redis state

```bash
redis-cli HGETALL project:{project_id}
```

## Requirements

- Docker running locally
- Docker socket access (`/var/run/docker.sock`)
- Project images built (`vibe-project-python`, etc.)
- Redis running (or fakeredis)

## Documentation

For more information, see the main [tests README](../README.md)
