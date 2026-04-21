"""
Generate dino artwork via RunwayML gen4_image API.
Usage: py tools/generate_dino_artwork.py --name "T-Rex" --prompt "roaring, lava bg" --output .tmp/artwork.png
"""
import argparse
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"


def headers():
    secret = os.getenv("RUNWAYML_API_SECRET")
    if not secret:
        raise RuntimeError("RUNWAYML_API_SECRET not set in .env")
    return {
        "Authorization": f"Bearer {secret}",
        "X-Runway-Version": RUNWAY_VERSION,
        "Content-Type": "application/json",
    }


def build_prompt(name: str, extra: str) -> str:
    base = (
        f"A dramatic fantasy battle card artwork of a {name} dinosaur. "
        "Prehistoric setting, highly detailed, dynamic pose, painterly digital art style, "
        "rich colors, atmospheric lighting, epic fantasy card game art."
    )
    if extra:
        base += f" {extra}"
    return base


def submit_image_task(prompt: str) -> str:
    payload = {
        "model": "gen4_image",
        "promptText": prompt,
        "ratio": "1168:880",
    }
    r = requests.post(f"{API_BASE}/text_to_image", json=payload, headers=headers())
    r.raise_for_status()
    data = r.json()
    task_id = data.get("id")
    if not task_id:
        raise RuntimeError(f"No task id in response: {data}")
    return task_id


def poll_task(task_id: str, interval: int = 5, timeout: int = 300) -> dict:
    start = time.time()
    while True:
        r = requests.get(f"{API_BASE}/tasks/{task_id}", headers=headers())
        r.raise_for_status()
        task = r.json()
        status = task.get("status")
        print(f"  [{status}] polling task {task_id}...")
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Task {status}: {task.get('error', 'unknown error')}")
        if time.time() - start > timeout:
            raise TimeoutError(f"Task did not complete within {timeout}s")
        time.sleep(interval)


def download_image(url: str, output_path: str):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def main():
    parser = argparse.ArgumentParser(description="Generate dino artwork via RunwayML")
    parser.add_argument("--name", required=True, help="Dinosaur name (e.g. 'T-Rex')")
    parser.add_argument("--prompt", default="", help="Extra prompt details")
    parser.add_argument("--output", required=True, help="Output PNG path")
    args = parser.parse_args()

    prompt = build_prompt(args.name, args.prompt)
    print(f"Prompt: {prompt}")
    print("Submitting to RunwayML gen4_image...")

    task_id = submit_image_task(prompt)
    print(f"Task ID: {task_id}")

    task = poll_task(task_id)
    url = task.get("output", [None])[0]
    if not url:
        raise RuntimeError(f"No output URL in succeeded task: {task}")

    print(f"Downloading to {args.output}...")
    download_image(url, args.output)
    print(f"Done: {args.output}")


if __name__ == "__main__":
    main()
