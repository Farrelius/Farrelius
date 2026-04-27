#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_stats.py
Produces:
  stats.svg     — language donut chart card
  top-repo.svg  — top repository widget (by stars)
  header.svg    — animated decipher header (static fallback if already exists)
"""

import os
import sys
import math
import datetime
import requests

# ── Config ──────────────────────────────────────────────────────────────────
USERNAME  = "Farrelius"
TOKEN     = os.environ.get("GH_TOKEN", "")
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
GREEN  = "#3fb950"
TEXT   = "#c9d1d9"
MUTED  = "#8b949e"
DIM    = "#30363d"
TRACK  = "#1c2128"
FONT   = "'JetBrains Mono','Fira Code','Courier New',monospace"

LANG_COLORS = ["#58a6ff","#3fb950","#d2a8ff","#ffa657","#ff7b72"]


# ═══════════════════════════════════════════════════════════════════════════
# GitHub API helpers
# ═══════════════════════════════════════════════════════════════════════════

def fetch_repos() -> list[dict]:
    try:
        r = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS, params={"per_page": 100}, timeout=12,
        )
        r.raise_for_status()
        return [repo for repo in r.json() if not repo.get("fork")]
    except Exception as exc:
        print(f"[warn] repos fetch failed: {exc}", file=sys.stderr)
        return []


def fetch_language_breakdown(repos: list[dict]) -> dict[str, float]:
    try:
        lang_bytes: dict[str, int] = {}
        for repo in repos:
            lr = requests.get(repo["languages_url"], headers=HEADERS, timeout=10)
            if lr.status_code != 200:
                continue
            for lang, count in lr.json().items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + count
        if not lang_bytes:
            raise ValueError("empty")
        total = sum(lang_bytes.values())
        top   = sorted(lang_bytes, key=lambda k: lang_bytes[k], reverse=True)[:MAX_LANGS]
        return {lang: round(lang_bytes[lang] / total * 100, 1) for lang in top}
    except Exception as exc:
        print(f"[warn] language breakdown failed: {exc}", file=sys.stderr)
        return {"Python": 42.0, "JavaScript": 28.5, "TypeScript": 15.3, "PHP": 9.2, "Dart": 5.0}


def fetch_commit_stats() -> dict:
    try:
        repos = fetch_repos()
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)

        year = datetime.datetime.utcnow().year
        sr = requests.get(
            "https://api.github.com/search/commits",
            headers={**HEADERS, "Accept": "application/vnd.github.cloak-preview+json"},
            params={"q": f"author:{USERNAME} committer-date:{year}-01-01..{year}-12-31",
                    "per_page": 1},
            timeout=12,
        )
        total_commits = "—"
        if sr.status_code == 200:
            tc = sr.json().get("total_count", "—")
            total_commits = f"{tc}+" if isinstance(tc, int) and tc > 9999 else str(tc)

        er = requests.get(
            f"https://api.github.com/users/{USERNAME}/events",
            headers=HEADERS, params={"per_page": 100}, timeout=12,
        )
        active_day = "—"
        if er.status_code == 200:
            day_counts: dict[str, int] = {}
            for ev in er.json():
                if ev.get("type") == "PushEvent":
                    created = ev.get("created_at", "")
                    if created:
                        dt  = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                        day = dt.strftime("%A")
                        day_counts[day] = day_counts.get(day, 0) + 1
            if day_counts:
                active_day = max(day_counts, key=lambda k: day_counts[k])[:3].upper()

        return {"commits": total_commits, "stars": str(total_stars), "peak·day": active_day}

    except Exception as exc:
        print(f"[warn] commit stats failed: {exc}", file=sys.stderr)
        return {"commits": "—", "stars": "—", "peak·day": "—"}


def fetch_top_repo() -> dict:
    """Return the repo with the most stars."""
    try:
        repos = fetch_repos()
        if not repos:
            raise ValueError("no repos")
        top = max(repos, key=lambda r: r.get("stargazers_count", 0))
        # Primary language
        lr = requests.get(top["languages_url"], headers=HEADERS, timeout=10)
        lang_bytes = lr.json() if lr.status_code == 200 else {}
        top_lang = max(lang_bytes, key=lambda k: lang_bytes[k]) if lang_bytes else "—"
        return {
            "name":        top.get("name", "—"),
            "stars":       top.get("stargazers_count", 0),
            "forks":       top.get("forks_count", 0),
            "lang":        top_lang,
            "description": (top.get("description") or "no description")[:52],
            "url":         top.get("html_url", ""),
        }
    except Exception as exc:
        print(f"[warn] top repo fetch failed: {exc}", file=sys.stderr)
        return {"name": "elry", "stars": 0, "forks": 0, "lang": "TypeScript",
                "description": "Privacy-focused personality analysis platform", "url": ""}


# ═══════════════════════════════════════════════════════════════════════════
# SVG helpers
# ═══════════════════════════════════════════════════════════════════════════

def donut(cx: float, cy: float, r: float, thickness: float, pct: float, color: str) -> str:
    c    = 2 * math.pi * r
    dash = c * pct / 100
    gap  = c - dash
    track = (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
             f'fill="none" stroke="{TRACK}" stroke-width="{thickness}"/>')
    arc   = (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
             f'fill="none" stroke="{color}" stroke-width="{thickness}" '
             f'stroke-dasharray="{dash:.2f} {gap:.2f}" stroke-linecap="round" '
             f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>')
    return track + "\n    " + arc


DEFS_SHARED = f"""
    <radialGradient id="glow_tl" cx="0%" cy="0%" r="55%">
      <stop offset="0%"   stop-color="{ACCENT}" stop-opacity="0.09"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow_br" cx="100%" cy="100%" r="55%">
      <stop offset="0%"   stop-color="{GREEN}" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="{GREEN}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
      <stop offset="0%"   stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.55"/>
    </radialGradient>
    <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="{BG}"    stop-opacity="1"/>
      <stop offset="25%"  stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="75%"  stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{BG}"    stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="divider_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="{BORDER}" stop-opacity="0"/>
      <stop offset="20%"  stop-color="{BORDER}" stop-opacity="1"/>
      <stop offset="80%"  stop-color="{BORDER}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{BORDER}" stop-opacity="0"/>
    </linearGradient>
"""


# ── stats.svg ────────────────────────────────────────────────────────────────
def build_stats_svg(langs: dict[str, float], commit_stats: dict) -> str:
    W, HEADER_H, DONUT_H, INFO_H = 620, 75, 200, 80
    H         = HEADER_H + DONUT_H + INFO_H
    GRID_STEP = 28
    R, THK    = 38.0, 11.0
    n         = len(langs)

    vcols = "\n      ".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>'
                            for x in range(0, W + 1, GRID_STEP))
    hrows = "\n      ".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>'
                            for y in range(0, H + 1, GRID_STEP))

    pad     = 52
    spacing = (W - 2 * pad) / n
    cy      = HEADER_H + 50 + R + 4
    centers = [(pad + spacing * i + spacing / 2, cy) for i in range(n)]

    donuts_svg = ""
    for i, (lang, pct) in enumerate(langs.items()):
        cx, cy_i = centers[i]
        color = LANG_COLORS[i % len(LANG_COLORS)]
        short = lang[:10] + ("." if len(lang) > 10 else "")
        donuts_svg += (
            f'\n    <text x="{cx:.1f}" y="{cy_i - R - 16:.1f}" text-anchor="middle" '
            f'fill="{color}" font-size="10" font-weight="700" letter-spacing="1">{short}</text>'
            f'\n    ' + donut(cx, cy_i, R, THK, pct, color) +
            f'\n    <text x="{cx:.1f}" y="{cy_i + 1:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{TEXT}" font-size="10.5" font-weight="700">{pct}%</text>'
            f'\n    <circle cx="{cx:.1f}" cy="{cy_i + R + 13:.1f}" r="2.5" fill="{color}" opacity="0.55"/>'
        )

    section_y = HEADER_H + DONUT_H
    info_y    = section_y + 40
    i_step    = W / (len(commit_stats) + 1)
    info_svg  = ""
    for idx, (label, val) in enumerate(commit_stats.items()):
        ix = i_step * (idx + 1)
        vc = GREEN if idx == 0 else ACCENT
        info_svg += (
            f'\n    <text x="{ix:.1f}" y="{info_y - 10:.1f}" text-anchor="middle" '
            f'fill="{vc}" font-size="19" font-weight="700">{val}</text>'
            f'\n    <text x="{ix:.1f}" y="{info_y + 12:.1f}" text-anchor="middle" '
            f'fill="{MUTED}" font-size="8.5" letter-spacing="2.5">{label.upper()}</text>'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>text {{ font-family: {FONT}; }}</style>
    {DEFS_SHARED}
    <clipPath id="card"><rect width="{W}" height="{H}" rx="14"/></clipPath>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{BG}"/>
    <g stroke="{GRID}" stroke-width="0.5" opacity="0.65">
      {vcols}
      {hrows}
    </g>
    <rect width="{W}" height="{H}" fill="url(#glow_tl)"/>
    <rect width="{W}" height="{H}" fill="url(#glow_br)"/>
    <rect width="{W}" height="{H}" fill="url(#vignette)"/>
    <rect width="{W}" height="{H}" rx="14" fill="none" stroke="{BORDER}" stroke-width="1"/>
    <rect x="80" y="0" width="{W - 160}" height="1.2" fill="url(#shimmer)" opacity="0.85"/>
    <text x="32" y="30" fill="{ACCENT}" font-size="11.5" letter-spacing="4" font-weight="700">0x456C72687961</text>
    <text x="32" y="50" fill="{MUTED}" font-size="9" letter-spacing="3">LANGUAGE · DISTRIBUTION · FARRELIUS</text>
    <line x1="32" y1="{HEADER_H - 4}" x2="{W - 32}" y2="{HEADER_H - 4}" stroke="url(#divider_grad)" stroke-width="0.8"/>
    {donuts_svg}
    <line x1="32" y1="{section_y}" x2="{W - 32}" y2="{section_y}" stroke="url(#divider_grad)" stroke-width="0.8"/>
    {info_svg}
    <text x="{W - 20}" y="{H - 11}" fill="{DIM}" font-size="8" text-anchor="end" letter-spacing="1.5" opacity="0.7">AUTO · UPDATED · 12H</text>
  </g>
</svg>"""


# ── top-repo.svg ─────────────────────────────────────────────────────────────
def build_top_repo_svg(repo: dict) -> str:
    W, H      = 300, 150
    GRID_STEP = 20

    vcols = "\n      ".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>'
                            for x in range(0, W + 1, GRID_STEP))
    hrows = "\n      ".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>'
                            for y in range(0, H + 1, GRID_STEP))

    name  = repo["name"][:22]
    desc  = repo["description"][:44]
    stars = repo["stars"]
    forks = repo["forks"]
    lang  = repo["lang"]

    # Language dot colour — try to match our palette heuristically
    lang_color_map = {
        "python": "#3fb950", "javascript": "#ffa657", "typescript": "#58a6ff",
        "php": "#d2a8ff", "dart": "#58a6ff", "go": "#79c0ff",
        "rust": "#ff7b72", "css": "#d2a8ff", "html": "#ff7b72",
    }
    lang_color = lang_color_map.get(lang.lower(), "#8b949e")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>text {{ font-family: {FONT}; }}</style>
    <radialGradient id="repo_glow" cx="0%" cy="0%" r="70%">
      <stop offset="0%"   stop-color="{ACCENT}" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="repo_vig" cx="50%" cy="50%" r="75%">
      <stop offset="0%"   stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.5"/>
    </radialGradient>
    <linearGradient id="repo_shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%"   stop-color="{BG}"    stop-opacity="1"/>
      <stop offset="40%"  stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="60%"  stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="100%" stop-color="{BG}"    stop-opacity="1"/>
    </linearGradient>
    <clipPath id="repo_card"><rect width="{W}" height="{H}" rx="12"/></clipPath>
  </defs>
  <g clip-path="url(#repo_card)">
    <rect width="{W}" height="{H}" fill="{BG}"/>
    <g stroke="{GRID}" stroke-width="0.5" opacity="0.6">
      {vcols}
      {hrows}
    </g>
    <rect width="{W}" height="{H}" fill="url(#repo_glow)"/>
    <rect width="{W}" height="{H}" fill="url(#repo_vig)"/>
    <rect width="{W}" height="{H}" rx="12" fill="none" stroke="{BORDER}" stroke-width="1"/>
    <!-- shimmer top -->
    <rect x="30" y="0" width="{W - 60}" height="1" fill="url(#repo_shimmer)" opacity="0.8"/>
    <!-- label -->
    <text x="20" y="26" fill="{MUTED}" font-size="8" letter-spacing="2.5">TOP · REPOSITORY</text>
    <!-- repo name -->
    <text x="20" y="50" fill="{ACCENT}" font-size="14" font-weight="700" letter-spacing="0.5">{name}</text>
    <!-- description -->
    <text x="20" y="68" fill="{MUTED}" font-size="9">{desc}</text>
    <!-- divider -->
    <line x1="20" y1="80" x2="{W - 20}" y2="80" stroke="{BORDER}" stroke-width="0.7"/>
    <!-- lang dot + label -->
    <circle cx="20" cy="101" r="4" fill="{lang_color}"/>
    <text x="30" y="102" fill="{TEXT}" font-size="9" dominant-baseline="middle">{lang}</text>
    <!-- star icon (★) -->
    <text x="130" y="102" fill="{MUTED}" font-size="9" dominant-baseline="middle">★</text>
    <text x="144" y="102" fill="{TEXT}" font-size="9" dominant-baseline="middle">{stars}</text>
    <!-- fork icon -->
    <text x="175" y="102" fill="{MUTED}" font-size="9" dominant-baseline="middle">⑂</text>
    <text x="189" y="102" fill="{TEXT}" font-size="9" dominant-baseline="middle">{forks}</text>
    <!-- bottom label -->
    <text x="{W - 16}" y="{H - 11}" fill="{DIM}" font-size="7.5" text-anchor="end"
          letter-spacing="1.5" opacity="0.7">AUTO · UPDATED · 12H</text>
  </g>
</svg>"""


# ── header.svg (decipher animation) ──────────────────────────────────────────
def build_header_svg() -> str:
    """
    Animated SVG — each character deciphers from random glyphs to its true value.
    Safe for GitHub (pure SVG SMIL, no JS, no CSS animation).
    """
    CHARS   = "0x456C72687961 — Farrelius"
    GLYPHS  = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#@!%&*<>?/\\"
    W, H    = 520, 72
    FONT_SZ = 17
    CHAR_W  = 13       # monospace character width estimate
    START_X = (W - len(CHARS) * CHAR_W) / 2
    Y       = 40
    TOTAL   = 2.6      # total animation seconds
    STEPS   = 8        # random glyph frames before settling
    import random, hashlib

    def stable_random(seed: str, choices: str) -> list[str]:
        """Deterministic random glyphs based on character seed."""
        result = []
        for i in range(STEPS):
            h = int(hashlib.md5(f"{seed}{i}".encode()).hexdigest(), 16)
            result.append(choices[h % len(choices)])
        return result

    # Build per-character <text> with <animate> for values
    chars_svg = ""
    for idx, ch in enumerate(CHARS):
        x      = START_X + idx * CHAR_W
        delay  = idx * (TOTAL / len(CHARS)) * 0.6   # stagger
        dur    = 0.18                                  # each frame duration

        if ch in (" ", "—"):
            # Non-animated spacers
            chars_svg += (
                f'\n  <text x="{x:.1f}" y="{Y}" fill="{MUTED}" '
                f'font-size="{FONT_SZ}" font-family="{FONT}" '
                f'text-anchor="middle">{ch}</text>'
            )
            continue

        rands  = stable_random(f"{idx}{ch}", GLYPHS)
        values = ";".join(rands) + f";{ch}"   # frames → true char
        key_times = ";".join(
            f"{(delay + i * dur) / TOTAL:.3f}" for i in range(STEPS)
        ) + f";{min((delay + STEPS * dur) / TOTAL, 0.98):.3f}"

        # Color animates: accent → TEXT
        fill_vals = f"{ACCENT};" * STEPS + TEXT

        chars_svg += f"""
  <text x="{x:.1f}" y="{Y}" font-size="{FONT_SZ}" font-family="{FONT}" text-anchor="middle">
    <animate attributeName="fill" values="{fill_vals}" keyTimes="{key_times};1"
             dur="{TOTAL}s" begin="0s" fill="freeze" repeatCount="1"/>
    <animate attributeName="textContent" values="{values}" keyTimes="{key_times}"
             dur="{TOTAL}s" begin="0s" fill="freeze" repeatCount="1"
             calcMode="discrete"/>
    {ch}
  </text>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <radialGradient id="hdr_glow" cx="50%" cy="50%" r="60%">
      <stop offset="0%"   stop-color="{ACCENT}" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{BG}" rx="10"/>
  <rect width="{W}" height="{H}" fill="url(#hdr_glow)"/>
  <!-- shimmer baseline -->
  <line x1="60" y1="{H - 6}" x2="{W - 60}" y2="{H - 6}"
        stroke="{BORDER}" stroke-width="0.7"/>
  {chars_svg}
</svg>"""


# ═══════════════════════════════════════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════════════════════════════════════
def write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"[done] → {path}")


def main() -> None:
    print("[info] Fetching repos…")
    repos = fetch_repos()

    print("[info] Building language breakdown…")
    langs = fetch_language_breakdown(repos)

    print("[info] Fetching commit stats…")
    commit_stats = fetch_commit_stats()

    print("[info] Fetching top repo…")
    top_repo = fetch_top_repo()

    print(f"[info] langs={langs}")
    print(f"[info] commit_stats={commit_stats}")
    print(f"[info] top_repo={top_repo['name']}")

    write("stats.svg",    build_stats_svg(langs, commit_stats))
    write("top-repo.svg", build_top_repo_svg(top_repo))
    write("header.svg",   build_header_svg())


if __name__ == "__main__":
    main()