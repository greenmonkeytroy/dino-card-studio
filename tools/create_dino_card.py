"""
Full pipeline: generate artwork (optional) then composite the card.
Usage:
  Generate + composite:
    py tools/create_dino_card.py --title "T-Rex Alpha" --action attack --footer "..." --border volcanic --generate --prompt "roaring, lava bg"
  Composite from existing file:
    py tools/create_dino_card.py --title "T-Rex Alpha" --action attack --footer "..." --border volcanic --artwork .tmp/trex.png
"""
import argparse
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(__file__))

from generate_dino_artwork import build_prompt, submit_image_task, poll_task, download_image
from composite_dino_card import composite_card, STYLES, ACTION_COLORS


def main():
    parser = argparse.ArgumentParser(description="Create a dino battle card end-to-end")
    parser.add_argument("--title", required=True, help="Dinosaur name")
    parser.add_argument("--action", required=True, choices=list(ACTION_COLORS))
    parser.add_argument("--footer", required=True, help="Card description text")
    parser.add_argument("--border", required=True, choices=list(STYLES))
    parser.add_argument("--generate", action="store_true",
                        help="Generate artwork via RunwayML (uses credits)")
    parser.add_argument("--prompt", default="",
                        help="Extra prompt detail for artwork generation")
    parser.add_argument("--artwork", default=None,
                        help="Path to existing artwork PNG (skips generation)")
    parser.add_argument("--output", default=None, help="Output card PNG path")
    args = parser.parse_args()

    slug = args.title.lower().replace(" ", "_")
    artwork_path = args.artwork or f".tmp/artwork_{slug}.png"
    output_path = args.output or f"output/{slug}.png"

    if args.generate:
        prompt = build_prompt(args.title, args.prompt)
        print(f"\n[1/2] Generating artwork...")
        print(f"Prompt: {prompt}")
        task_id = submit_image_task(prompt)
        print(f"Task: {task_id}")
        task = poll_task(task_id)
        url = task.get("output", [None])[0]
        if not url:
            print(f"ERROR: No output URL in task: {task}")
            sys.exit(1)
        download_image(url, artwork_path)
        print(f"Artwork saved: {artwork_path}")
    elif not args.artwork:
        print("ERROR: Provide --artwork <path> or use --generate to create artwork.")
        sys.exit(1)

    print(f"\n[2/2] Compositing card...")
    composite_card(args.title, args.action, args.footer, args.border, artwork_path, output_path)
    print(f"\nDone! Card: {output_path}")


if __name__ == "__main__":
    main()
