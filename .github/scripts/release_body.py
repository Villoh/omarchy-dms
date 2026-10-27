#!/usr/bin/env python3
"""Print the body of the GitHub release for a tag.

usage: release_body.py TAG [--generated]

The body has two parts:

1. What changed, written for you from the Conventional Commits between the previous tag
   and TAG (feat, fix, docs, ...). Nothing to write per release. If you do want to word a
   release yourself, put it in .github/release-notes/<TAG>.md and that is used instead
   (--generated ignores it, to preview the generated text).
2. The sections every release carries: .github/release-notes/_install.md, where {tag} and
   {version} are replaced.

Needs the git history and tags (checkout with fetch-depth: 0). GITHUB_REPOSITORY, if set,
turns the commit hashes and the changelog line into links.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "release-notes"

# Shown as they are, in this order.
SECTIONS = [
    ("breaking", "Breaking changes"),
    ("feat", "Features"),
    ("fix", "Bug fixes"),
    ("perf", "Performance"),
    ("docs", "Documentation"),
    ("refactor", "Refactoring"),
]
# Collapsed under "Maintenance": real, but rarely what a user reads a release for.
MAINTENANCE = {"build", "ci", "chore", "test", "style", "revert"}
COMMIT_RE = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<subject>.+)$")
SKIP_RE = re.compile(r"^(chore: release|Merge )")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def previous_tag(tag):
    try:
        return git("describe", "--tags", "--abbrev=0", "--match", "v*", f"{tag}^").strip()
    except subprocess.CalledProcessError:
        return None  # the first release


def commits(tag):
    prev = previous_tag(tag)
    out = git("log", "--no-merges", "--format=%H%x1f%s%x1f%b%x1e", f"{prev}..{tag}" if prev else tag)
    rows = []
    for entry in out.split("\x1e"):
        if entry.strip():
            sha, subject, body = entry.strip("\n").split("\x1f", 2)
            rows.append((sha, subject, body))
    return prev, rows


def classify(subject, body):
    """-> (bucket, scope, text); bucket is a conventional type, 'breaking' or 'other'."""
    m = COMMIT_RE.match(subject)
    if not m:
        return "other", None, subject
    breaking = m["bang"] or "BREAKING CHANGE" in body
    return ("breaking" if breaking else m["type"].lower()), m["scope"], m["subject"]


def generated(tag):
    repo = os.environ.get("GITHUB_REPOSITORY")
    prev, rows = commits(tag)
    buckets = {}
    for sha, subject, body in rows:
        if SKIP_RE.match(subject):
            continue
        bucket, scope, text = classify(subject, body)
        short = sha[:7]
        ref = f"[`{short}`](https://github.com/{repo}/commit/{sha})" if repo else f"`{short}`"
        line = f"- {f'**{scope}:** ' if scope else ''}{text} ({ref})"
        buckets.setdefault(bucket, []).append(line)

    out = []
    for key, title in SECTIONS:
        if key in buckets:
            out += [f"### {title}", *buckets.pop(key), ""]
    maintenance = [line for k in sorted(buckets) if k in MAINTENANCE for line in buckets.pop(k)]
    other = [line for k in sorted(buckets) for line in buckets[k]]
    if other:
        out += ["### Other changes", *other, ""]
    if maintenance:
        out += ["<details>", "<summary>Maintenance</summary>", "", *maintenance, "", "</details>", ""]
    if not out:
        out = ["No user-facing changes.", ""]
    if repo and prev:
        out.append(f"**Full Changelog**: https://github.com/{repo}/compare/{prev}...{tag}")
    return "\n".join(out).rstrip() + "\n"


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    tag = args[0]
    version = tag.removeprefix("v")
    written = NOTES / f"{tag}.md"
    body = written.read_text() if written.is_file() and "--generated" not in argv else generated(tag)
    fixed = (NOTES / "_install.md").read_text().replace("{tag}", tag).replace("{version}", version)
    print(f"{body.rstrip()}\n\n{fixed.rstrip()}")


if __name__ == "__main__":
    main(sys.argv[1:])
