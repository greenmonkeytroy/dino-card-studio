# Workflow: Create Dino Battle Card

## Objective
Generate a single 750×1050px dinosaur battle card as a PNG. The card has a themed border, a key artwork image, a title pill, an action pill, and a footer description pill.

## Required Inputs
| Input | Description | Example |
|-------|-------------|---------|
| `title` | Dinosaur name shown at top | "T-Rex Alpha" |
| `action` | Card action type | attack, defend, flee, dodge, roar, stomp, charge, bite, crush, ambush |
| `footer` | Flavor/description text (1–3 sentences) | "Apex predator of the Cretaceous..." |
| `border` | Border style preset | bone, stone, jungle, volcanic, ice |
| `artwork_source` | How to get the key image | `generate` or a local file path |
| `artwork_prompt` | Extra detail for AI generation (optional) | "roaring, volcanic background, dramatic lighting" |

## Tools
| Tool | Script | Purpose |
|------|--------|---------|
| Generate artwork | `tools/generate_dino_artwork.py` | Calls RunwayML gen4_image to produce the dino artwork |
| Composite card | `tools/composite_dino_card.py` | Assembles border, image, pills, and text into final PNG |
| Full orchestrator | `tools/create_dino_card.py` | Runs both tools end to end in one command |

## Steps

### Step 1 — Get the artwork
**Option A: Generate with RunwayML**
```bash
py tools/generate_dino_artwork.py --name "T-Rex Alpha" --prompt "roaring, volcanic background, dramatic lighting" --output .tmp/artwork_trex.png
```
This calls `POST /text_to_image` with model `gen4_image`, polls until SUCCEEDED, then downloads the image.

**Option B: Use an existing file**
Skip this step — pass the file path directly to the compositor in Step 2.

### Step 2 — Composite the card
```bash
py tools/composite_dino_card.py \
  --title "T-Rex Alpha" \
  --action attack \
  --footer "The undisputed ruler of the Cretaceous. One bite ends the battle." \
  --border volcanic \
  --artwork .tmp/artwork_trex.png \
  --output output/trex_alpha.png
```

### Step 3 — One-command shortcut (generate + composite)
```bash
py tools/create_dino_card.py \
  --title "T-Rex Alpha" \
  --action attack \
  --footer "The undisputed ruler of the Cretaceous. One bite ends the battle." \
  --border volcanic \
  --generate \
  --prompt "roaring, volcanic background, dramatic lighting"
```

## Border Presets
| Style | Palette | Vibe |
|-------|---------|------|
| `bone` | Ivory, tan, dark gold | Fossil museum, ancient skeleton |
| `stone` | Charcoal, grey | Cave wall, rock formation |
| `jungle` | Deep green | Dense prehistoric jungle |
| `volcanic` | Dark red, ember orange | Lava fields, eruption |
| `ice` | Deep navy, cyan | Ice age, frozen tundra |

## Action Types & Colors
| Action | Color |
|--------|-------|
| attack | Deep red |
| defend | Steel blue |
| flee | Forest green |
| dodge | Amber |
| roar | Purple |
| stomp | Dark brown |
| charge | Orange |
| bite | Crimson |
| crush | Earth brown |
| ambush | Dark green |

## Output
- PNG saved to `output/<slug>.png` at 750×1050px
- Artwork cached to `.tmp/artwork_<name>.png` (valid 24h from RunwayML)

## Edge Cases
- **RunwayML rate limit**: If `generate_dino_artwork.py` fails with 429, wait 60s and retry. API allows 2 concurrent gen4_image generations.
- **Long footer text**: The compositor auto-wraps text. Keep footer under 200 characters for best layout.
- **Missing font**: Falls back to Pillow default if Impact/Arial not found on system.
- **Artwork URL expiry**: RunwayML image URLs expire after 24h. Re-run generate step if the `.tmp/` file is missing or stale.
