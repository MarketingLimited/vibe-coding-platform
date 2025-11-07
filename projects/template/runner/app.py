#!/usr/bin/env python3
"""
Vibe Coding Platform - Exec API
Secure command execution API with advanced security features
"""

import os, re, time, shlex, psutil, subprocess, tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import logging

# Configuration
API_KEY = os.getenv("API_KEY", "")
MAX_SECONDS = int(os.getenv("EXEC_TIMEOUT_SECONDS", "90"))
MAX_OUTPUT_BYTES = int(os.getenv("EXEC_MAX_OUTPUT", str(5 * 1024 * 1024)))
WORKSPACE = os.getenv("WORKSPACE", "/workspace")

ALLOWLIST_STR = os.getenv("EXEC_ALLOWLIST", "")
ALLOWLIST = set(c.strip() for c in ALLOWLIST_STR.split(",") if c.strip()) if ALLOWLIST_STR else None

RATE_LIMIT = int(os.getenv("EXEC_RATE_LIMIT", "100"))
rate_limit_store: Dict[str, List[float]] = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Vibe Coding Exec API", version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Models
class ExecRequest(BaseModel):
    cmd: str = Field(..., min_length=1, max_length=10000)
    cwd: Optional[str] = Field(None, max_length=500)
    timeout: Optional[int] = Field(None, ge=1, le=MAX_SECONDS)
    
    @validator('cmd')
    def validate_cmd(cls, v):
        dangerous = [r'rm\s+-rf\s+/', r':\(\)\s*\{', r'dd\s+if=', r'mkfs\.', r'format\s+', r'>\s*/dev/sd']
        for pattern in dangerous:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Dangerous pattern: {pattern}")
        return v

class ExecResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    truncated: bool = False
    timed_out: bool = False

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    workspace: str
    system: Dict[str, Any]

# Security
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if API_KEY and (not x_api_key or x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")

async def rate_limit_check(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] if current_time - t < 60]
    else:
        rate_limit_store[client_ip] = []
    
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    rate_limit_store[client_ip].append(current_time)

def check_allowlist(cmd: str):
    if not ALLOWLIST:
        return
    parts = shlex.split(cmd, posix=True)
    if parts:
        program = os.path.basename(parts[0])
        if program not in ALLOWLIST:
            raise HTTPException(status_code=403, detail=f"Command '{program}' not allowed")

def within_workspace(path: str) -> bool:
    try:
        return os.path.realpath(path).startswith(os.path.realpath(WORKSPACE))
    except:
        return False

# Endpoints
@app.get("/")
async def root():
    return {"name": "Vibe Coding Exec API", "version": "2.0.0", "docs": "/docs"}

@app.get("/health", response_model=HealthResponse)
async def health():
    start_time = getattr(app.state, 'start_time', time.time())
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(WORKSPACE)
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=round(time.time() - start_time, 2),
        workspace=WORKSPACE,
        system={
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
        }
    )

@app.post("/exec", response_model=ExecResponse)
async def exec_command(req: ExecRequest, x_api_key: Optional[str] = Header(None), request: Request = None):
    await verify_api_key(x_api_key)
    await rate_limit_check(request)
    check_allowlist(req.cmd)
    
    cwd = req.cwd or WORKSPACE
    if not within_workspace(cwd):
        raise HTTPException(status_code=400, detail="cwd must be in workspace")
    os.makedirs(cwd, exist_ok=True)
    
    timeout = req.timeout or MAX_SECONDS
    start_time = time.time()
    
    with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
        proc = subprocess.Popen(
            ["bash", "-lc", req.cmd],
            cwd=cwd,
            stdout=stdout_f,
            stderr=stderr_f,
            preexec_fn=os.setsid,
            env=os.environ.copy()
        )
        
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except:
                        pass
                parent.kill()
            except:
                pass
            raise HTTPException(status_code=408, detail=f"Timeout after {timeout}s")
        
        elapsed = time.time() - start_time
        stdout_f.seek(0)
        stderr_f.seek(0)
        
        stdout_data = stdout_f.read(MAX_OUTPUT_BYTES + 1)
        stderr_data = stderr_f.read(MAX_OUTPUT_BYTES + 1)
        
        truncated = len(stdout_data) > MAX_OUTPUT_BYTES or len(stderr_data) > MAX_OUTPUT_BYTES
        
        return ExecResponse(
            returncode=proc.returncode,
            stdout=stdout_data[:MAX_OUTPUT_BYTES].decode('utf-8', errors='replace'),
            stderr=stderr_data[:MAX_OUTPUT_BYTES].decode('utf-8', errors='replace'),
            elapsed_seconds=round(elapsed, 3),
            truncated=truncated
        )

@app.on_event("startup")
async def startup():
    app.state.start_time = time.time()
    logger.info("Vibe Coding Exec API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")
