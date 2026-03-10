# Made with love by Harsh Mistry (OpenSoure Weekend)
"""
OSW Email Tracker — Tracking Server
====================================
A minimal FastAPI server to track email opens.
It listens for hits on /t/{tracking_id}, serves a 1x1 GIF,
and logs the event with the recipient details.

Usage:
    pip install fastapi uvicorn
    python tracker_server.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import FileResponse
    import uvicorn
except ImportError:
    print("Error: FastAPI or Uvicorn not found.")
    print("Please run: pip install fastapi uvicorn")
    exit(1)

from osw_mailer.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_dir / "tracking_events.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tracker")

app = FastAPI(title="OSW Email Tracker")

# 1x1 Transparent GIF
PIXEL_DATA = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

@app.get("/")
async def root():
    return {"status": "tracker active", "logs": str(settings.log_dir / "tracking_events.log")}

@app.get("/t/{tracking_id}")
async def track_open(tracking_id: str, request: Request):
    """Serve a 1x1 pixel and log the open event."""
    
    # Try to load the recipient info
    mapping_path = settings.log_dir / "tracking_map.json"
    recipient_info = {}
    
    if mapping_path.exists():
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
                recipient_info = mapping.get(tracking_id, {})
        except Exception as e:
            logger.error(f"Failed to load tracking map: {e}")

    email = recipient_info.get("email", "unknown")
    name = recipient_info.get("name", "unknown")
    company = recipient_info.get("company_name", "unknown")
    
    # Log the event
    user_agent = request.headers.get("user-agent", "unknown")
    client_host = request.client.host if request.client else "unknown"
    
    log_msg = f"OPENED: {email} ({name} at {company}) | IP: {client_host} | UA: {user_agent}"
    logger.info(log_msg)
    
    # Append to a structured CSV for easier analysis later
    events_csv = settings.log_dir / "tracking_stats.csv"
    if not events_csv.exists():
        with open(events_csv, "w", encoding="utf-8") as f:
            f.write("timestamp,email,name,company,ip,user_agent\n")
            
    with open(events_csv, "a", encoding="utf-8") as f:
        ts = datetime.now().isoformat()
        f.write(f'"{ts}","{email}","{name}","{company}","{client_host}","{user_agent}"\n')

    return Response(content=PIXEL_DATA, media_type="image/gif")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
