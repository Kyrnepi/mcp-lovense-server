"""
MCP HTTP Server with Bearer Authentication
Provides Lovense toy control via MCP protocol
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import json
import asyncio
import logging
import os
from typing import Optional, Dict, Any
import requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-http-server")

# Global configuration
config = {
    "domain_url": "",
    "auth_token": ""
}

# ========================
# Utility Functions
# ========================

def convert_ip_to_domain(game_mode_ip: str, https_port: str) -> tuple:
    """Convert local IP to Lovense domain format"""
    if not game_mode_ip:
        return None, "❌ IP address cannot be empty"
    
    ip = game_mode_ip.strip()
    
    if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
        return None, "❌ Invalid IP format"
    
    for part in ip.split('.'):
        try:
            if not 0 <= int(part) <= 255:
                raise ValueError
        except ValueError:
            return None, "❌ Each IP segment must be between 0 and 255"
    
    domain = f"https://{ip.replace('.', '-')}.lovense.club:{https_port}"
    return domain, f"✅ Converted domain: {domain}"


def send_functions(toys: str, commands: str, time_sec: int) -> Dict[str, Any]:
    """Send function command to Lovense toys"""
    url = f"{config['domain_url']}/command"
    data = {
        "command": "Function",
        "action": commands,
        "timeSec": time_sec,
        "toy": toys,
        "apiVer": 1
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ SendFunctions Response: {result}")
            return {"success": True, "data": result}
        else:
            logger.error(f"❌ SendFunctions Failed. Status: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ SendFunctions Exception: {str(e)}")
        return {"success": False, "error": str(e)}


def send_stop_function(toys: str) -> Dict[str, Any]:
    """Stop all running toy functions"""
    url = f"{config['domain_url']}/command"
    data = {
        "command": "Function",
        "action": "Stop",
        "timeSec": 0,
        "toy": toys,
        "apiVer": 1
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ SendStopFunction Response: {result}")
            return {"success": True, "data": result}
        else:
            logger.error(f"❌ SendStopFunction Failed. Status: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ SendStopFunction Exception: {str(e)}")
        return {"success": False, "error": str(e)}


# ========================
# Lifespan Management
# ========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    # Startup
    game_mode_ip = os.getenv("GAME_MODE_IP")
    game_mode_port = os.getenv("GAME_MODE_PORT", "30010")
    auth_token = os.getenv("AUTH_TOKEN")
    
    if not game_mode_ip:
        logger.error("❌ GAME_MODE_IP environment variable is required")
        raise ValueError("GAME_MODE_IP not set")
    
    if not auth_token:
        logger.error("❌ AUTH_TOKEN environment variable is required")
        raise ValueError("AUTH_TOKEN not set")
    
    domain, message = convert_ip_to_domain(game_mode_ip, game_mode_port)
    if not domain:
        logger.error(f"❌ Failed to convert IP: {message}")
        raise ValueError(message)
    
    config["domain_url"] = domain
    config["auth_token"] = auth_token
    
    logger.info(f"✅ Server configured: {domain}")
    logger.info(f"✅ Authentication enabled")
    
    yield
    
    # Shutdown
    logger.info("🛑 Server shutting down")


# Create FastAPI app with lifespan
app = FastAPI(title="Lovense MCP Server", lifespan=lifespan)


# ========================
# Authentication Middleware
# ========================

async def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify Bearer token - accepts both 'Bearer <token>' and '<token>' formats"""
    logger.info(f"Authorization header received: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Extract token - handle both "Bearer token" and "token" formats
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
    
    logger.info(f"Extracted token (first 10 chars): {token[:10]}...")
    logger.info(f"Expected token (first 10 chars): {config['auth_token'][:10]}...")
    
    if token != config["auth_token"]:
        logger.warning("Invalid authentication token provided")
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    
    logger.info("✅ Authentication successful")
    return True


# ========================
# MCP Protocol Handlers
# ========================

def handle_initialize(request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP initialize request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "lovense-remote-mcp",
                "version": "1.0.0"
            }
        }
    }


def handle_tools_list(request_id: str) -> Dict[str, Any]:
    """Handle MCP tools/list request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "send_vibrate",
                    "description": "Send vibration command to Lovense toys",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID (empty string for all toys)",
                                "default": ""
                            },
                            "intensity": {
                                "type": "integer",
                                "description": "Vibration intensity (0-20)",
                                "minimum": 0,
                                "maximum": 20,
                                "default": 10
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Duration in seconds",
                                "minimum": 1,
                                "maximum": 60,
                                "default": 2
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "send_stop",
                    "description": "Stop all running toy functions immediately",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "toy": {
                                "type": "string",
                                "description": "Toy ID (empty string for all toys)",
                                "default": ""
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
    }


def handle_tools_call(request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tools/call request"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name == "send_vibrate":
        toy = arguments.get("toy", "")
        intensity = arguments.get("intensity", 10)
        duration = arguments.get("duration", 2)
        
        result = send_functions(toy, f"Vibrate:{intensity}", duration)
        
        if result["success"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ Vibration sent: intensity={intensity}, duration={duration}s"
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
                    "message": f"Failed to send vibration: {result.get('error', 'Unknown error')}"
                }
            }
    
    elif tool_name == "send_stop":
        toy = arguments.get("toy", "")
        result = send_stop_function(toy)
        
        if result["success"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": "✅ All toy functions stopped"
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
                    "message": f"Failed to stop functions: {result.get('error', 'Unknown error')}"
                }
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown tool: {tool_name}"
            }
        }


# ========================
# HTTP Endpoints
# ========================

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
        response = handle_tools_call(request_id, params)
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
        "domain_configured": bool(config["domain_url"])
    }


# ========================
# Application Entry Point
# ========================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)