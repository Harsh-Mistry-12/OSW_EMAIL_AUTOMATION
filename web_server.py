# Made with love by Harsh Mistry (OpenSoure Weekend)
import json
import logging
import os
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from jinja2 import Environment, FileSystemLoader, select_autoescape

from osw_mailer.config import settings
from osw_mailer.models import load_recipients, Recipient
from osw_mailer.renderer import _bullets_to_html

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_dir / "web_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_server")

app = FastAPI(title="OSW Email Automation Dashboard")

# Constants
UPLOAD_DIR = Path("automation_data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR = Path("osw_mailer/templates")
PIXEL_DATA = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

# Jinja2 for preview
preview_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)

# --- Tracking Logic (Merged from tracker_server.py) ---

@app.get("/t/{tracking_id}")
async def track_open(tracking_id: str, request: Request):
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
    
    user_agent = request.headers.get("user-agent", "unknown")
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"OPENED: {email} ({name} at {company}) | IP: {client_host}")
    
    events_csv = settings.log_dir / "tracking_stats.csv"
    if not events_csv.exists():
        with open(events_csv, "w", encoding="utf-8") as f:
            f.write("timestamp,email,name,company,ip,user_agent\n")
            
    with open(events_csv, "a", encoding="utf-8") as f:
        ts = datetime.now().isoformat()
        f.write(f'"{ts}","{email}","{name}","{company}","{client_host}","{user_agent}"\n')

    return Response(content=PIXEL_DATA, media_type="image/gif")

# --- API Endpoints ---

@app.get("/api/sample-csv")
async def get_sample_csv():
    sample_path = Path("sample_recipients.csv")
    if sample_path.exists():
        return FileResponse(sample_path, media_type="text/csv", filename="sample_recipients.csv")
    return JSONResponse({"error": "Sample CSV not found"}, status_code=404)

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    try:
        df = pd.read_csv(file_path)
        preview = df.head(10).to_dict(orient="records")
        columns = list(df.columns)
        return {"filename": file.filename, "columns": columns, "preview": preview}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/api/templates")
async def list_templates():
    templates = [f.name for f in TEMPLATE_DIR.glob("*.html")]
    return {"templates": templates}

@app.get("/api/template/{name}")
async def get_template_content(name: str):
    file_path = TEMPLATE_DIR / name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    content = file_path.read_text(encoding="utf-8")
    # Identify dynamic parts
    placeholders = list(set(re.findall(r"\{\{\s*(\w+)\s*\}\}", content)))
    return {"content": content, "placeholders": placeholders}

@app.post("/api/save-template")
async def save_template(name: str = Form(...), content: str = Form(...)):
    if not name.endswith(".html"):
        name += ".html"
    file_path = TEMPLATE_DIR / name
    try:
        file_path.write_text(content, encoding="utf-8")
        return {"status": "success", "name": name}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/preview")
async def preview_template(template_content: str = Form(...), data: str = Form(...)):
    try:
        render_data = json.loads(data)
        # We use a temporary env for the content
        from jinja2 import Template
        template = Template(template_content)
        
        # Handle special bullets logic if present
        if "benefit_bullets_html" in template_content and "benefit_bullets" in render_data:
            render_data["benefit_bullets_html"] = _bullets_to_html(render_data["benefit_bullets"])
            
        rendered = template.render(**render_data)
        return {"html": rendered}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --- Frontend ---

# Serve static files (style.css, script.js) at the root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

