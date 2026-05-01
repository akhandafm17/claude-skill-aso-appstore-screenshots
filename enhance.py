#!/usr/bin/env python3
"""
Enhance App Store screenshot scaffolds using Nano Banana Pro
via fal.ai or Replicate APIs.

No external dependencies — uses only Python standard library.

Usage:
    python3 enhance.py \
        --provider fal \
        --api-key "your-key" \
        --prompt "Enhancement instructions..." \
        --images scaffold.png [style_template.jpg] \
        --outputs v1.jpg v2.jpg v3.jpg \
        --aspect-ratio "9:16" \
        --resolution "4K"
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

POLL_INTERVAL = 3     # seconds between status checks
MAX_POLL_TIME = 300   # 5 minutes max wait


# ── Helpers ────────────────────────────────────────────────────────────

def encode_image_data_uri(path):
    """Encode a local image file as a base64 data URI."""
    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def http_json(url, data=None, headers=None, method=None):
    """Make an HTTP request, return parsed JSON."""
    body = json.dumps(data).encode() if data is not None else None
    if method is None:
        method = "POST" if body else "GET"
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"Error: HTTP {e.code}\n{err_body}", file=sys.stderr)
        sys.exit(1)


def download_file(url, path):
    """Download a file from a URL to a local path."""
    urllib.request.urlretrieve(url, path)


# ── fal.ai ─────────────────────────────────────────────────────────────

def enhance_fal(api_key, prompt, image_paths, output_paths, aspect_ratio, resolution):
    n = len(output_paths)
    post_headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}
    get_headers = {"Authorization": f"Key {api_key}"}

    print(f"Encoding {len(image_paths)} image(s)...")
    image_urls = [encode_image_data_uri(p) for p in image_paths]

    payload = {
        "prompt": prompt,
        "image_urls": image_urls,
        "num_images": n,
        "aspect_ratio": aspect_ratio,
        "output_format": "jpeg",
        "resolution": resolution,
    }

    print("Submitting to fal.ai Nano Banana Pro...")
    result = http_json(
        "https://queue.fal.run/fal-ai/nano-banana-pro/edit",
        data=payload,
        headers=post_headers,
    )

    request_id = result.get("request_id")
    if not request_id:
        # Synchronous response
        if "images" in result:
            for i, img in enumerate(result["images"][:n]):
                download_file(img["url"], output_paths[i])
                print(f"✓ {output_paths[i]}")
            return
        print(f"Unexpected response: {json.dumps(result)[:500]}", file=sys.stderr)
        sys.exit(1)

    # Use URLs from the queue response (more reliable than constructing them)
    status_url = result.get("status_url")
    response_url = result.get("response_url")
    # Fallback to constructed URLs if not provided
    base = f"https://queue.fal.run/fal-ai/nano-banana-pro/edit/requests/{request_id}"
    if not status_url:
        status_url = f"{base}/status"
    if not response_url:
        response_url = base

    print(f"Queued (ID: {request_id}). Generating {n} image(s)...")
    start = time.time()
    while time.time() - start < MAX_POLL_TIME:
        time.sleep(POLL_INTERVAL)
        status = http_json(status_url, headers=get_headers)
        s = status.get("status")
        if s == "COMPLETED":
            break
        elif s in ("FAILED", "CANCELLED"):
            logs = status.get("logs", "")
            print(f"Generation {s}. {logs}", file=sys.stderr)
            sys.exit(1)
        elapsed = int(time.time() - start)
        print(f"  {s} ({elapsed}s)...")
    else:
        print("Timed out waiting for generation.", file=sys.stderr)
        sys.exit(1)

    # Fetch result
    result = http_json(response_url, headers=get_headers)
    images = result.get("images", [])
    if not images:
        print(f"No images in result: {json.dumps(result)[:500]}", file=sys.stderr)
        sys.exit(1)

    for i, img in enumerate(images[:n]):
        download_file(img["url"], output_paths[i])
        print(f"✓ {output_paths[i]}")

    if len(images) < n:
        print(f"Warning: requested {n} images but got {len(images)}", file=sys.stderr)


# ── Replicate ──────────────────────────────────────────────────────────

def enhance_replicate(api_key, prompt, image_paths, output_paths, aspect_ratio):
    n = len(output_paths)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    print(f"Encoding {len(image_paths)} image(s)...")
    input_data = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "num_outputs": n,
    }

    if image_paths:
        input_data["image"] = encode_image_data_uri(image_paths[0])
    # Replicate's Nano Banana Pro accepts a single `image` param.
    # Additional reference images (style template) should be described
    # in the prompt for Replicate, or use fal.ai for multi-image input.
    if len(image_paths) > 1:
        print(
            "Note: Replicate accepts one input image. Additional images "
            "are included in prompt context only. Use fal.ai for native "
            "multi-image support.",
            file=sys.stderr,
        )

    print("Submitting to Replicate Nano Banana Pro...")
    result = http_json(
        "https://api.replicate.com/v1/models/google/nano-banana-pro/predictions",
        data={"input": input_data},
        headers=headers,
    )

    pred_id = result.get("id")
    status = result.get("status")

    if status == "succeeded":
        for i, url in enumerate(result.get("output", [])[:n]):
            download_file(url, output_paths[i])
            print(f"✓ {output_paths[i]}")
        return

    # Poll for completion
    poll_url = result.get("urls", {}).get(
        "get", f"https://api.replicate.com/v1/predictions/{pred_id}"
    )
    print(f"Prediction created (ID: {pred_id}). Generating {n} image(s)...")
    start = time.time()
    while time.time() - start < MAX_POLL_TIME:
        time.sleep(POLL_INTERVAL)
        result = http_json(poll_url, headers=headers)
        status = result.get("status")
        if status == "succeeded":
            break
        elif status in ("failed", "canceled"):
            print(
                f"Prediction {status}: {result.get('error', 'unknown error')}",
                file=sys.stderr,
            )
            sys.exit(1)
        elapsed = int(time.time() - start)
        print(f"  {status} ({elapsed}s)...")
    else:
        print("Timed out waiting for prediction.", file=sys.stderr)
        sys.exit(1)

    output = result.get("output", [])
    if not output:
        print("No output images.", file=sys.stderr)
        sys.exit(1)

    for i, url in enumerate(output[:n]):
        download_file(url, output_paths[i])
        print(f"✓ {output_paths[i]}")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Enhance App Store screenshots via Nano Banana Pro (fal.ai or Replicate)"
    )
    p.add_argument("--provider", choices=["fal", "replicate"], required=True)
    p.add_argument(
        "--api-key",
        help="API key (or set FAL_KEY / REPLICATE_API_TOKEN env var)",
    )
    p.add_argument("--prompt", required=True)
    p.add_argument("--images", nargs="+", required=True, help="Input image path(s)")
    p.add_argument(
        "--outputs",
        nargs="+",
        required=True,
        help="Output path(s) — one per version to generate",
    )
    p.add_argument("--aspect-ratio", default="9:16")
    p.add_argument(
        "--resolution", default="4K", help="fal.ai only: 1K, 2K, 4K"
    )
    args = p.parse_args()

    # Resolve API key
    env_var = "FAL_KEY" if args.provider == "fal" else "REPLICATE_API_TOKEN"
    api_key = args.api_key or os.environ.get(env_var)
    if not api_key:
        print(f"Error: provide --api-key or set {env_var} env var.", file=sys.stderr)
        sys.exit(1)

    # Ensure output directories exist
    for path in args.outputs:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    if args.provider == "fal":
        enhance_fal(
            api_key, args.prompt, args.images, args.outputs,
            args.aspect_ratio, args.resolution,
        )
    else:
        enhance_replicate(
            api_key, args.prompt, args.images, args.outputs,
            args.aspect_ratio,
        )


if __name__ == "__main__":
    main()
