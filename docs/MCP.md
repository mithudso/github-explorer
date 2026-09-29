# MCP applicability

GitHub Explorer is a local Python/Textual application, not an MCP server or client.
It registers no MCP tools and requires no MCP credentials. [.mcp.json](../.mcp.json)
and [.vscode/mcp.json](../.vscode/mcp.json) intentionally contain empty server maps.

User-level agent tooling is outside the package and is not installed or configured
by this repository. The generated [tool inventory](tool-inventory.json) describes
project entry points and explicitly represents MCP applicability; it must not be
read as a list of running MCP servers.

If a future feature needs MCP, first document its purpose, trust boundary, tool
names, and secret handling, then update the configuration and tests. Do not add
unrelated services merely to fill a template.
