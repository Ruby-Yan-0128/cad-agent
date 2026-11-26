import base64
import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel

from cad_engine import run_model_script, render_four_views

load_dotenv()

ROOT = Path(__file__).parent.resolve()
MODELS_DIR = ROOT / "models"
EXPORTS_DIR = ROOT / "exports"
MODELS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

MODEL_ID = "gemini-3.8-flash"
client = genai.Client()

import time

FALLBACK_MODEL_ID = "gemini-4-hydrogen"

def _create_interaction(**kwargs):
    for attempt in range(2):
        try:
            return client.interactions.create(**kwargs)
        except Exception as e:
            if "503" in str(e) or "service_unavailable" in str(e):
                if attempt == 0:
                    time.sleep(2)
                    continue
                kwargs["model"] = FALLBACK_MODEL_ID
                return client.interactions.create(**kwargs)
            raise

RULES_PATH = ROOT / ".github" / "copilot-instructions.md"
SYSTEM_INSTRUCTION = (
    RULES_PATH.read_text(encoding="utf-8")
    if RULES_PATH.exists()
    else (
        "You are a parametric CAD agent writing build123d Python scripts in models/. "
        "Assign the final shape to `result`, define key dimensions in mm as uppercase constants, "
        "and call write_and_run_model to execute and visually inspect every model you create or edit."
    )
)

TOOLS = [
    {
        "type": "function",
        "name": "read_model_script",
        "description": "Read an existing build123d Python script from models/ before modifying it.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename inside models/, e.g. l_bracket.py"}
            },
            "required": ["filename"],
        },
    },
    {
        "type": "function",
        "name": "write_and_run_model",
        "description": (
            "Save a build123d Python script to models/, run it to validate geometry and export STEP/STL, "
            "and return the validation metadata plus a 2x2 multi-view PNG for visual inspection."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename ending in .py, e.g. l_bracket.py"},
                "code": {"type": "string", "description": "Complete build123d Python script assigning final shape to `result`."},
            },
            "required": ["filename", "code"],
        },
    },
]

app = FastAPI(title="CAD Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")


class ScriptRequest(BaseModel):
    script_path: str


class SaveAndRunRequest(BaseModel):
    filename: str
    code: str


class ChatRequest(BaseModel):
    prompt: str
    previous_interaction_id: str | None = None


def _safe_model_path(rel_or_name: str) -> Path:
    if "/" in rel_or_name or "\\" in rel_or_name:
        path = (ROOT / rel_or_name).resolve()
    else:
        path = (MODELS_DIR / rel_or_name).resolve()
    if not path.is_relative_to(MODELS_DIR):
        raise HTTPException(status_code=400, detail="Script must be inside models/")
    return path


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run")
async def run_script(req: ScriptRequest):
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


@app.post("/chat")
async def chat(req: ChatRequest):
    kwargs = {
        "model": MODEL_ID,
        "input": req.prompt,
        "tools": TOOLS,
        "system_instruction": SYSTEM_INSTRUCTION,
    }
    if req.previous_interaction_id:
        kwargs["previous_interaction_id"] = req.previous_interaction_id

    interaction = _create_interaction(**kwargs)

    last_artifact = {}
    max_turns = 6

    for _ in range(max_turns):
        fc_steps = [s for s in interaction.steps if s.type == "function_call"]
        if not fc_steps:
            break

        tool_results = []
        for step in fc_steps:
            args = step.arguments or {}

            if step.name == "read_model_script":
                try:
                    path = _safe_model_path(args["filename"])
                    content = path.read_text(encoding="utf-8") if path.exists() else f"File not found: {args['filename']}"
                except Exception as e:
                    content = f"Error: {e}"
                tool_results.append({
                    "type": "function_result",
                    "name": step.name,
                    "call_id": step.id,
                    "result": [{"type": "text", "text": content}],
                })

            elif step.name == "write_and_run_model":
                filename = args.get("filename", "model.py")
                if not filename.endswith(".py"):
                    filename += ".py"
                code = args.get("code", "")
                path = _safe_model_path(filename)
                path.write_text(code, encoding="utf-8")

                run_result = run_model_script(str(path))
                result_parts = [{"type": "text", "text": json.dumps(run_result)}]

                if run_result.get("ok"):
                    stl_path = Path(run_result.get("stl_path", EXPORTS_DIR / f"{path.stem}.stl"))
                    png_path = Path(render_four_views(str(stl_path)))
                    img_b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
                    result_parts.append({
                        "type": "image",
                        "data": img_b64,
                        "mime_type": "image/png",
                    })
                    last_artifact = {
                        "filename": path.name,
                        "code": code,
                        "run": run_result,
                        "image_url": f"http://127.0.0.1:8000/exports/{png_path.name}",
                        "step_url": f"http://127.0.0.1:8000/exports/{path.stem}.step",
                    }

                tool_results.append({
                    "type": "function_result",
                    "name": step.name,
                    "call_id": step.id,
                    "result": result_parts,
                })

        interaction = _create_interaction(
            model=MODEL_ID,
            input=tool_results,
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
            previous_interaction_id=interaction.id,
        )

    return {
        "interaction_id": interaction.id,
        "reply": interaction.output_text,
        "artifact": last_artifact or None,
    }