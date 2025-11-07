#!/usr/bin/env python3
"""
Vibe Coding Platform - Central Multi-Tenant API
Supports multiple users/projects with authentication
"""

import os
import json
import hashlib
import secrets
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis
import docker

from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import logging

# Configuration
API_PORT = int(os.getenv("API_PORT", "9000"))
API_KEY = os.getenv("API_KEY", "")
MASTER_API_KEY = API_KEY  # للعمليات الإدارية

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

MAX_PROJECTS_PER_USER = int(os.getenv("MAX_PROJECTS_PER_USER", "10"))
EXEC_TIMEOUT = int(os.getenv("EXEC_TIMEOUT", "300"))
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", str(10 * 1024 * 1024)))

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/projects")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Docker client
docker_client = docker.from_env()

# FastAPI app
app = FastAPI(
    title="Vibe Coding Central API",
    version="2.0.0",
    description="Multi-tenant development platform",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# =============================================================================
# Models
# =============================================================================

class ProjectCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-z0-9_-]+$')
    project_name: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-z0-9_-]+$')
    project_type: str = Field("python", pattern=r'^(python|nodejs|php|full)$')
    database: Optional[str] = Field(None, pattern=r'^(postgres|mysql|sqlite|none)?$')
    redis: bool = False

class ProjectAuth(BaseModel):
    project_id: str
    password: str

class ExecRequest(ProjectAuth):
    cmd: str = Field(..., min_length=1, max_length=10000)
    cwd: Optional[str] = Field("/workspace", max_length=500)
    timeout: Optional[int] = Field(EXEC_TIMEOUT, ge=1, le=EXEC_TIMEOUT)

class ExecResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float

class ProjectInfo(BaseModel):
    project_id: str
    username: str
    project_name: str
    project_type: str
    created_at: str
    status: str
    container_id: Optional[str]

# =============================================================================
# Helper Functions
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password with SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_password(length: int = 16) -> str:
    """Generate secure random password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_project_id(username: str, project_name: str) -> str:
    """Generate unique project ID"""
    return f"{username}-{project_name}"

def verify_master_key(x_api_key: Optional[str] = Header(None)):
    """Verify master API key for admin operations"""
    if not MASTER_API_KEY or x_api_key != MASTER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid master API key")

def get_project_data(project_id: str) -> Optional[Dict]:
    """Get project data from Redis"""
    data = redis_client.hgetall(f"project:{project_id}")
    return dict(data) if data else None

def verify_project_auth(project_id: str, password: str) -> bool:
    """Verify project authentication"""
    project = get_project_data(project_id)
    if not project:
        return False
    return project.get("password_hash") == hash_password(password)

def get_project_container(project_id: str) -> Optional[docker.models.containers.Container]:
    """Get project Docker container"""
    try:
        containers = docker_client.containers.list(
            filters={"label": f"com.vibe.project-id={project_id}"}
        )
        return containers[0] if containers else None
    except Exception as e:
        logger.error(f"Error getting container for {project_id}: {e}")
        return None

def create_project_container(project_id: str, project_type: str, database: Optional[str]) -> str:
    """Create new project container"""
    try:
        # Select base image
        images = {
            "python": "vibe-project-python:latest",
            "nodejs": "vibe-project-nodejs:latest",
            "php": "vibe-project-php:latest",
            "full": "vibe-project-full:latest",
        }
        image = images.get(project_type, "vibe-project-python:latest")
        
        # Environment variables
        env = {
            "PROJECT_ID": project_id,
            "WORKSPACE": "/workspace",
        }
        
        if database:
            env[f"{database.upper()}_ENABLED"] = "true"
        
        # Create container
        container = docker_client.containers.create(
            image=image,
            name=f"vibe-{project_id}",
            detach=True,
            environment=env,
            volumes={
                f"{PROJECTS_DIR}/{project_id}": {"bind": "/workspace", "mode": "rw"}
            },
            network="vibe-network",
            labels={
                "com.vibe.project-id": project_id,
                "com.vibe.project-type": project_type,
            },
            mem_limit="4g",
            cpu_period=100000,
            cpu_quota=200000,  # 2 CPUs
            read_only=False,
            tmpfs={"/tmp": "size=512m"},
        )
        
        container.start()
        
        logger.info(f"Created container for {project_id}: {container.id}")
        return container.id
        
    except Exception as e:
        logger.error(f"Error creating container for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create container: {str(e)}")

# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "name": "Vibe Coding Central API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "projects": {
                "create": "POST /projects/create",
                "list": "GET /projects/{username}",
                "info": "GET /projects/info",
                "delete": "DELETE /projects/delete",
            },
            "exec": "POST /exec",
        }
    }

@app.get("/health")
async def health():
    """Health check"""
    try:
        redis_client.ping()
        docker_client.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "redis": "connected",
            "docker": "connected",
            "projects_count": len(redis_client.keys("project:*")),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")

@app.post("/projects/create", dependencies=[Depends(verify_master_key)])
async def create_project(data: ProjectCreate):
    """Create new project (requires master API key)"""
    
    # Generate project ID
    project_id = generate_project_id(data.username, data.project_name)
    
    # Check if exists
    if redis_client.exists(f"project:{project_id}"):
        raise HTTPException(status_code=400, detail="Project already exists")
    
    # Check user's project limit
    user_projects = redis_client.smembers(f"user:{data.username}:projects")
    if len(user_projects) >= MAX_PROJECTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_PROJECTS_PER_USER} projects per user")
    
    # Generate password
    password = generate_password()
    password_hash = hash_password(password)
    
    # Create project directory
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, ".logs"), exist_ok=True)
    
    # Create container
    container_id = create_project_container(project_id, data.project_type, data.database)
    
    # Store project data
    project_data = {
        "project_id": project_id,
        "username": data.username,
        "project_name": data.project_name,
        "project_type": data.project_type,
        "database": data.database or "none",
        "redis": str(data.redis),
        "password_hash": password_hash,
        "container_id": container_id,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    
    redis_client.hset(f"project:{project_id}", mapping=project_data)
    redis_client.sadd(f"user:{data.username}:projects", project_id)
    
    logger.info(f"Created project: {project_id}")
    
    return {
        "project_id": project_id,
        "password": password,  # Return only once!
        "status": "ready",
        "container_id": container_id,
        "message": "Save this password! It won't be shown again.",
    }

@app.get("/projects/{username}")
async def list_projects(username: str, x_api_key: Optional[str] = Header(None)):
    """List user's projects"""
    verify_master_key(x_api_key)
    
    project_ids = redis_client.smembers(f"user:{username}:projects")
    
    projects = []
    for project_id in project_ids:
        project = get_project_data(project_id)
        if project:
            # Remove sensitive data
            project.pop("password_hash", None)
            projects.append(project)
    
    return {"username": username, "projects": projects}

@app.post("/projects/info")
async def get_project_info(auth: ProjectAuth):
    """Get project information"""
    
    if not verify_project_auth(auth.project_id, auth.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    project = get_project_data(auth.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Remove password
    project.pop("password_hash", None)
    
    # Get container status
    container = get_project_container(auth.project_id)
    if container:
        project["container_status"] = container.status
    
    return project

@app.post("/exec", response_model=ExecResponse)
async def execute_command(req: ExecRequest):
    """Execute command in project container"""
    
    # Verify authentication
    if not verify_project_auth(req.project_id, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Get container
    container = get_project_container(req.project_id)
    if not container:
        raise HTTPException(status_code=404, detail="Project container not found")
    
    # Check if running
    if container.status != "running":
        try:
            container.start()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")
    
    # Execute command
    start_time = datetime.now()
    
    try:
        result = container.exec_run(
            f"bash -lc '{req.cmd}'",
            workdir=req.cwd,
            demux=True,
            stream=False,
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        stdout = result.output[0].decode('utf-8', errors='replace') if result.output[0] else ""
        stderr = result.output[1].decode('utf-8', errors='replace') if result.output[1] else ""
        
        # Truncate if needed
        if len(stdout) > MAX_OUTPUT_SIZE:
            stdout = stdout[:MAX_OUTPUT_SIZE] + "\n...[truncated]"
        if len(stderr) > MAX_OUTPUT_SIZE:
            stderr = stderr[:MAX_OUTPUT_SIZE] + "\n...[truncated]"
        
        return ExecResponse(
            returncode=result.exit_code,
            stdout=stdout,
            stderr=stderr,
            elapsed_seconds=round(elapsed, 3)
        )
    
    except Exception as e:
        logger.error(f"Execution error in {req.project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/projects/delete")
async def delete_project(auth: ProjectAuth, x_api_key: Optional[str] = Header(None)):
    """Delete project (requires master key or project password)"""
    
    # Verify either master key or project password
    is_admin = x_api_key == MASTER_API_KEY if MASTER_API_KEY else False
    is_owner = verify_project_auth(auth.project_id, auth.password)
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Get project data
    project = get_project_data(auth.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Stop and remove container
    container = get_project_container(auth.project_id)
    if container:
        try:
            container.stop()
            container.remove()
        except Exception as e:
            logger.error(f"Error removing container: {e}")
    
    # Remove data
    redis_client.delete(f"project:{auth.project_id}")
    redis_client.srem(f"user:{project['username']}:projects", auth.project_id)
    
    logger.info(f"Deleted project: {auth.project_id}")
    
    return {"message": "Project deleted successfully"}

# =============================================================================
# Startup
# =============================================================================

@app.on_event("startup")
async def startup():
    logger.info("Vibe Coding Central API started")
    logger.info(f"Port: {API_PORT}")
    logger.info(f"Projects dir: {PROJECTS_DIR}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, log_level="info")
