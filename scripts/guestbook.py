#!/usr/bin/env python3
"""Guestbook lewat issue. Pesan tampil hanya setelah pemilik repo memberi label 'approved'."""
import datetime
import json
import os
import re
import sys
import textwrap
import urllib.request
from pathlib import Path

from svgkit import BLUE, MUTED, TEXT, VIOLET, terminal

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "guestbook.json"
SVG = ROOT / "assets" / "guestbook.svg"
SHOW = 5
LINE_LIMIT = 96


def sanitize(text, limit):
    text = re.sub(r"[\x00-\x1f\x7f\ufffe\uffff]", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def parse_form(body):
    fields = {}
    for part in re.split(r"^### +", body or "", flags=re.M)[1:]:
        head, _, value = part.partition("\n")
        value = value.strip()
        fields[head.strip()] = "" if value == "_No response_" else value
    return fields


def load():
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def render(entries):
    lines = []
    for e in entries[-SHOW:][::-1]:
        who = e.get("name") or "@" + e.get("user", "tamu")
        prefix = f"[{e['date']}] {who}: "
        width = max(LINE_LIMIT - len(prefix), 30)
        wrapped = textwrap.wrap(e["message"], width=width) or [""]
        lines.append([(f"[{e['date']}] ", MUTED), (who, VIOLET), (": ", MUTED), (wrapped[0], TEXT)])
        for cont in wrapped[1:]:
            lines.append([(" " * len(prefix) + cont, TEXT)])
    if not lines:
        lines.append([("belum ada pesan. jadilah yang pertama!", MUTED)])
    lines.append([("# klik tombol di bawah untuk menulis pesan", MUTED)])
    SVG.parent.mkdir(exist_ok=True)
    SVG.write_text(terminal("~/segara — guestbook.log", [(f"tail -n {SHOW} guestbook.log", lines)],
                            "Guestbook pengunjung profil"), encoding="utf-8")


def gh(method, path, payload=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                 "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-guestbook"},
    )
    urllib.request.urlopen(req, timeout=20).read()


def main():
    if "--render" in sys.argv:
        render(load())
        print("guestbook.svg ditulis")
        return
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    owner = os.environ.get("REPO_OWNER", "").lower()
    if event.get("action") != "labeled" or (event.get("label") or {}).get("name") != "approved":
        return print("bukan label 'approved', dilewati")
    if (event.get("sender") or {}).get("login", "").lower() != owner:
        return print("label tidak diberikan oleh pemilik repo, dilewati")
    issue = event["issue"]
    if not issue["title"].startswith("[Guestbook]"):
        return print("bukan issue guestbook, dilewati")

    entries = load()
    fields = parse_form(issue.get("body"))
    message = sanitize(fields.get("Pesan", ""), 140)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    num = issue["number"]
    if not message:
        return print("pesan kosong, dilewati")
    if not any(e.get("issue") == num for e in entries):
        entries.append({
            "issue": num,
            "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            "user": sanitize(issue["user"]["login"], 39),
            "name": sanitize(fields.get("Nama (opsional)", ""), 30),
            "message": message,
        })
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render(entries)
    try:
        gh("POST", f"/repos/{repo}/issues/{num}/comments", {"body": "Terima kasih! Pesanmu sudah tampil di profil. 🙌"})
        gh("PATCH", f"/repos/{repo}/issues/{num}", {"state": "closed"})
    except Exception as exc:
        print("gagal membalas/menutup issue:", exc, file=sys.stderr)


if __name__ == "__main__":
    main()
