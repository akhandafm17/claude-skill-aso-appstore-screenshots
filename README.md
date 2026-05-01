# ASO App Store Screenshots

A Claude Code skill that generates high-converting App Store screenshots for your iOS app. It analyzes your codebase, identifies core benefits, and creates professional screenshot images using AI.

## What It Does

1. **Benefit Discovery** — Analyzes your app's codebase to identify the 3-5 core benefits that drive downloads
2. **Screenshot Pairing** — Reviews your simulator screenshots, rates them, and pairs each with the best benefit
3. **Generation** — Creates polished App Store screenshots using a two-stage process: deterministic scaffolding (compose.py) + AI enhancement (Nano Banana Pro via fal.ai or Replicate)
4. **Showcase** — Generates a preview image with all screenshots side-by-side

## Installation

### 1. Add the skill to Claude Code

Copy the skill into your Claude Code skills directory:

```bash
git clone https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots.git \
  ~/.claude/skills/aso-appstore-screenshots
```

### 2. Install Python dependencies

```bash
pip install Pillow
```

### 3. Font requirement

The skill uses **SF Pro Display Black** for headline text. On macOS, install it from [Apple's developer fonts](https://developer.apple.com/fonts/). The expected path is:

```
/Library/Fonts/SF-Pro-Display-Black.otf
```

### 4. Get an API key (for AI enhancement)

The generation phase uses Nano Banana Pro for AI enhancement. You need an API key from one of these platforms:

**fal.ai** (recommended):
1. Sign up at [fal.ai](https://fal.ai)
2. Create an API key at [fal.ai/dashboard/keys](https://fal.ai/dashboard/keys)

**Replicate**:
1. Sign up at [replicate.com](https://replicate.com)
2. Create a token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)

The skill will ask for your API key when you reach the generation phase. Keys are used for the session only and never saved to disk.

## Usage

From within your app's project directory, run:

```
/aso-appstore-screenshots
```

The skill will guide you through each phase interactively. Progress is saved to Claude Code's memory system, so you can resume across conversations.

## How It Works

### Scaffold → Enhance Pipeline

Rather than generating screenshots from scratch (which produces inconsistent results), the skill uses a two-stage approach:

1. **compose.py** creates a deterministic scaffold with exact text positioning, device frame, and your simulator screenshot composited inside
2. **enhance.py** sends the scaffold to Nano Banana Pro (via fal.ai or Replicate) — adding a photorealistic device frame, breakout elements, and visual polish

This ensures consistent layout across all screenshots while letting AI handle the creative enhancement.

### Output

Screenshots are saved to a `screenshots/` directory in your project:

```
screenshots/
  01-benefit-slug/          ← working versions
    scaffold.png            ← deterministic compose.py output
    v1.jpg, v2.jpg, v3.jpg  ← AI-enhanced versions
    v1-resized.jpg, ...     ← cropped to App Store dimensions
  final/                    ← approved screenshots, ready to upload
    01-benefit-slug.jpg
    02-benefit-slug.jpg
  showcase.png              ← preview image with all screenshots
```

The `final/` folder contains App Store-ready screenshots at exact Apple dimensions (default: 1290×2796px for iPhone 6.7").

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill prompt — defines the multi-phase workflow |
| `compose.py` | Deterministic scaffold generator (Pillow-based) |
| `enhance.py` | AI enhancement via fal.ai or Replicate (Nano Banana Pro) |
| `generate_frame.py` | Generates the device frame template |
| `showcase.py` | Generates the side-by-side showcase image |
| `assets/device_frame.png` | Pre-rendered iPhone device frame template |

## License

MIT
