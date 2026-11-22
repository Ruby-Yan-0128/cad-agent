import sys
from pathlib import Path

sys.stderr = open(Path(__file__).with_name("mcp_debug.log"), "w", buffering=1)
print("server.py launched by VS Code", file=sys.stderr)

from mcp.server.mcpserver import MCPServer, Image
from cad_engine import run_model_script, render_four_views

mcp = MCPServer("cad-agent")


@mcp.tool()
def run_cad_script(filepath: str) -> dict:
    """Run a build123d Python script, export STL/STEP, and return geometry metrics (bbox, volume, solid count)."""
    return run_model_script(filepath)


@mcp.tool()
def render_model_views(filepath: str) -> Image:
    """Run a build123d script and return a 2x2 multi-view PNG (Iso, Front, Top, Right) for visual inspection."""
    res = run_model_script(filepath)
    if not res.get("ok"):
        raise RuntimeError(res.get("error", "Model execution failed."))
    png_path = render_four_views(res["stl_path"])
    return Image(path=png_path)


if __name__ == "__main__":
    mcp.run()