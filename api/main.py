"""
InfraIQ Demo - Session Management API

Handles email capture and Docker container lifecycle for demo sessions.
"""

import asyncio
import hashlib
import os
import secrets
import subprocess
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from tinydb import Query, TinyDB

# Configuration
SESSION_DURATION_MINUTES = 15
MAX_CONCURRENT_SESSIONS = 10
TTYD_BASE_PORT = 7700
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DEMO_IMAGE = os.environ.get("DEMO_IMAGE", "autonops/infraiq-demo:latest")

# Initialize
app = FastAPI(title="InfraIQ Demo API")
db = TinyDB(f"{DATA_DIR}/demo.json")
sessions_table = db.table("sessions")
leads_table = db.table("leads")


class SessionRequest(BaseModel):
    email: EmailStr


class Session(BaseModel):
    id: str
    email: str
    container_id: Optional[str]
    port: int
    created_at: str
    expires_at: str
    active: bool


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return secrets.token_urlsafe(16)


def get_available_port() -> Optional[int]:
    """Find an available port for ttyd."""
    Session = Query()
    active_sessions = sessions_table.search(Session.active == True)
    used_ports = {s["port"] for s in active_sessions}
    
    for port in range(TTYD_BASE_PORT, TTYD_BASE_PORT + MAX_CONCURRENT_SESSIONS):
        if port not in used_ports:
            return port
    return None


async def start_demo_container(session_id: str, port: int) -> str:
    """Start a Docker container with ttyd for the demo session."""
    container_name = f"demo-{session_id[:8]}"
    
    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--rm",
        "-p", f"{port}:7681",
        "--memory", "512m",
        "--cpus", "0.5",
        "-e", f"SESSION_ID={session_id}",
        DEMO_IMAGE
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"Failed to start container: {result.stderr}")
    
    container_id = result.stdout.strip()
    return container_id


async def stop_demo_container(container_id: str):
    """Stop and remove a demo container."""
    try:
        subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            timeout=10
        )
    except Exception as e:
        print(f"Error stopping container {container_id}: {e}")


async def cleanup_expired_sessions():
    """Clean up expired sessions."""
    Session = Query()
    now = datetime.utcnow().isoformat()
    
    expired = sessions_table.search(
        (Session.active == True) & (Session.expires_at < now)
    )
    
    for session in expired:
        if session.get("container_id"):
            await stop_demo_container(session["container_id"])
        sessions_table.update({"active": False}, Query().id == session["id"])
    
    return len(expired)


@app.on_event("startup")
async def startup_event():
    """Start background cleanup task."""
    asyncio.create_task(cleanup_loop())


async def cleanup_loop():
    """Periodically clean up expired sessions."""
    while True:
        try:
            cleaned = await cleanup_expired_sessions()
            if cleaned > 0:
                print(f"Cleaned up {cleaned} expired sessions")
        except Exception as e:
            print(f"Cleanup error: {e}")
        await asyncio.sleep(60)  # Check every minute


@app.post("/api/session")
async def create_session(request: SessionRequest):
    """Create a new demo session."""
    email = request.email.lower().strip()
    
    # Clean up expired sessions first
    await cleanup_expired_sessions()
    
    # Check for available port
    port = get_available_port()
    if port is None:
        raise HTTPException(
            status_code=503,
            detail="All demo slots are currently in use. Please try again in a few minutes."
        )
    
    # Record lead
    leads_table.insert({
        "email": email,
        "timestamp": datetime.utcnow().isoformat(),
        "ip": None,  # Could capture from request if needed
    })
    
    # Create session
    session_id = generate_session_id()
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=SESSION_DURATION_MINUTES)
    
    try:
        container_id = await start_demo_container(session_id, port)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    session = {
        "id": session_id,
        "email": email,
        "container_id": container_id,
        "port": port,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "active": True,
    }
    
    sessions_table.insert(session)
    
    # Wait a moment for ttyd to start
    await asyncio.sleep(2)
    
    return {
        "session_id": session_id,
        "session_url": f"/terminal/{session_id}",
        "expires_in_minutes": SESSION_DURATION_MINUTES,
    }


@app.get("/terminal/{session_id}")
async def terminal_redirect(session_id: str):
    """Redirect to the ttyd terminal for a session."""
    Session = Query()
    session = sessions_table.get(Session.id == session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session["active"]:
        raise HTTPException(status_code=410, detail="Session has expired")
    
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        await cleanup_expired_sessions()
        raise HTTPException(status_code=410, detail="Session has expired")
    
    # Redirect to ttyd via Caddy proxy path
    return RedirectResponse(url=f"/t/{session['port']}")
    


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session status."""
    Session = Query()
    session = sessions_table.get(Session.id == session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    now = datetime.utcnow()
    expires_at = datetime.fromisoformat(session["expires_at"])
    remaining = max(0, int((expires_at - now).total_seconds()))
    
    return {
        "session_id": session_id,
        "active": session["active"] and expires_at > now,
        "remaining_seconds": remaining,
    }


@app.delete("/api/session/{session_id}")
async def end_session(session_id: str):
    """End a session early."""
    Session = Query()
    session = sessions_table.get(Session.id == session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.get("container_id"):
        await stop_demo_container(session["container_id"])
    
    sessions_table.update({"active": False}, Query().id == session_id)
    
    return {"status": "ended"}


@app.get("/api/leads")
async def get_leads(secret: str):
    """Export captured leads (requires secret key)."""
    if secret != os.environ.get("ADMIN_SECRET", ""):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return {"leads": leads_table.all()}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    Session = Query()
    active_count = len(sessions_table.search(Session.active == True))
    
    return {
        "status": "healthy",
        "active_sessions": active_count,
        "max_sessions": MAX_CONCURRENT_SESSIONS,
    }


# Serve static files (landing page)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
