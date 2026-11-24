from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cad_engine import run_model_script, render_four_views

ROOT = Path(__file__).parent.resolve()
MODELS_DIR = ROOT / "models"
EXPORTS_DIR = ROOT / "exports"
MODELS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CAD Agent API")

# Allow requests from Chrome/Edge extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PNGs and STEP files at http://127.0.0.1:8000/exports/<file>
app.mount("/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")


class ScriptRequest(BaseModel):
    script_path: str  # e.g. "models/l_bracket.py" or "l_bracket.py"


class SaveAndRunRequest(BaseModel):
    filename: str  # e.g. "l_bracket.py"
    code: str


def _safe_model_path(rel_or_name: str) -> Path:
    if "/" in rel_or_name or "\\" in rel_or_name:
        path = (ROOT / rel_or_name).resolve()
    else:
        path = (MODELS_DIR / rel_or_name).resolve()
    if not path.is_relative_to(MODELS_DIR):
        raise HTTPException(status_code=400, detail="Script must be inside models/")
    return path


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run_script(req: ScriptRequest):
    path = _safe_model_path(req.script_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {req.script_path}")
    return run_model_script(str(path))


@app.post("/render")
async def render_views(req: ScriptRequest):
    path = _safe_model_path(req.script_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {req.script_path}")

    stl_path = EXPORTS_DIR / f"{path.stem}.stl"
    if not stl_path.exists():
        run_result = run_model_script(str(path))
        if not run_result.get("ok"):
            raise HTTPException(status_code=400, detail=run_result)
        stl_path = Path(run_result.get("stl_path", stl_path))

    png_path = Path(render_four_views(str(stl_path)))
    return {
        "ok": True,
        "png_path": str(png_path),
        "image_url": f"http://127.0.0.1:8000/exports/{png_path.name}",
    }


@app.post("/save-and-run")
async def save_and_run(req: SaveAndRunRequest):
    if not req.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Filename must end with .py")
    path = _safe_model_path(req.filename)
    path.write_text(req.code, encoding="utf-8")

    run_result = run_model_script(str(path))
    image_url = None
    if run_result.get("ok"):
        stl_path = Path(run_result.get("stl_path", EXPORTS_DIR / f"{path.stem}.stl"))
        png_path = Path(render_four_views(str(stl_path)))
        image_url = f"http://127.0.0.1:8000/exports/{png_path.name}"

    return {
        "script_path": f"models/{path.name}",
        "run": run_result,
        "image_url": image_url,
    }