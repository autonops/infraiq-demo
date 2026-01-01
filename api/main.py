"""
InfraIQ Demo - Session Management API

Handles email capture and Docker container lifecycle for demo sessions.
"""

import asyncio
import hashlib
import httpx
import os
import secrets
import subprocess
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator
from tinydb import Query, TinyDB

# Blocked email domains (personal/free email providers)
BLOCKED_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "protonmail.com", "zoho.com", "yandex.com",
    "gmx.com", "live.com", "msn.com", "me.com", "inbox.com",
}

# Configuration
SESSION_DURATION_MINUTES = 15
MAX_CONCURRENT_SESSIONS = 10
TTYD_BASE_PORT = 7700
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DEMO_IMAGE = os.environ.get("DEMO_IMAGE", "autonops/infraiq-demo:latest")

# Initialize
app = FastAPI(title="InfraIQ Demo API", debug=True)
db = TinyDB(f"{DATA_DIR}/demo.json")
sessions_table = db.table("sessions")
leads_table = db.table("leads")


class SessionRequest(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def validate_company_email(cls, v):
        domain = v.split('@')[1].lower()
        if domain in BLOCKED_EMAIL_DOMAINS:
            raise ValueError('Please use your company email address')
        return v


async def send_slack_notification(email: str, session_id: str):
    """Send Slack notification for new demo session."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[DEBUG] No SLACK_WEBHOOK_URL configured, skipping notification")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={
                "text": f"🎉 New InfraIQ Demo Session",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*New Demo Session Started*\n\n📧 *Email:* {email}\n🆔 *Session:* `{session_id[:8]}...`\n⏰ *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                        }
                    }
                ]
            })
        print(f"[DEBUG] Slack notification sent for {email}")
    except Exception as e:
        print(f"[DEBUG] Failed to send Slack notification: {e}")


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
    SessionQuery = Query()
    active_sessions = sessions_table.search(SessionQuery.active == True)
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
    
    print(f"[DEBUG] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"[DEBUG] Return code: {result.returncode}")
    print(f"[DEBUG] Stdout: {result.stdout}")
    print(f"[DEBUG] Stderr: {result.stderr}")
    
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
    SessionQuery = Query()
    now = datetime.utcnow().isoformat()
    
    expired = sessions_table.search(
        (SessionQuery.active == True) & (SessionQuery.expires_at < now)
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
    try:
        print(f"[DEBUG] === Creating session for {request.email} ===")
        email = request.email.lower().strip()
        
        # Clean up expired sessions first
        print("[DEBUG] Cleaning up expired sessions...")
        await cleanup_expired_sessions()
        
        # Check for available port
        print("[DEBUG] Getting available port...")
        port = get_available_port()
        print(f"[DEBUG] Got port: {port}")
        if port is None:
            raise HTTPException(
                status_code=503,
                detail="All demo slots are currently in use. Please try again in a few minutes."
            )
        
        # Record lead
        print("[DEBUG] Recording lead...")
        leads_table.insert({
            "email": email,
            "timestamp": datetime.utcnow().isoformat(),
            "ip": None,
        })
        
        # Create session
        session_id = generate_session_id()
        print(f"[DEBUG] Session ID: {session_id}")
        
        # Send Slack notification
        await send_slack_notification(email, session_id)
        
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=SESSION_DURATION_MINUTES)
        
        print("[DEBUG] Starting container...")
        container_id = await start_demo_container(session_id, port)
        print(f"[DEBUG] Container ID: {container_id}")
        
        session = {
            "id": session_id,
            "email": email,
            "container_id": container_id,
            "port": port,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "active": True,
        }
        
        print("[DEBUG] Inserting session...")
        sessions_table.insert(session)
        
        # Wait a moment for ttyd to start
        print("[DEBUG] Waiting for ttyd...")
        await asyncio.sleep(2)
        
        print("[DEBUG] Session created successfully!")
        return {
            "session_id": session_id,
            "session_url": f"/terminal/{session_id}",
            "expires_in_minutes": SESSION_DURATION_MINUTES,
        }
    except HTTPException:
        raise
    except Exception as e:
        print("=" * 50)
        print("SESSION CREATE ERROR:")
        print(traceback.format_exc())
        print("=" * 50)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/terminal/{session_id}")
async def terminal_redirect(session_id: str):
    """Redirect to the ttyd terminal for a session."""
    SessionQuery = Query()
    session = sessions_table.get(SessionQuery.id == session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session["active"]:
        raise HTTPException(status_code=410, detail="Session has expired")
    
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        await cleanup_expired_sessions()
        raise HTTPException(status_code=410, detail="Session has expired")
    
    # Redirect to ttyd via Caddy proxy path
    return RedirectResponse(url=f"/t/{session['port']}/")


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session status."""
    SessionQuery = Query()
    session = sessions_table.get(SessionQuery.id == session_id)
    
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
    SessionQuery = Query()
    session = sessions_table.get(SessionQuery.id == session_id)
    
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
    SessionQuery = Query()
    active_count = len(sessions_table.search(SessionQuery.active == True))
    
    return {
        "status": "healthy",
        "active_sessions": active_count,
        "max_sessions": MAX_CONCURRENT_SESSIONS,
    }


# Serve static files (landing page)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
