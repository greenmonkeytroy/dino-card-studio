import base64
import os
import sys
import tempfile
import threading
import time
import uuid

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
from composite_dino_card import STYLES, ACTION_COLORS, composite_card

app = Flask(__name__)

API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"

# In-memory job store — resets on server restart (fine for MVP)
jobs: dict[str, dict] = {}


# --- RunwayML helpers ---

def runway_headers():
    secret = os.getenv("RUNWAYML_API_SECRET")
    if not secret:
        raise RuntimeError("RUNWAYML_API_SECRET not configured")
    return {
        "Authorization": f"Bearer {secret}",
        "X-Runway-Version": RUNWAY_VERSION,
        "Content-Type": "application/json",
    }


def build_prompt(title: str, extra: str) -> str:
    base = (
        f"A dramatic fantasy battle card artwork of a {title} dinosaur. "
        "Prehistoric setting, highly detailed, dynamic pose, painterly digital art style, "
        "rich colors, atmospheric lighting, epic fantasy card game art."
    )
    return f"{base} {extra}".strip() if extra else base


def submit_image_task(prompt: str) -> str:
    r = requests.post(
        f"{API_BASE}/text_to_image",
        json={"model": "gen4_image", "promptText": prompt, "ratio": "1168:880"},
        headers=runway_headers(),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    task_id = data.get("id")
    if not task_id:
        raise RuntimeError(f"No task id in response: {data}")
    return task_id


def poll_task(task_id: str, job_id: str, interval: int = 5, timeout: int = 300) -> dict:
    start = time.time()
    while True:
        r = requests.get(f"{API_BASE}/tasks/{task_id}", headers=runway_headers(), timeout=15)
        r.raise_for_status()
        task = r.json()
        status = task.get("status")
        jobs[job_id]["progress"] = f"Generating artwork… [{status}]"
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"RunwayML task {status}: {task.get('error', 'unknown')}")
        if time.time() - start > timeout:
            raise TimeoutError("Artwork generation timed out after 5 minutes")
        time.sleep(interval)


def download_image_to_tmp(url: str) -> str:
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    for chunk in r.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name


def save_upload_to_tmp(b64_data: str) -> str:
    data = base64.b64decode(b64_data.split(",")[-1])
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


# --- Background generation job ---

def run_job(job_id: str, payload: dict):
    artwork_path = None
    card_path = None
    try:
        title = payload["title"]
        action = payload["action"]
        footer = payload["footer"]
        border = payload["border"]
        source = payload.get("source", "generate")
        extra_prompt = payload.get("prompt", "")
        artwork_b64 = payload.get("artwork_b64")

        if source == "upload" and artwork_b64:
            jobs[job_id]["progress"] = "Processing uploaded artwork…"
            artwork_path = save_upload_to_tmp(artwork_b64)
        else:
            jobs[job_id]["progress"] = "Submitting to RunwayML…"
            prompt = build_prompt(title, extra_prompt)
            jobs[job_id]["prompt_used"] = prompt
            task_id = submit_image_task(prompt)
            jobs[job_id]["progress"] = f"Generating artwork… [PENDING]"
            task = poll_task(task_id, job_id)
            url = task.get("output", [None])[0]
            if not url:
                raise RuntimeError("No output URL from RunwayML")
            jobs[job_id]["progress"] = "Downloading artwork…"
            artwork_path = download_image_to_tmp(url)

        jobs[job_id]["progress"] = "Compositing card…"
        card_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        card_path = card_tmp.name
        card_tmp.close()
        art_scale = float(payload.get("art_scale", 1.0))
        art_x = float(payload.get("art_x", 0.0))
        art_y = float(payload.get("art_y", 0.0))
        composite_card(title, action, footer, border, artwork_path, card_path,
                       art_scale=art_scale, art_offset_x=art_x, art_offset_y=art_y)

        with open(card_path, "rb") as f:
            card_b64 = base64.b64encode(f.read()).decode()

        jobs[job_id].update({"status": "done", "progress": "Card ready!", "card_b64": card_b64})

    except Exception as e:
        jobs[job_id].update({"status": "error", "progress": str(e)})
    finally:
        for path in [artwork_path, card_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass


# --- Routes ---

@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/")
def index():
    return render_template(
        "index.html",
        border_styles=list(STYLES.keys()),
        action_types=list(ACTION_COLORS.keys()),
    )


@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No payload"}), 400

    required = ["title", "action", "footer", "border"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "progress": "Starting…", "card_b64": None}
    t = threading.Thread(target=run_job, args=(job_id, payload), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
