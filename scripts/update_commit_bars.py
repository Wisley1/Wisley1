#!/usr/bin/env python3
"""Refresh the commit bars in README.md from the GitHub contributors API.

Question Graph keeps a fixed personal count of 29. GitHub attributes fewer
commits to this account than that share, so only the repository total moves.
"""

import json
import os
import re
import subprocess
import sys

README = os.path.join(os.path.dirname(__file__), "..", "README.md")
BAR_WIDTH = 20
LOGIN = "Wisley1"

# fixed_mine is kept when GitHub's author count is not the share to show.
REPOS = [
    ("https://github.com/gurinboru/MASDA_Datasets", "gurinboru/MASDA_Datasets", None),
    ("https://github.com/ai-chem/AMP_competition", "ai-chem/AMP_competition", None),
    ("https://github.com/GenerativeMolMachines/DNAzymesGEN", "GenerativeMolMachines/DNAzymesGEN", None),
    ("https://github.com/GenerativeMolMachines/siRNA", "GenerativeMolMachines/siRNA", None),
    ("https://github.com/ai-chem/question-graph", "ai-chem/question-graph", 29),
]


def api_token():
    stats = os.environ.get("STATS_TOKEN", "").strip()
    if stats:
        return stats
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def contributors(repo):
    env = os.environ.copy()
    token = api_token()
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(
        [
            "gh", "api", "--paginate",
            f"repos/{repo}/contributors?anon=1&per_page=100",
            "--jq",
            ".[] | {login: .login, contributions: .contributions}",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().splitlines()
        detail = message[-1] if message else "request failed"
        raise RuntimeError(detail)
    mine = 0
    total = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        count = int(row["contributions"])
        total += count
        if row.get("login") == LOGIN:
            mine = count
    if total <= 0:
        raise RuntimeError("contributor list was empty")
    return mine, total


def bar(mine, total):
    filled = round(BAR_WIDTH * mine / total)
    filled = max(0, min(BAR_WIDTH, filled))
    percent = round(100 * mine / total)
    return "█" * filled + "░" * (BAR_WIDTH - filled), percent


def replace_card(text, url, mine, total):
    pattern = re.compile(
        rf"({re.escape(url)}[\s\S]*?)`[█░]+` \*\*\d+%\*\*\n\n\*\*\d+ of \d+\*\* commits"
    )
    glyphs, percent = bar(mine, total)
    replacement = rf"\1`{glyphs}` **{percent}%**\n\n**{mine} of {total}** commits"
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"card not found for {url}")
    return updated


def main():
    path = os.path.abspath(README)
    text = open(path, encoding="utf-8").read()
    for url, repo, fixed_mine in REPOS:
        try:
            mine, total = contributors(repo)
        except RuntimeError as error:
            print(f"skip {repo}: {error}", file=sys.stderr)
            continue
        if fixed_mine is not None:
            mine = fixed_mine
        text = replace_card(text, url, mine, total)
        print(f"{repo}: {mine} of {total}")
    open(path, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
