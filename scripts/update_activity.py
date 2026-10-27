#!/usr/bin/env python3
"""Membuat assets/activity.svg dari aktivitas publik GitHub (hanya stdlib)."""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from svgkit import BLUE, GREEN, MUTED, ORANGE, RED, TEXT, VIOLET, fit, pad, terminal

ROOT = Path(__file__).resolve().parent.parent
USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Sekyurass"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAX_ROWS = 6
LINE_LIMIT = 96


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-readme-activity",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def first_line(text):
    text = (text or "").strip()
    return text.splitlines()[0].strip() if text else ""


def describe(ev):
    t, p = ev.get("type"), ev.get("payload", {}) or {}
    full = ev["repo"]["name"]
    repo = full.split("/")[-1]
    base = {"date": ev["created_at"][:10], "repo": repo, "full": full}
    if t == "PushEvent":
        branch = (p.get("ref") or "").replace("refs/heads/", "")
        return {**base, "verb": "push", "color": GREEN, "detail": f"ke {branch}", "head": p.get("head")}
    if t == "PullRequestEvent":
        pr = p.get("pull_request", {}) or {}
        action = "merged" if p.get("action") == "closed" and pr.get("merged") else p.get("action", "")
        return {**base, "verb": "pr", "color": VIOLET, "detail": f"{action}: {pr.get('title', '')}"}
    if t == "IssuesEvent":
        return {**base, "verb": "issue", "color": ORANGE,
                "detail": f"{p.get('action', '')}: {(p.get('issue') or {}).get('title', '')}"}
    if t == "IssueCommentEvent":
        return {**base, "verb": "komentar", "color": ORANGE, "detail": (p.get("issue") or {}).get("title", "")}
    if t == "CreateEvent":
        return {**base, "verb": "create", "color": BLUE,
                "detail": f"{p.get('ref_type', '')} {p.get('ref') or ''}".strip()}
    if t == "WatchEvent":
        return {**base, "verb": "star", "color": ORANGE, "detail": "memberi bintang"}
    if t == "ForkEvent":
        return {**base, "verb": "fork", "color": BLUE, "detail": "membuat fork"}
    if t == "ReleaseEvent":
        return {**base, "verb": "rilis", "color": RED, "detail": (p.get("release") or {}).get("tag_name", "")}
    return None


def collect():
    events = api(f"/users/{USER}/events/public?per_page=60")
    rows, seen_push, lookups = [], set(), 0
    for ev in events:
        if ev["repo"]["name"].lower() == f"{USER}/{USER}".lower():
            continue  # abaikan repo profil sendiri
        row = describe(ev)
        if not row:
            continue
        if row["verb"] == "push":
            if row["full"] in seen_push:
                continue
            seen_push.add(row["full"])
            if row.get("head") and lookups < MAX_ROWS:
                lookups += 1
                try:
                    c = api(f"/repos/{row['full']}/commits/{row['head']}")
                    msg = first_line(c["commit"]["message"])
                    if msg:
                        row["detail"] = msg
                except Exception as exc:  # pesan commit hanya pelengkap
                    print("lewati pesan commit:", exc, file=sys.stderr)
        rows.append(row)
        if len(rows) >= MAX_ROWS:
            break
    return rows


def render(rows):
    lines = []
    for r in rows:
        used = 10 + 2 + 8 + 1 + 20 + 1
        lines.append([
            (r["date"] + "  ", MUTED),
            (pad(r["verb"], 8) + " ", r["color"]),
            (pad(r["repo"], 20) + " ", BLUE),
            (fit(r["detail"], LINE_LIMIT - used), TEXT),
        ])
    if not lines:
        lines.append([("belum ada aktivitas publik terbaru", MUTED)])
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    lines.append([(f"# diperbarui {today} (UTC), otomatis lewat GitHub Actions", MUTED)])
    return terminal("~/segara — activity.log", [(f"tail -n {MAX_ROWS} activity.log", lines)],
                    "Aktivitas GitHub publik terbaru")


def main():
    rows = [] if "--empty" in sys.argv else collect()
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "activity.svg").write_text(render(rows), encoding="utf-8")
    print(f"activity.svg ditulis ({len(rows)} baris)")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"Gagal memanggil GitHub API: {exc}", file=sys.stderr)
        sys.exit(1)
