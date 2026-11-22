import json
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image as PILImage
import pyvista as pv

BASE_DIR = Path(__file__).parent.resolve()
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)


def run_model_script(filepath: str) -> dict:
    """Executes a build123d script in a subprocess, checks metrics, and exports STL/STEP."""
    script_path = Path(filepath).resolve()
    if not script_path.exists():
        return {"ok": False, "error": f"File not found: {script_path}"}

    stem = script_path.stem
    stl_path = EXPORTS_DIR / f"{stem}.stl"
    step_path = EXPORTS_DIR / f"{stem}.step"

    runner_code = f"""
import json, traceback
from build123d import export_stl, export_step

ns = {{}}
try:
    with open({str(script_path)!r}, "r", encoding="utf-8") as f:
        exec(compile(f.read(), {str(script_path)!r}, "exec"), ns)

    part = ns.get("result")
    if part is None:
        raise ValueError("Script must assign the final build123d shape to a variable named 'result'.")
    if hasattr(part, "part"):
        part = part.part

    bb = part.bounding_box()
    export_stl(part, {str(stl_path)!r})
    export_step(part, {str(step_path)!r})

    out = {{
        "ok": True,
        "valid": bool(part.is_valid),
        "solid_count": len(part.solids()),
        "volume_mm3": round(float(part.volume), 3),
        "bbox_mm": {{
            "x": round(float(bb.size.X), 3),
            "y": round(float(bb.size.Y), 3),
            "z": round(float(bb.size.Z), 3),
        }},
        "stl_path": {str(stl_path)!r},
        "step_path": {str(step_path)!r},
    }}
    print("___CAD_JSON___" + json.dumps(out))
except Exception:
    print("___CAD_JSON___" + json.dumps({{"ok": False, "error": traceback.format_exc()}}))
"""
    proc = subprocess.run(
        [sys.executable, "-c", runner_code],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    for line in proc.stdout.splitlines():
        if line.startswith("___CAD_JSON___"):
            return json.loads(line.replace("___CAD_JSON___", "", 1))

    return {"ok": False, "error": proc.stderr or proc.stdout or "Unknown execution error."}


def render_four_views(stl_path: str) -> str:
    """Renders Iso, Front, Top, and Right views of an STL into a single 2x2 PNG."""
    stl = Path(stl_path).resolve()
    mesh = pv.read(str(stl))

    views = [
        ("iso", lambda p: p.view_isometric()),
        ("front", lambda p: p.view_xz()),
        ("top", lambda p: p.view_xy()),
        ("right", lambda p: p.view_yz()),
    ]

    imgs = []
    for name, set_cam in views:
        plotter = pv.Plotter(off_screen=True, window_size=(512, 512))
        plotter.set_background("white")
        plotter.add_mesh(mesh, color="steelblue", smooth_shading=True, show_edges=False)
        plotter.add_axes()
        plotter.add_text(name.upper(), position="upper_left", font_size=12, color="black")
        set_cam(plotter)
        plotter.reset_camera()
        img_array = plotter.screenshot(return_img=True)
        plotter.close()
        imgs.append(PILImage.fromarray(img_array))

    grid = PILImage.new("RGB", (1024, 1024), "white")
    grid.paste(imgs[0], (0, 0))
    grid.paste(imgs[1], (512, 0))
    grid.paste(imgs[2], (0, 512))
    grid.paste(imgs[3], (512, 512))

    out_png = EXPORTS_DIR / f"{stl.stem}_views.png"
    grid.save(out_png)
    return str(out_png)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cad_engine.py models/test_bracket.py")
        sys.exit(1)
    res = run_model_script(sys.argv[1])
    print(json.dumps(res, indent=2))
    if res.get("ok"):
        png = render_four_views(res["stl_path"])
        print(f"Rendered 4-view preview to: {png}")