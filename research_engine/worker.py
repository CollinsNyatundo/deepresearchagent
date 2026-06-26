# ==========================================
# MANDATORY INTEGRITY WARNING
# DO NOT CHEAT. All implementations must be genuine.
# - DO NOT hardcode test results, expected outputs, or verification strings.
# - DO NOT create dummy or facade implementations.
# - Every implementation must maintain real state and produce real behavior.
# ==========================================

import hashlib
import hmac
import json
import logging
import os
import time
import uuid

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Deep Research Agent Scraper Worker", version="0.1.0")

class WebhookTriggerRequest(BaseModel):
    query: str
    run_id: str
    workspace_id: str
    depth: int = 1
    model: str | None = None
    provider: str | None = None
    timestamp: int | None = None

# Default HMAC secret
DEFAULT_HMAC_SECRET = "test-webhook-hmac-shared-secret-key"

def get_webhook_secret() -> str:
    return os.environ.get("WEBHOOK_HMAC_SECRET", DEFAULT_HMAC_SECRET)

async def run_scraper_task(payload: dict):
    # This simulates starting the research/scraping job
    logger.info(f"Worker starting research job: {payload}")
    try:
        from research_engine.agent.orchestrator import DeepResearchOrchestrator
        from research_engine.config import get_config
        from research_engine.models import ResearchRequest

        config = get_config()
        orchestrator = DeepResearchOrchestrator(config)

        # Prepare request
        req = ResearchRequest(
            query=payload["query"],
            depth=payload.get("depth", 1),
            model=payload.get("model"),
            provider=payload.get("provider"),
            workspace_id=payload["workspace_id"]
        )

        # We run the orchestrator (it will write updates to the database and emit realtime broadcasts)
        await orchestrator.run(req, run_id=payload["run_id"])

    except Exception as e:
        logger.error(f"Background worker execution failed: {e}")

@app.post("/webhook/trigger")
async def trigger_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature")
):
    body = await request.body()

    # 1. Check for missing signature header
    if not x_webhook_signature:
        raise HTTPException(status_code=400, detail="Missing X-Webhook-Signature header")

    # 2. Check for empty body
    if not body or len(body.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty body")

    # 3. Verify HMAC signature
    secret = get_webhook_secret()
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, x_webhook_signature):
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")

    # 4. Validate JSON payload
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")

    # 5. Check for expired timestamp
    timestamp = payload.get("timestamp")
    if timestamp is not None:
        try:
            ts = int(timestamp)
            now = int(time.time())
            # Signature older than 5 minutes is rejected
            if abs(now - ts) > 300:
                raise HTTPException(status_code=403, detail="Signature timestamp expired")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format")

    # Verify required payload fields
    if "query" not in payload or "run_id" not in payload or "workspace_id" not in payload:
        raise HTTPException(status_code=400, detail="Missing required fields (query, run_id, workspace_id)")

    task_id = str(uuid.uuid4())

    # Add background task
    background_tasks.add_task(run_scraper_task, payload)

    return {
        "task_id": task_id,
        "status": "triggered",
        "message": "Scraping worker triggered successfully"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "worker": True}
