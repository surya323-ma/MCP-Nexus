"""
FastMCP server exposing file operation tools (list/read/write/delete).
Runs over the streamable-http transport so it can be deployed as a standalone
Render web service and reached over a normal HTTPS URL.
"""
import os
from fastmcp import FastMCP

mcp = FastMCP("File Operations Server")

# All file operations are sandboxed to this directory.
BASE_DIR = os.environ.get("FILE_SERVER_BASE_DIR", "/tmp/mcp_files")
os.makedirs(BASE_DIR, exist_ok=True)


def _safe_path(filename: str) -> str:
    """Resolve a filename to an absolute path, refusing anything that
    escapes the sandbox directory (basic path-traversal protection)."""
    path = os.path.abspath(os.path.join(BASE_DIR, filename))
    if not path.startswith(os.path.abspath(BASE_DIR)):
        raise ValueError("Invalid file path: path traversal is not allowed.")
    return path


@mcp.tool()
def list_files() -> list[str]:
    """List every file currently available in the workspace."""
    return sorted(os.listdir(BASE_DIR))


@mcp.tool()
def read_file(filename: str) -> str:
    """Read and return the text contents of a file in the workspace.

    Args:
        filename: Name of the file to read (relative to the workspace).
    """
    path = _safe_path(filename)
    if not os.path.exists(path):
        return f"Error: '{filename}' does not exist."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@mcp.tool()
def write_file(filename: str, content: str) -> str:
    """Create or overwrite a text file in the workspace with the given content.

    Args:
        filename: Name of the file to write (relative to the workspace).
        content: Text content to write into the file.
    """
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} characters to '{filename}'."


@mcp.tool()
def delete_file(filename: str) -> str:
    """Delete a file from the workspace.

    Args:
        filename: Name of the file to delete.
    """
    path = _safe_path(filename)
    if os.path.exists(path):
        os.remove(path)
        return f"Deleted '{filename}'."
    return f"'{filename}' does not exist."


if __name__ == "__main__":
    # Render (and most PaaS platforms) inject the port to bind via $PORT.
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
