#!/usr/bin/env python3
"""Generate self-hosted SVGs for the profile README from GitHub contributions."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = "amazing-source"
OUT = Path("assets")


def fetch_calendar() -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN/GITHUB_TOKEN is required")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)
    query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from, to:$to) {
          contributionCalendar {
            totalContributions
            weeks {
              firstDay
              contributionDays { date contributionCount weekday }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": now.isoformat().replace("+00:00", "Z"),
        },
    }).encode()
    req = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "amazing-source-profile",
        },
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_activity(calendar: dict) -> str:
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    days = days[-31:]
    values = [d["contributionCount"] for d in days]

    width, height = 900, 270
    left, right, top, bottom = 45, 18, 48, 42
    plot_w, plot_h = width - left - right, height - top - bottom
    max_v = max(values or [1])
    y_max = max(1, int(math.ceil(max_v / 5.0) * 5))

    def xy(i: int, value: int) -> tuple[float, float]:
        x = left + (plot_w * i / max(1, len(values) - 1))
        y = top + plot_h - (plot_h * value / y_max)
        return x, y

    pts = [xy(i, v) for i, v in enumerate(values)]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = " ".join(
        [f"{left},{top + plot_h}"]
        + [f"{x:.1f},{y:.1f}" for x, y in pts]
        + [f"{left + plot_w},{top + plot_h}"]
    )

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="8" fill="#0d1117"/>',
        '<text x="18" y="28" fill="#f0f6fc" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="15" font-weight="600">ren\'s contribution activity</text>',
        '<text x="882" y="28" text-anchor="end" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="11">last 31 days</text>',
    ]

    for step in range(5):
        y = top + plot_h * step / 4
        label = round(y_max * (1 - step / 4))
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#21262d" stroke-width="1"/>')
        lines.append(f'<text x="{left - 9}" y="{y + 4:.1f}" text-anchor="end" fill="#6e7681" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="10">{label}</text>')

    if pts:
        lines.append(f'<polygon points="{area}" fill="#58a6ff" fill-opacity="0.10"/>')
        lines.append(f'<polyline points="{polyline}" fill="none" stroke="#79c0ff" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in pts:
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#c9d1d9" stroke="#58a6ff" stroke-width="1.2"/>')

    for i, day in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            x, _ = xy(i, 0)
            label = datetime.fromisoformat(day["date"]).strftime("%b %d")
            lines.append(f'<text x="{x:.1f}" y="{height - 15}" text-anchor="middle" fill="#6e7681" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="10">{esc(label)}</text>')

    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def svg_contributions(calendar: dict) -> str:
    weeks = calendar["weeks"]
    width, height = 900, 170
    left, top = 52, 46
    cell, gap = 11, 3
    stride = cell + gap
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0]
    max_count = max(counts or [1])

    def level(count: int) -> int:
        if count <= 0:
            return 0
        return min(4, max(1, math.ceil(4 * count / max_count)))

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="8" fill="#0d1117"/>',
        '<text x="18" y="26" fill="#f0f6fc" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="14" font-weight="600">contributions in the last year</text>',
        f'<text x="882" y="26" text-anchor="end" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="11">{calendar["totalContributions"]} contributions</text>',
    ]

    month_seen: set[tuple[int, int]] = set()
    for wi, week in enumerate(weeks):
        x = left + wi * stride
        for day in week["contributionDays"]:
            dt = datetime.fromisoformat(day["date"])
            if dt.day <= 7 and (dt.year, dt.month) not in month_seen:
                month_seen.add((dt.year, dt.month))
                lines.append(f'<text x="{x}" y="39" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="10">{dt.strftime("%b")}</text>')
            y = top + day["weekday"] * stride
            c = colors[level(day["contributionCount"])]
            lines.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')

    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = top + weekday * stride + cell - 1
        lines.append(f'<text x="42" y="{y}" text-anchor="end" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="9">{label}</text>')

    legend_x = width - 160
    legend_y = height - 18
    lines.append(f'<text x="{legend_x - 7}" y="{legend_y + 9}" text-anchor="end" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="9">Less</text>')
    for i, color in enumerate(colors):
        lines.append(f'<rect x="{legend_x + i * 14}" y="{legend_y}" width="10" height="10" rx="2" fill="{color}"/>')
    lines.append(f'<text x="{legend_x + 76}" y="{legend_y + 9}" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" font-size="9">More</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main() -> None:
    calendar = fetch_calendar()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "activity.svg").write_text(svg_activity(calendar), encoding="utf-8")
    (OUT / "contributions.svg").write_text(svg_contributions(calendar), encoding="utf-8")


if __name__ == "__main__":
    main()
