#!/usr/bin/env python3
"""
scripts/build.py - Static Site Generator for GitHub Pages & Local Distribution
Copies assets, validates JSON files, and packages dist/ for zero-configuration hosting.
"""

import json
import shutil
import sys
from pathlib import Path


def build(dist_dir: str = "dist", root_dir: str = "."):
    root = Path(root_dir).resolve()
    dist = Path(dist_dir).resolve()

    print(f"Building AMA Archive for GitHub Pages -> {dist}")

    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)

    threads_path = root / "assets" / "data" / "threads.json"
    if not threads_path.exists():
        print(f"Error: Registry missing at {threads_path}", file=sys.stderr)
        sys.exit(1)

    try:
        threads = json.loads(threads_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error parsing {threads_path}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(threads)} registered AMA thread(s).")
    total_answers = 0

    for t in threads:
        thread_file = root / t.get("file", f"assets/data/{t['id']}.json")
        if not thread_file.exists():
            print(f"Error: Thread file {thread_file} does not exist.", file=sys.stderr)
            sys.exit(1)
        data = json.loads(thread_file.read_text(encoding="utf-8"))
        ans_count = len(data.get("items", []))
        total_answers += ans_count
        print(f" - [{t['id']}] {t.get('guest_name')} ({t.get('subreddit')}) -> {ans_count} answers")

    assets_src = root / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, dist / "assets")

    index_src = root / "index.html"
    if not index_src.exists():
        print("Error: index.html missing in root directory.", file=sys.stderr)
        sys.exit(1)
    shutil.copy2(index_src, dist / "index.html")

    (dist / ".nojekyll").touch()

    print("Build complete successfully.")
    print(f"Total Threads: {len(threads)} | Total Answers: {total_answers}")
    print(f"Deploy directory ready: {dist}")

if __name__ == "__main__":
    build()
