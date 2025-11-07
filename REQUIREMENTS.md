# Lovense MCP Server - Original Requirements

## Project Specification

I need you to adapt the provided MCP server to be an HTTP streamable MCP server while respecting the MCP standard:

### Complete MCP Protocol

- **initialize method**: Respond to client initialization request
- **tools/list method**: List available tools with their schemas
- **tools/call method**: Execute tools with provided parameters
- **JSON-RPC 2.0 format**: All responses follow the MCP standard

### Docker Container Requirements

I want this server to run in a Docker container, so all necessary variables should be managed through Docker environment variables.

Structure the project and provide me the code for each necessary file.

### Authentication

Add bearer token authentication to the MCP server. This token should also be in the Docker environment variables.

### Endpoint

The server must respond on the `/mcp` route.

---

**Note**: This document contains the original French requirements that were used to create the initial version of this MCP server. The server has since been refactored to use the MCP Python SDK with stdio transport, which is the standard approach for MCP servers.
