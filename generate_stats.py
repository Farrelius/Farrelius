#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_stats.py
Generates an elegant stats.svg with per-language donut charts.
Fetches language breakdown from GitHub API with graceful fallback.
"""

import os
import sys
import math
import requests

# ── Config ──────────────────────────────────────────────────────────────────
USERNAME  = "Farrelius"
TOKEN     = os.environ.get("GH_TOKEN", "")
OUTPUT    = "stats.svg"
MAX_LANGS = 5

HEADERS = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
}

# ── Palette ──────────────────────────────────────────────────────────────────
BG     = "#0d1117"
GRID   = "#161b22"
BORDER = "#21262d"
ACCENT = "#58a6ff"
TEXT   = "#c9d1d9"
MUTED  = "#8b949e"
DIM    = "#30363d"
TRACK  = "#1c2128"
FONT   = "'JetBrains Mono','Fira Code','Courier New',monospace"

LANG_COLORS = [
    "#58a6ff",  # cyan-blue
    "#3fb950",  # green
    "#d2a8ff",  # purple
    "#ffa657",  # orange
    "#ff7b72",  # red
]

# ── GitHub API ───────────────────────────────────────────────────────────────
def fetch_language_breakdown() -> dict[str, float]:
    try:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS, params={"per_page": 100}, timeout=12,
        )
        resp.raise_for_status()

        lang_bytes: dict[str, int] = {}
        for repo in resp.json():
            if repo.get("fork"):
                continue
            lr = requests.get(repo["languages_url"], headers=HEADERS, timeout=10)
            if lr.status_code != 200:
                continue
            for lang, count in lr.json().items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + count

        if not lang_bytes:
            raise ValueError("no data")

        total = sum(lang_bytes.values())
        top   = sorted(lang_bytes, key=lambda k: lang_bytes[k], reverse=True)[:MAX_LANGS]
        return {lang: round(lang_bytes[lang] / total * 100, 1) for lang in top}

    except Exception as exc:
        print(f"[warn] Language fetch failed: {exc}", file=sys.stderr)
        return {"Python": 42.0, "JavaScript": 28.5, "TypeScript": 15.3, "PHP": 9.2, "Dart": 5.0}


def fetch_user_stats() -> dict:
    try:
        r = requests.get(f"https://api.github.com/users/{USERNAME}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        d = r.json()
        return {"repos": d.get("public_repos", "—"), "followers": d.get("followers", "—"), "following": d.get("following", "—")}
    except Exception as exc:
        print(f"[warn] User stats failed: {exc}", file=sys.stderr)
        return {"repos": "—", "followers": "—", "following": "—"}


# ── Donut arc ────────────────────────────────────────────────────────────────
def donut(cx: float, cy: float, r: float, thickness: float,
          pct: float, color: str) -> str:
    circumference = 2 * math.pi * r
    dash = circumference * pct / 100
    gap  = circumference - dash
    track = (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="none" stroke="{TRACK}" stroke-width="{thickness}"/>'
    )
    arc = (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="{thickness}" '
        f'stroke-dasharray="{dash:.2f} {gap:.2f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>'
    )
    return track + "\n    " + arc


# ── SVG ──────────────────────────────────────────────────────────────────────
def build_svg(langs: dict[str, float], stats: dict) -> str:
    W             = 620
    DONUT_H       = 230
    INFO_H        = 90
    H             = DONUT_H + INFO_H
    GRID_STEP     = 28
    R             = 38.0
    THICKNESS     = 11.0
    n             = len(langs)

    # Grid
    vcols = "\n      ".join(
        f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>' for x in range(0, W + 1, GRID_STEP))
    hrows = "\n      ".join(
        f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>' for y in range(0, H + 1, GRID_STEP))

    # Donut centres — vertically centred in donut section
    pad      = 52
    spacing  = (W - 2 * pad) / n
    cy       = DONUT_H / 2 + 10   # nudge down slightly for labels above
    centers  = [(pad + spacing * i + spacing / 2, cy) for i in range(n)]

    # Build donut group
    donuts_svg = ""
    for i, (lang, pct) in enumerate(langs.items()):
        cx, cy_i = centers[i]
        color    = LANG_COLORS[i % len(LANG_COLORS)]
        short    = lang[:10] + ("." if len(lang) > 10 else "")

        # Language name above
        donuts_svg += (
            f'\n    <text x="{cx:.1f}" y="{cy_i - R - 18:.1f}" text-anchor="middle" '
            f'fill="{color}" font-size="10" font-weight="700" letter-spacing="1">{short}</text>'
        )
        # Donut ring
        donuts_svg += "\n    " + donut(cx, cy_i, R, THICKNESS, pct, color)
        # Percentage inside
        donuts_svg += (
            f'\n    <text x="{cx:.1f}" y="{cy_i + 1:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{TEXT}" '
            f'font-size="10.5" font-weight="700">{pct}%</text>'
        )
        # Small dot below
        donuts_svg += (
            f'\n    <circle cx="{cx:.1f}" cy="{cy_i + R + 14:.1f}" '
            f'r="2.5" fill="{color}" opacity="0.6"/>'
        )

    # Info row
    info_y   = DONUT_H + 44
    i_step   = W / (len(stats) + 1)
    info_svg = ""
    for idx, (label, val) in enumerate(stats.items()):
        ix = i_step * (idx + 1)
        info_svg += (
            f'\n    <text x="{ix:.1f}" y="{info_y - 12:.1f}" text-anchor="middle" '
            f'fill="{ACCENT}" font-size="20" font-weight="700">{val}</text>'
            f'\n    <text x="{ix:.1f}" y="{info_y + 11:.1f}" text-anchor="middle" '
            f'fill="{MUTED}" font-size="9" letter-spacing="2.5">{label.upper()}</text>'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>text {{ font-family: {FONT}; }}</style>

    <radialGradient id="glow_tl" cx="0%" cy="0%" r="55%">
      <stop offset="0%"   stop-color="{ACCENT}" stop-opacity="0.09"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow_br" cx="100%" cy="100%" r="55%">
      <stop offset="0%"   stop-color="#3fb950" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="#3fb950" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
      <stop offset="0%"   stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.55"/>
    </radialGradient>
    <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="{BG}"     stop-opacity="1"/>
      <stop offset="25%"  stop-color="{ACCENT}"  stop-opacity="1"/>
      <stop offset="75%"  stop-color="{ACCENT}"  stop-opacity="1"/>
      <stop offset="100%" stop-color="{BG}"     stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="divider_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="{BORDER}" stop-opacity="0"/>
      <stop offset="20%"  stop-color="{BORDER}" stop-opacity="1"/>
      <stop offset="80%"  stop-color="{BORDER}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{BORDER}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="card">
      <rect width="{W}" height="{H}" rx="14"/>
    </clipPath>
  </defs>

  <g clip-path="url(#card)">
    <!-- Background -->
    <rect width="{W}" height="{H}" fill="{BG}"/>

    <!-- Grid -->
    <g stroke="{GRID}" stroke-width="0.5" opacity="0.65">
      {vcols}
      {hrows}
    </g>

    <!-- Glows -->
    <rect width="{W}" height="{H}" fill="url(#glow_tl)"/>
    <rect width="{W}" height="{H}" fill="url(#glow_br)"/>
    <rect width="{W}" height="{H}" fill="url(#vignette)"/>

    <!-- Border -->
    <rect width="{W}" height="{H}" rx="14"
          fill="none" stroke="{BORDER}" stroke-width="1"/>

    <!-- Shimmer line at top -->
    <rect x="80" y="0" width="{W - 160}" height="1.2" fill="url(#shimmer)" opacity="0.85"/>

    <!-- Header -->
    <text x="32" y="34"
          fill="{ACCENT}" font-size="11.5" letter-spacing="4" font-weight="700">
      0x456C72687961
    </text>
    <text x="32" y="53"
          fill="{MUTED}" font-size="9" letter-spacing="3">
      LANGUAGE · DISTRIBUTION · FARRELIUS
    </text>

    <!-- Header rule -->
    <line x1="32" y1="63" x2="{W - 32}" y2="63"
          stroke="url(#divider_grad)" stroke-width="0.8"/>

    <!-- Donut charts -->
    {donuts_svg}

    <!-- Section divider -->
    <line x1="32" y1="{DONUT_H}" x2="{W - 32}" y2="{DONUT_H}"
          stroke="url(#divider_grad)" stroke-width="0.8"/>

    <!-- Stats row -->
    {info_svg}

    <!-- Timestamp -->
    <text x="{W - 20}" y="{H - 11}"
          fill="{DIM}" font-size="8" text-anchor="end"
          letter-spacing="1.5" opacity="0.7">AUTO · UPDATED · 12H</text>
  </g>
</svg>
"""


# ── Entry ────────────────────────────────────────────────────────────────────
def main() -> None:
    print("[info] Fetching data…")
    langs = fetch_language_breakdown()
    stats = fetch_user_stats()
    print(f"[info] langs={langs}")
    print(f"[info] stats={stats}")
    svg = build_svg(langs, stats)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print(f"[done] → {OUTPUT}")


if __name__ == "__main__":
    main()