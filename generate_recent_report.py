#!/usr/bin/env python3
import sys
import json
import argparse
import datetime

TODAY = datetime.date.today().isoformat()
LIMIT = 1000


def load_repos(path):
    with open(path) as f:
        return json.load(f)


def org_label(org):
    if not org:
        return "(unknown)"
    return "[%s](https://github.com/%s)" % (org, org)


def deleted_on_label(deleted_on):
    if not deleted_on or deleted_on == TODAY:
        return None

    deleted_date = datetime.date.fromisoformat(deleted_on) - datetime.timedelta(days=1)
    return deleted_date.isoformat()


def build_report(repos):
    dated = [r for r in repos if r.get("deleted_on") and r.get("deleted_on") != TODAY]
    recent = sorted(dated, key=lambda r: r.get("deleted_on"), reverse=True)[:LIMIT]

    lines = []
    lines.append("# Most recently deleted repositories")
    lines.append("")
    lines.append("Showing the %s most recently deleted repositories." % len(recent))
    lines.append("")
    lines.append("| Organisation | Repository | Description | Deleted On |")
    lines.append("| --- | --- | --- | --- |")
    for r in recent:
        org = r.get("org")
        name = r.get("name") or r.get("mirror_name")
        url = r.get("mirror_url")
        description = r.get("description") or ""

        repo_label = "[`%s`](%s)" % (name, url) if url else "`%s`" % name
        deleted_on = deleted_on_label(r.get("deleted_on")) or ""

        lines.append("| %s | %s | %s | %s |" % (org_label(org), repo_label, description, deleted_on))
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to the JSON file produced by fetch_source_repos.py")
    parser.add_argument("-o", "--output", default="recently_deleted_report.md", help="Output markdown file path")
    args = parser.parse_args()

    repos = load_repos(args.input)
    report = build_report(repos)

    with open(args.output, "w") as f:
        f.write(report)

    print("Wrote report to %s" % args.output, file=sys.stderr)


if __name__ == "__main__":
    main()
