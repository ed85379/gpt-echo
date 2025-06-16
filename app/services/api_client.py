import httpx
from datetime import datetime, timezone

async def log_message_to_api(text, role="muse", source="frontend", timestamp=None, api_url="http://localhost:5000/api/messages/log"):
    payload = {
        "message": text,
        "role": role,
        "timestamp": timestamp,
        "source": source
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json=payload)
        resp.raise_for_status()
        return resp.json()  # Optionally return status/message_id/etc

# Usage in an async context:
# await log_message_to_api("This is my log text.", source="continuity_engine")