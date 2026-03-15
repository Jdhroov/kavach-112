"""
server.py — Web server for KAVACH 112 Operator Panel.

Serves the panel UI and issues LiveKit access tokens for the browser.

Run: python3 server.py        → opens at http://localhost:3000
     python3 agent.py dev     → (separate terminal) connects agent to LiveKit

When the browser joins room "kavach-112", LiveKit dispatches the agent to
that same room automatically.
"""

import os
from aiohttp import web
from livekit.api import AccessToken, VideoGrants
from dotenv import load_dotenv

load_dotenv()

LIVEKIT_URL    = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY    = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
ROOM_NAME = "kavach-112"


async def handle_token(request: web.Request) -> web.Response:
    """
    Issue a short-lived LiveKit JWT for the operator panel browser client.
    The token grants join + publish + subscribe + data for ROOM_NAME.
    """
    identity = request.rel_url.query.get("identity", "operator-panel")

    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("Operator Panel")
        .with_grants(VideoGrants(
            room_join=True,
            room=ROOM_NAME,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
    )

    return web.json_response({
        "token": token.to_jwt(),
        "url": LIVEKIT_URL,
        "room": ROOM_NAME,
    })


async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse("panel/index.html")


app = web.Application()
app.router.add_get("/", handle_index)
app.router.add_get("/token", handle_token)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"\n  KAVACH Operator Panel → http://localhost:{port}\n")
    print("  Also start the agent in a separate terminal:")
    print("    source .venv/bin/activate && python3 agent.py dev\n")
    web.run_app(app, host="0.0.0.0", port=port, print=None)
