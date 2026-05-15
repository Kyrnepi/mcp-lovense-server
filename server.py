"""
Lovense MCP Server
MCP-compliant server for controlling Lovense toys via Game Mode.

Supports both stdio and Streamable HTTP transports as defined by the
MCP specification (2025-11-25).
"""

import hmac
import json
import logging
import os
import re
import warnings
from typing import Annotated, Any, Literal, Optional

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("lovense-mcp-server")

# Lovense uses self-signed certificates – suppress the per-request warning
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


# ---------------------------------------------------------------------------
# Lovense API layer
# ---------------------------------------------------------------------------


class LovenseConfig:
    """Configuration for Lovense API connection"""

    def __init__(self):
        self.game_mode_ip = os.getenv("GAME_MODE_IP")
        self.game_mode_port = os.getenv("GAME_MODE_PORT", "30010")
        self.auth_token = os.getenv("MCP_AUTH_TOKEN")

        if not self.game_mode_ip:
            raise ValueError("GAME_MODE_IP environment variable is required")

        self.domain_url = self._convert_ip_to_domain()
        logger.info(f"Lovense API configured: {self.domain_url}")
        if self.auth_token:
            logger.info("Authentication enabled")

    def _convert_ip_to_domain(self) -> str:
        """Convert local IP to Lovense domain format"""
        ip = self.game_mode_ip.strip()

        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
            raise ValueError(f"Invalid IP format: {ip}")

        for part in ip.split("."):
            if not 0 <= int(part) <= 255:
                raise ValueError(f"Invalid IP range: {ip}")

        return f"https://{ip.replace('.', '-')}.lovense.club:{self.game_mode_port}"


class LovenseAPIClient:
    """Async client for Lovense Game Mode API"""

    def __init__(self, config: LovenseConfig):
        self.config = config
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            verify=False,  # Lovense uses self-signed certificates
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()

    async def send_command(
        self, command: str, action: str, time_sec: int, toy: str = ""
    ) -> dict[str, Any]:
        url = f"{self.config.domain_url}/command"
        data = {
            "command": command,
            "action": action,
            "timeSec": time_sec,
            "toy": toy,
            "apiVer": 1,
        }
        try:
            response = await self.http_client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Command sent successfully: {command} - {action}")
            return {"success": True, "data": result}
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    async def vibrate(
        self, intensity: int, duration: int, toy: str = ""
    ) -> dict[str, Any]:
        if not 0 <= intensity <= 20:
            return {"success": False, "error": "Intensity must be between 0 and 20"}
        if not 1 <= duration <= 60:
            return {
                "success": False,
                "error": "Duration must be between 1 and 60 seconds",
            }
        return await self.send_command("Function", f"Vibrate:{intensity}", duration, toy)

    async def rotate(
        self, intensity: int, duration: int, toy: str = ""
    ) -> dict[str, Any]:
        if not 0 <= intensity <= 20:
            return {"success": False, "error": "Intensity must be between 0 and 20"}
        if not 1 <= duration <= 60:
            return {
                "success": False,
                "error": "Duration must be between 1 and 60 seconds",
            }
        return await self.send_command("Function", f"Rotate:{intensity}", duration, toy)

    async def pump(
        self, intensity: int, duration: int, toy: str = ""
    ) -> dict[str, Any]:
        if not 0 <= intensity <= 3:
            return {"success": False, "error": "Intensity must be between 0 and 3"}
        if not 1 <= duration <= 60:
            return {
                "success": False,
                "error": "Duration must be between 1 and 60 seconds",
            }
        return await self.send_command("Function", f"Pump:{intensity}", duration, toy)

    async def stop(self, toy: str = "") -> dict[str, Any]:
        return await self.send_command("Function", "Stop", 0, toy)

    async def get_toys(self) -> dict[str, Any]:
        url = f"{self.config.domain_url}/GetToys"
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            logger.error(f"Failed to get toys: {e}")
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Global state – initialised at startup
# ---------------------------------------------------------------------------

config: Optional[LovenseConfig] = None
api_client: Optional[LovenseAPIClient] = None


def _require_client() -> LovenseAPIClient:
    """Return the initialised API client or raise a clear error."""
    if api_client is None or api_client.http_client is None:
        raise RuntimeError(
            "Lovense API client is not initialised. "
            "Make sure GAME_MODE_IP is set and the server was started correctly."
        )
    return api_client


# ---------------------------------------------------------------------------
# MCP Server (FastMCP) – protocol version 2025-11-25
# ---------------------------------------------------------------------------

# Build the list of allowed hosts for DNS-rebinding protection.
# Always allow localhost; add the external hostname if configured.
_allowed_hosts = ["localhost", "127.0.0.1"]
_external_host = os.getenv("EXTERNAL_HOST", "")
if _external_host:
    _allowed_hosts.append(_external_host)

mcp = FastMCP(
    "lovense-mcp-server",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts,
    ),
)


# ---- Tools ----------------------------------------------------------------


def _check_result(result: dict[str, Any], tool_name: str) -> str:
    """Return success text or raise on failure (-> isError=true in MCP)."""
    if result["success"]:
        return (
            f"Success: Command '{tool_name}' executed. "
            f"Response: {result.get('data', {})}"
        )
    raise Exception(
        f"Failed to execute '{tool_name}': {result.get('error', 'Unknown error')}"
    )


@mcp.tool(
    description=(
        "Send vibration command to Lovense toy. "
        "Controls vibration intensity and duration."
    )
)
async def vibrate(
    intensity: Annotated[
        int,
        Field(
            description="Vibration intensity level (0-20, where 0 is off and 20 is maximum)",
            ge=0,
            le=20,
        ),
    ] = 10,
    duration: Annotated[
        int,
        Field(description="Duration in seconds (1-60)", ge=1, le=60),
    ] = 5,
    toy: Annotated[
        str,
        Field(description="Toy ID to control (empty string for all connected toys)"),
    ] = "",
) -> str:
    client = _require_client()
    result = await client.vibrate(intensity, duration, toy)
    return _check_result(result, "vibrate")


@mcp.tool(
    description=(
        "Send rotation command to Lovense toy with rotation capability. "
        "Controls rotation speed and duration."
    )
)
async def rotate(
    intensity: Annotated[
        int,
        Field(description="Rotation intensity level (0-20)", ge=0, le=20),
    ] = 10,
    duration: Annotated[
        int,
        Field(description="Duration in seconds (1-60)", ge=1, le=60),
    ] = 5,
    toy: Annotated[
        str,
        Field(description="Toy ID to control (empty string for all connected toys)"),
    ] = "",
) -> str:
    client = _require_client()
    result = await client.rotate(intensity, duration, toy)
    return _check_result(result, "rotate")


@mcp.tool(
    description=(
        "Send pump command to Lovense toy with pump capability. "
        "Controls pump intensity and duration."
    )
)
async def pump(
    intensity: Annotated[
        int,
        Field(description="Pump intensity level (0-3)", ge=0, le=3),
    ] = 2,
    duration: Annotated[
        int,
        Field(description="Duration in seconds (1-60)", ge=1, le=60),
    ] = 5,
    toy: Annotated[
        str,
        Field(description="Toy ID to control (empty string for all connected toys)"),
    ] = "",
) -> str:
    client = _require_client()
    result = await client.pump(intensity, duration, toy)
    return _check_result(result, "pump")


@mcp.tool(
    description=(
        "Immediately stop all running functions on Lovense toy(s). "
        "Emergency stop command."
    )
)
async def stop(
    toy: Annotated[
        str,
        Field(description="Toy ID to stop (empty string for all connected toys)"),
    ] = "",
) -> str:
    client = _require_client()
    result = await client.stop(toy)
    return _check_result(result, "stop")


PATTERN_MAP = {
    "pulse": "Preset:1",
    "wave": "Preset:2",
    "fireworks": "Preset:3",
    "earthquake": "Preset:4",
}


@mcp.tool(
    description=(
        "Send a preset vibration pattern to Lovense toy. "
        "Use predefined patterns for varied experiences."
    )
)
async def pattern(
    pattern_name: Annotated[
        Literal["pulse", "wave", "fireworks", "earthquake"],
        Field(
            description=(
                "Pattern name: 'pulse' (rhythmic pulses), 'wave' (gradual waves), "
                "'fireworks' (random bursts), 'earthquake' (intense vibrations)"
            ),
        ),
    ] = "pulse",
    duration: Annotated[
        int,
        Field(description="Duration in seconds (1-60)", ge=1, le=60),
    ] = 10,
    toy: Annotated[
        str,
        Field(description="Toy ID to control (empty string for all connected toys)"),
    ] = "",
) -> str:
    client = _require_client()
    action = PATTERN_MAP[pattern_name]
    result = await client.send_command("Function", action, duration, toy)
    return _check_result(result, f"pattern({pattern_name})")


# ---- Resources ------------------------------------------------------------


@mcp.resource(
    "lovense://toys/connected",
    name="Connected Toys",
    description="List of currently connected Lovense toys and their status",
    mime_type="application/json",
)
async def connected_toys() -> str:
    client = _require_client()
    result = await client.get_toys()
    if result["success"]:
        return json.dumps(result["data"], indent=2)
    return json.dumps(
        {"error": result.get("error", "Failed to get toys")}, indent=2
    )


@mcp.resource(
    "lovense://config/api",
    name="API Configuration",
    description="Current Lovense API configuration and connection details",
    mime_type="application/json",
)
async def api_configuration() -> str:
    if config is None:
        return json.dumps({"error": "Server not configured"}, indent=2)
    return json.dumps(
        {
            "domain_url": config.domain_url,
            "game_mode_ip": config.game_mode_ip,
            "game_mode_port": config.game_mode_port,
            "status": "connected",
        },
        indent=2,
    )


# ---- Prompts --------------------------------------------------------------


@mcp.prompt(
    description="Interactive prompt for controlling Lovense toys with guided parameters"
)
def control_toy(
    action: str, intensity: str = "10", duration: str = "5"
) -> str:
    return (
        f"I want to control the Lovense toy with the following parameters:\n\n"
        f"Action: {action}\n"
        f"Intensity: {intensity}\n"
        f"Duration: {duration} seconds\n\n"
        f"Please execute this command using the appropriate tool."
    )


@mcp.prompt(description="Quick vibration with preset intensity and duration")
def quick_vibrate(level: str = "medium") -> str:
    intensity_map = {"low": 5, "medium": 10, "high": 18}
    intensity = intensity_map.get(level, 10)
    return (
        f"Please send a quick vibration command with {level} intensity "
        f"(level {intensity}) for 3 seconds."
    )


@mcp.prompt(description="Play a vibration pattern with specified duration")
def pattern_play(pattern_name: str = "pulse", duration: str = "10") -> str:
    return f"Please play the '{pattern_name}' vibration pattern for {duration} seconds."


# ---------------------------------------------------------------------------
# Streamable HTTP transport with auth & Origin validation
# (MCP spec 2025-11-25 §Transports)
# ---------------------------------------------------------------------------


class AuthOriginMiddleware:
    """ASGI middleware that enforces Bearer-token auth and Origin validation.

    - Skips auth for /health.
    - If MCP_AUTH_TOKEN is unset, auth is disabled.
    - If ALLOWED_ORIGINS is unset, Origin checking is disabled.
    - Returns HTTP 403 for invalid Origin (per MCP spec).
    """

    def __init__(self, app):
        self.app = app
        self.auth_token = os.getenv("MCP_AUTH_TOKEN")
        raw_origins = os.getenv("ALLOWED_ORIGINS", "")
        self.allowed_origins = (
            [o.strip() for o in raw_origins.split(",") if o.strip()]
            if raw_origins
            else []
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/health":
            await self.app(scope, receive, send)
            return

        headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}

        # Origin validation (MCP spec: MUST validate to prevent DNS rebinding)
        origin = headers.get("origin", "")
        if origin and self.allowed_origins and origin not in self.allowed_origins:
            resp = Response("Forbidden: invalid origin", status_code=403)
            await resp(scope, receive, send)
            return

        # Bearer token auth
        if self.auth_token:
            auth_header = headers.get("authorization", "")
            token = (
                auth_header.removeprefix("Bearer ").strip() if auth_header else ""
            )
            if not hmac.compare_digest(token, self.auth_token):
                resp = Response("Unauthorized", status_code=401)
                await resp(scope, receive, send)
                return

        await self.app(scope, receive, send)


def create_streamable_http_app():
    """Build an ASGI app that serves MCP over Streamable HTTP transport.

    Uses FastMCP's built-in streamable_http_app which provides a single
    MCP endpoint supporting POST (client messages) and GET (server SSE stream),
    with session management via MCP-Session-Id headers.

    A /health endpoint and auth/origin middleware are layered on top.
    """
    from contextlib import asynccontextmanager

    from starlette.applications import Starlette
    from starlette.routing import Mount

    async def health(request: Request):
        return JSONResponse(
            {
                "status": "healthy",
                "server": "lovense-mcp-server",
                "version": "2.0.0",
                "domain_configured": bool(config and config.domain_url),
            }
        )

    # FastMCP provides the complete Streamable HTTP ASGI app
    # (single endpoint with POST + GET + DELETE, session management, etc.)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/health", endpoint=health),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )

    return AuthOriginMiddleware(app)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    transport = os.getenv("MCP_TRANSPORT", "streamable-http")

    # Initialize Lovense connection
    config = LovenseConfig()
    api_client = LovenseAPIClient(config)

    if transport == "stdio":
        # stdio transport – launched as a subprocess by the MCP client
        async def run_stdio():
            async with api_client:
                await mcp.run_stdio_async()

        asyncio.run(run_stdio())
    else:
        # Streamable HTTP transport – standalone server (MCP spec 2025-11-25)
        async def run_http():
            async with api_client:
                host = os.getenv("HOST", "127.0.0.1")
                port = int(os.getenv("PORT", "8000"))
                app = create_streamable_http_app()
                server_config = uvicorn.Config(
                    app, host=host, port=port, log_level="info"
                )
                server = uvicorn.Server(server_config)
                await server.serve()

        asyncio.run(run_http())
