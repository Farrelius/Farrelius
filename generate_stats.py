#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_stats.py
Generates a minimalist stats.svg for Farrelius's GitHub profile README.
Fetches top programming language from GitHub API with fallback support.
"""

import os
import sys
import requests

# ── Config ─────────────────────────────────────────────────────────────────
USERNAME   = "Farrelius"
TOKEN      = os.environ.get("GH_TOKEN", "")
OUTPUT     = "stats.svg"

HEADERS = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
}

# ── Colours / Font ──────────────────────────────────────────────────────────
BG      = "#0d1117"
GRID    = "#161b22"
ACCENT  = "#58a6ff"
DIM     = "#30363d"
TEXT    = "#c9d1d9"
MUTED   = "#8b949e"
FONT    = "'JetBrains Mono', 'Fira Code', 'Courier New', monospace"

# ── Fetch top language ───────────────────────────────────────────────────────
def fetch_top_language() -> str:
    """Return the top programming language across all repos, or a fallback."""
    try:
        url = f"https://api.github.com/users/{USERNAME}/repos"
        resp = requests.get(url, headers=HEADERS, params={"per_page": 100}, timeout=10)
        resp.raise_for_status()
        repos = resp.json()

        lang_bytes: dict[str, int] = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            lang_url = repo.get("languages_url", "")
            if not lang_url:
                continue
            lr = requests.get(lang_url, headers=HEADERS, timeout=10)
            if lr.status_code != 200:
                continue
            for lang, count in lr.json().items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + count

        if not lang_bytes:
            return "Unknown"

        top = max(lang_bytes, key=lambda k: lang_bytes[k])
        total = sum(lang_bytes.values())
        pct = round(lang_bytes[top] / total * 100, 1)
        return f"{top} ({pct}%)"

    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub API unavailable: {exc}", file=sys.stderr)
        return "N/A"


# ── Fetch basic stats ────────────────────────────────────────────────────────
def fetch_user_stats() -> dict:
    """Return public repos, followers, following counts."""
    try:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "repos":     data.get("public_repos", "—"),
            "followers": data.get("followers", "—"),
            "following": data.get("following", "—"),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] User stats unavailable: {exc}", file=sys.stderr)
        return {"repos": "—", "followers": "—", "following": "—"}


# ── SVG builder ──────────────────────────────────────────────────────────────
def build_svg(top_lang: str, stats: dict) -> str:
    W, H = 520, 200
    GRID_STEP = 26

    # Grid columns
    grid_cols = "\n".join(
        f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" />'
        for x in range(0, W + 1, GRID_STEP)
    )
    # Grid rows
    grid_rows = "\n".join(
        f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" />'
        for y in range(0, H + 1, GRID_STEP)
    )

    # Stat row helper (returns three <text> elements)
    def stat_row(label: str, value: str, y: int) -> str:
        return (
            f'<text x="32" y="{y}" fill="{MUTED}" font-size="11">{label}</text>'
            f'<text x="200" y="{y}" fill="{TEXT}" font-size="11" font-weight="600">{value}</text>'
        )

    rows = "\n".join([
        stat_row("top language", top_lang,          94),
        stat_row("public repos", str(stats["repos"]),    118),
        stat_row("followers",    str(stats["followers"]), 142),
        stat_row("following",    str(stats["following"]), 166),
    ])

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>
      text {{
        font-family: {FONT};
        dominant-baseline: middle;
      }}
    </style>
    <!-- subtle vignette -->
    <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
      <stop offset="0%"   stop-color="{BG}"    stop-opacity="0"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.45"/>
    </radialGradient>
  </defs>

  <!-- background -->
  <rect width="{W}" height="{H}" fill="{BG}" rx="10"/>

  <!-- grid -->
  <g stroke="{GRID}" stroke-width="0.6" opacity="0.9">
    {grid_cols}
    {grid_rows}
  </g>

  <!-- vignette overlay -->
  <rect width="{W}" height="{H}" fill="url(#vignette)" rx="10"/>

  <!-- accent top bar -->
  <rect x="0" y="0" width="{W}" height="3" fill="{ACCENT}" rx="2"/>

  <!-- left accent stripe -->
  <rect x="0" y="0" width="3" height="{H}" fill="{ACCENT}" opacity="0.35"/>

  <!-- header -->
  <text x="32" y="44"
        fill="{ACCENT}" font-size="13" letter-spacing="3"
        font-weight="700">0x456C72687961</text>
  <text x="32" y="66"
        fill="{MUTED}" font-size="10" letter-spacing="1.5">GITHUB · FARRELIUS</text>

  <!-- divider -->
  <line x1="32" y1="78" x2="{W - 32}" y2="78" stroke="{DIM}" stroke-width="0.8"/>

  <!-- stats -->
  {rows}

  <!-- bottom timestamp label -->
  <text x="{W - 32}" y="{H - 16}"
        fill="{DIM}" font-size="9" text-anchor="end"
        letter-spacing="1">AUTO · UPDATED · EVERY · 12H</text>
</svg>
"""
    return svg


# ── Entry point ──────────────────────────────────────────────────────────────
def main() -> None:
    print("[info] Fetching stats…")
    top_lang = fetch_top_language()
    stats    = fetch_user_stats()
    print(f"[info] top_lang={top_lang}  stats={stats}")

    svg = build_svg(top_lang, stats)

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)

    print(f"[done] Written → {OUTPUT}")


if __name__ == "__main__":
    main()
