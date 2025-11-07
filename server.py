"""
Lovense MCP Server
MCP-compliant HTTP server for controlling Lovense toys via Game Mode
"""

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("lovense-mcp-server")


class LovenseConfig:
    """Configuration for Lovense API connection"""

    def __init__(self):
        self.game_mode_ip = os.getenv("GAME_MODE_IP")
        self.game_mode_port = os.getenv("GAME_MODE_PORT", "30010")
        self.auth_token = os.getenv("MCP_AUTH_TOKEN")

        if not self.game_mode_ip:
            raise ValueError("GAME_MODE_IP environment variable is required")

        if not self.auth_token:
            raise ValueError("MCP_AUTH_TOKEN environment variable is required")

        self.domain_url = self._convert_ip_to_domain()
        logger.info(f"Lovense API configured: {self.domain_url}")
        logger.info("Authentication enabled")

    def _convert_ip_to_domain(self) -> str:
        """Convert local IP to Lovense domain format"""
        ip = self.game_mode_ip.strip()

        # Validate IP format
        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
            raise ValueError(f"Invalid IP format: {ip}")

        # Validate IP range
        for part in ip.split('.'):
            if not 0 <= int(part) <= 255:
                raise ValueError(f"Invalid IP range: {ip}")

        # Convert to Lovense domain format
        domain = f"https://{ip.replace('.', '-')}.lovense.club:{self.game_mode_port}"
        return domain


class LovenseAPIClient:
    """Async client for Lovense Game Mode API"""

    def __init__(self, config: LovenseConfig):
        self.config = config
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Setup async HTTP client"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            verify=False  # Lovense uses self-signed certificates
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async HTTP client"""
        if self.http_client:
            await self.http_client.aclose()

    async def send_command(self, command: str, action: str, time_sec: int, toy: str = "") -> dict[str, Any]:
        """Send command to Lovense API"""
        url = f"{self.config.domain_url}/command"
        data = {
            "command": command,
            "action": action,
            "timeSec": time_sec,
            "toy": toy,
            "apiVer": 1
        }

        try:
            response = await self.http_client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Command sent successfully: {command} - {action}")
            return {"success": True, "data": result}
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def vibrate(self, intensity: int, duration: int, toy: str = "") -> dict[str, Any]:
        """Send vibration command"""
        if not 0 <= intensity <= 20:
            return {"success": False, "error": "Intensity must be between 0 and 20"}
        if not 1 <= duration <= 60:
            return {"success": False, "error": "Duration must be between 1 and 60 seconds"}
        return await self.send_command("Function", f"Vibrate:{intensity}", duration, toy)

    async def rotate(self, intensity: int, duration: int, toy: str = "") -> dict[str, Any]:
        """Send rotation command"""
        if not 0 <= intensity <= 20:
            return {"success": False, "error": "Intensity must be between 0 and 20"}
        if not 1 <= duration <= 60:
            return {"success": False, "error": "Duration must be between 1 and 60 seconds"}
        return await self.send_command("Function", f"Rotate:{intensity}", duration, toy)

    async def pump(self, intensity: int, duration: int, toy: str = "") -> dict[str, Any]:
        """Send pump command"""
        if not 0 <= intensity <= 3:
            return {"success": False, "error": "Intensity must be between 0 and 3"}
        if not 1 <= duration <= 60:
            return {"success": False, "error": "Duration must be between 1 and 60 seconds"}
        return await self.send_command("Function", f"Pump:{intensity}", duration, toy)

    async def stop(self, toy: str = "") -> dict[str, Any]:
        """Stop all toy functions"""
        return await self.send_command("Function", "Stop", 0, toy)

    async def get_toys(self) -> dict[str, Any]:
        """Get list of connected toys"""
        url = f"{self.config.domain_url}/GetToys"
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            result = response.json()
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to get toys: {str(e)}")
            return {"success": False, "error": str(e)}


# Global state
config: Optional[LovenseConfig] = None
api_client: Optional[LovenseAPIClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global config, api_client

    # Startup
    try:
        config = LovenseConfig()
        api_client = LovenseAPIClient(config)
        await api_client.__aenter__()
        logger.info("Server started successfully")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

    yield

    # Shutdown
    if api_client:
        await api_client.__aexit__(None, None, None)
    logger.info("Server shutting down")


# Create FastAPI app
app = FastAPI(title="Lovense MCP Server", lifespan=lifespan)


async def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify Bearer token - accepts both 'Bearer <token>' and '<token>' formats"""
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token - handle both "Bearer token" and "token" formats
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix

    if token != config.auth_token:
        logger.warning("Invalid authentication token provided")
        raise HTTPException(status_code=403, detail="Invalid authentication token")

    return True


def handle_initialize(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP initialize request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "lovense-mcp-server",
                "version": "2.0.0"
            }
        }
    }


def handle_tools_list(request_id: str) -> dict[str, Any]:
    """Handle MCP tools/list request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "vibrate",
                    "description": "Send vibration command to Lovense toy. Controls vibration intensity and duration.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID to control (empty string for all connected toys)",
                                "default": ""
                            },
                            "intensity": {
                                "type": "integer",
                                "description": "Vibration intensity level (0-20, where 0 is off and 20 is maximum)",
                                "minimum": 0,
                                "maximum": 20,
                                "default": 10
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Duration in seconds (1-60)",
                                "minimum": 1,
                                "maximum": 60,
                                "default": 5
                            }
                        },
                        "required": ["intensity", "duration"]
                    }
                },
                {
                    "name": "rotate",
                    "description": "Send rotation command to Lovense toy with rotation capability. Controls rotation speed and duration.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID to control (empty string for all connected toys)",
                                "default": ""
                            },
                            "intensity": {
                                "type": "integer",
                                "description": "Rotation intensity level (0-20)",
                                "minimum": 0,
                                "maximum": 20,
                                "default": 10
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Duration in seconds (1-60)",
                                "minimum": 1,
                                "maximum": 60,
                                "default": 5
                            }
                        },
                        "required": ["intensity", "duration"]
                    }
                },
                {
                    "name": "pump",
                    "description": "Send pump command to Lovense toy with pump capability. Controls pump intensity and duration.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID to control (empty string for all connected toys)",
                                "default": ""
                            },
                            "intensity": {
                                "type": "integer",
                                "description": "Pump intensity level (0-3)",
                                "minimum": 0,
                                "maximum": 3,
                                "default": 2
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Duration in seconds (1-60)",
                                "minimum": 1,
                                "maximum": 60,
                                "default": 5
                            }
                        },
                        "required": ["intensity", "duration"]
                    }
                },
                {
                    "name": "stop",
                    "description": "Immediately stop all running functions on Lovense toy(s). Emergency stop command.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID to stop (empty string for all connected toys)",
                                "default": ""
                            }
                        }
                    }
                },
                {
                    "name": "pattern",
                    "description": "Send a preset vibration pattern to Lovense toy. Use predefined patterns for varied experiences.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID to control (empty string for all connected toys)",
                                "default": ""
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Pattern name: 'pulse' (rhythmic pulses), 'wave' (gradual waves), 'fireworks' (random bursts), 'earthquake' (intense vibrations)",
                                "enum": ["pulse", "wave", "fireworks", "earthquake"],
                                "default": "pulse"
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Duration in seconds (1-60)",
                                "minimum": 1,
                                "maximum": 60,
                                "default": 10
                            }
                        },
                        "required": ["pattern", "duration"]
                    }
                }
            ]
        }
    }


async def handle_tools_call(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP tools/call request"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "vibrate":
            result = await api_client.vibrate(
                intensity=arguments.get("intensity", 10),
                duration=arguments.get("duration", 5),
                toy=arguments.get("toy", "")
            )
        elif tool_name == "rotate":
            result = await api_client.rotate(
                intensity=arguments.get("intensity", 10),
                duration=arguments.get("duration", 5),
                toy=arguments.get("toy", "")
            )
        elif tool_name == "pump":
            result = await api_client.pump(
                intensity=arguments.get("intensity", 2),
                duration=arguments.get("duration", 5),
                toy=arguments.get("toy", "")
            )
        elif tool_name == "stop":
            result = await api_client.stop(toy=arguments.get("toy", ""))
        elif tool_name == "pattern":
            pattern_map = {
                "pulse": "Preset:1",
                "wave": "Preset:2",
                "fireworks": "Preset:3",
                "earthquake": "Preset:4"
            }
            pattern = arguments.get("pattern", "pulse")
            action = pattern_map.get(pattern, "Preset:1")
            result = await api_client.send_command(
                "Function", action,
                arguments.get("duration", 10),
                arguments.get("toy", "")
            )
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

        if result["success"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Success: Command '{tool_name}' executed. Response: {result.get('data', {})}"
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"Failed to execute '{tool_name}': {result.get('error', 'Unknown error')}"
                }
            }

    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": f"Execution error: {str(e)}"
            }
        }


def handle_resources_list(request_id: str) -> dict[str, Any]:
    """Handle MCP resources/list request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "resources": [
                {
                    "uri": "lovense://toys/connected",
                    "name": "Connected Toys",
                    "description": "List of currently connected Lovense toys and their status",
                    "mimeType": "application/json"
                },
                {
                    "uri": "lovense://config/api",
                    "name": "API Configuration",
                    "description": "Current Lovense API configuration and connection details",
                    "mimeType": "application/json"
                }
            ]
        }
    }


async def handle_resources_read(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP resources/read request"""
    uri = params.get("uri")

    try:
        if uri == "lovense://toys/connected":
            result = await api_client.get_toys()
            if result["success"]:
                content = json.dumps(result["data"], indent=2)
            else:
                content = json.dumps({"error": result.get("error", "Failed to get toys")}, indent=2)

        elif uri == "lovense://config/api":
            config_info = {
                "domain_url": config.domain_url,
                "game_mode_ip": config.game_mode_ip,
                "game_mode_port": config.game_mode_port,
                "status": "connected"
            }
            content = json.dumps(config_info, indent=2)

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Unknown resource URI: {uri}"
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": content
                    }
                ]
            }
        }

    except Exception as e:
        logger.error(f"Resource read error: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": f"Failed to read resource: {str(e)}"
            }
        }


def handle_prompts_list(request_id: str) -> dict[str, Any]:
    """Handle MCP prompts/list request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "prompts": [
                {
                    "name": "control_toy",
                    "description": "Interactive prompt for controlling Lovense toys with guided parameters",
                    "arguments": [
                        {
                            "name": "action",
                            "description": "Action to perform: vibrate, rotate, pump, stop, or pattern",
                            "required": True
                        },
                        {
                            "name": "intensity",
                            "description": "Intensity level (0-20 for most actions, 0-3 for pump)",
                            "required": False
                        },
                        {
                            "name": "duration",
                            "description": "Duration in seconds (1-60)",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "quick_vibrate",
                    "description": "Quick vibration with preset intensity and duration",
                    "arguments": [
                        {
                            "name": "level",
                            "description": "Intensity level: low, medium, or high",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "pattern_play",
                    "description": "Play a vibration pattern with specified duration",
                    "arguments": [
                        {
                            "name": "pattern_name",
                            "description": "Pattern: pulse, wave, fireworks, or earthquake",
                            "required": True
                        },
                        {
                            "name": "duration",
                            "description": "Duration in seconds",
                            "required": False
                        }
                    ]
                }
            ]
        }
    }


def handle_prompts_get(request_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Handle MCP prompts/get request"""
    prompt_name = params.get("name")
    arguments = params.get("arguments", {})

    if prompt_name == "control_toy":
        action = arguments.get("action", "vibrate")
        intensity = arguments.get("intensity", "10")
        duration = arguments.get("duration", "5")

        message = f"""I want to control the Lovense toy with the following parameters:

Action: {action}
Intensity: {intensity}
Duration: {duration} seconds

Please execute this command using the appropriate tool."""

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "description": f"Control Lovense toy: {action}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": message
                        }
                    }
                ]
            }
        }

    elif prompt_name == "quick_vibrate":
        level = arguments.get("level", "medium")
        intensity_map = {"low": 5, "medium": 10, "high": 18}
        intensity = intensity_map.get(level, 10)

        message = f"Please send a quick vibration command with {level} intensity (level {intensity}) for 3 seconds."

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "description": f"Quick vibrate: {level}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": message
                        }
                    }
                ]
            }
        }

    elif prompt_name == "pattern_play":
        pattern = arguments.get("pattern_name", "pulse")
        duration = arguments.get("duration", "10")

        message = f"Please play the '{pattern}' vibration pattern for {duration} seconds."

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "description": f"Pattern: {pattern}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": message
                        }
                    }
                ]
            }
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": f"Unknown prompt: {prompt_name}"
            }
        }


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Main MCP endpoint with streaming support"""
    await verify_token(authorization)

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Handle JSON-RPC request
    method = body.get("method")
    request_id = body.get("id")
    params = body.get("params", {})

    logger.info(f"Received MCP request: method={method}, id={request_id}")

    # Route to appropriate handler
    if method == "initialize":
        response = handle_initialize(request_id, params)
    elif method == "tools/list":
        response = handle_tools_list(request_id)
    elif method == "tools/call":
        response = await handle_tools_call(request_id, params)
    elif method == "resources/list":
        response = handle_resources_list(request_id)
    elif method == "resources/read":
        response = await handle_resources_read(request_id, params)
    elif method == "prompts/list":
        response = handle_prompts_list(request_id)
    elif method == "prompts/get":
        response = handle_prompts_get(request_id, params)
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    # Stream response
    async def generate():
        yield json.dumps(response).encode('utf-8')

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server": "lovense-mcp-server",
        "version": "2.0.0",
        "domain_configured": bool(config and config.domain_url)
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
