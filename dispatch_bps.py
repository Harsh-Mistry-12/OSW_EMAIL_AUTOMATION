# Made with love by Harsh Mistry (OpenSoure Weekend)
"""
Dedicated Dispatcher for Best Practices Summit 2026
===================================================
Uses the static template 'best_practices_summit.html' and 'bps_dispatch.csv'.
"""

import asyncio
import uuid
import json
import pandas as pd
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import aiosmtplib
from rich.console import Console
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    MofNCompleteColumn, 
    TaskProgressColumn, 
    TimeElapsedColumn
)

from osw_mailer.config import settings
from osw_mailer.logger import get_logger

console = Console()
log = get_logger("bps_dispatch")

TEMPLATE_PATH = Path("osw_mailer/templates/best_practices_summit.html")
CSV_PATH = Path("bps_dispatch.csv")
SUBJECT = "Best Practices Summit 2026 — Official Invitation"

async def send_email(email, html_content, tracking_id):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    # Using the sender details from .env settings
    msg["From"] = formataddr((settings.sender_name, settings.sender_email))
    msg["To"] = email
    msg["Reply-To"] = settings.sender_email
    
    # Add tracking pixel (consistent with existing infra)
    tracking_url = f"{settings.tracking_base_url}/t/{tracking_id}"
    pixel_tag = (
        f'\n<img src="{tracking_url}" width="1" height="1" '
        'style="display:none !important; visibility:hidden; opacity:0;" alt="" />'
    )
    full_html = html_content + pixel_tag
    
    msg.attach(MIMEText(full_html, "html", "utf-8"))
    
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        start_tls=True,
        timeout=30,
    )

async def dispatch_all():
    if not CSV_PATH.exists():
        console.print(f"[bold red]Error:[/] {CSV_PATH} not found.")
        return

    # Read CSV (header is assumed to be 'email')
    try:
        df = pd.read_csv(CSV_PATH)
        # Normalize column names just in case
        df.columns = [c.strip().lower() for c in df.columns]
        if 'email' not in df.columns:
            console.print(f"[bold red]Error:[/] CSV must have an 'email' column. Found: {list(df.columns)}")
            return
        emails = df['email'].dropna().unique().tolist()
    except Exception as e:
        console.print(f"[bold red]Error reading CSV:[/] {e}")
        return
    
    if not emails:
        console.print("[bold yellow]No valid emails found in CSV.[/]")
        return
        
    if not TEMPLATE_PATH.exists():
        console.print(f"[bold red]Error:[/] Template {TEMPLATE_PATH} not found.")
        return
        
    html_content = TEMPLATE_PATH.read_text(encoding="utf-8")
    
    console.rule("[bold magenta]✦  BPS 2026 Dispatch  ✦[/bold magenta]")
    console.print(f"[bold cyan]Target:[/] {len(emails)} recipients")
    console.print(f"[bold cyan]Template:[/] {TEMPLATE_PATH.name}")
    console.print(f"[bold cyan]Sender:[/] {settings.sender_formatted}")
    print()

    tracking_map = {}
    sem = asyncio.Semaphore(settings.max_concurrent_sends)
    
    async def send_task(email, progress, task_id):
        async with sem:
            tracking_id = uuid.uuid4().hex
            # Store in the map so tracker_server knows who opened it
            tracking_map[tracking_id] = {
                "email": email, 
                "name": "Respected Sir/Madam",
                "template": "best_practices_summit",
                "company_name": "N/A"
            }
            try:
                await send_email(email, html_content, tracking_id)
                log.info("✓ Sent → %s", email)
            except Exception as e:
                log.error("✗ Failed → %s: %s", email, e)
            finally:
                progress.advance(task_id)
                # Respect the configured delay to avoid rate limiting
                await asyncio.sleep(settings.send_delay_seconds)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task("Dispatching Emails...", total=len(emails))
        await asyncio.gather(*[send_task(email, progress, task_id) for email in emails])
    
    # Save the tracking map to logs (consistent with tracker_server expectations)
    tracking_map_path = settings.log_dir / "tracking_map.json"
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    
    # Merge with existing map if it exists
    existing_map = {}
    if tracking_map_path.exists():
        try:
            with open(tracking_map_path, "r", encoding="utf-8") as f:
                existing_map = json.load(f)
        except:
            pass
    
    existing_map.update(tracking_map)
    
    with open(tracking_map_path, "w", encoding="utf-8") as f:
        json.dump(existing_map, f, indent=4)
        
    console.print(f"\n[bold green]✓ Success:[/] Finished dispatching to {len(emails)} contacts.")
    console.print(f"[dim]Tracking mapping updated at {tracking_map_path}[/dim]")

if __name__ == "__main__":
    asyncio.run(dispatch_all())
