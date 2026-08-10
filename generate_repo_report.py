#!/usr/bin/env python3
import sys
import json
import argparse
import datetime
import urllib.parse
from collections import defaultdict

TODAY = datetime.date.today().isoformat()


def load_repos(path):
    with open(path) as f:
        return json.load(f)


def org_label(org):
    if org == "(unknown)":
        return org
    return "[%s](https://github.com/%s)" % (org, org)


def count_label(org, org_repos):
    full_name = org_repos[0].get("full_name") or ""
    mirror_org = full_name.split("/", 1)[0] if "/" in full_name else None
    count = len(org_repos)

    if not mirror_org:
        return "**%s**" % count

    query = urllib.parse.quote_plus('mirror:false fork:false archived:false "%s."' % org)
    url = "https://github.com/orgs/%s/repositories?q=%s" % (mirror_org, query)
    return "[**%s**](%s)" % (count, url)


def percent_deleted_label(org, org_repos, org_totals):
    deleted_count = len(org_repos)
    current_repos = org_totals.get(org) or 0

    total = current_repos + deleted_count
    if total == 0:
        return "—"

    return "%.1f%%" % (deleted_count / total * 100)


def deleted_on_label(deleted_on):
    if not deleted_on or deleted_on == TODAY:
        return None

    deleted_date = datetime.date.fromisoformat(deleted_on) - datetime.timedelta(days=1)
    return deleted_date.isoformat()


def build_report(repos, org_totals):
    by_org = defaultdict(list)
    for r in repos:
        org = r.get("org") or "(unknown)"
        by_org[org].append(r)

    sorted_orgs = sorted(by_org.items(), key=lambda kv: len(kv[1]), reverse=True)

    lines = []
    lines.append("# Deleted UK Government code repositories")
    lines.append("")
    lines.append("Total deleted repositories: **%s**" % len(repos))
    lines.append("Organisations affected: **%s**" % len(sorted_orgs))
    lines.append("")
    lines.append("See [RECENTLY_DELETED.md](RECENTLY_DELETED.md) for the most recently deleted repositories.")
    lines.append("")
    lines.append("| Organisation | Deleted Repos | % Deleted |")
    lines.append("| --- | ---: | ---: |")
    for org, org_repos in sorted_orgs:
        lines.append(
            "| %s | %s | %s |"
            % (org_label(org), count_label(org, org_repos), percent_deleted_label(org, org_repos, org_totals))
        )
    lines.append("")

    for org, org_repos in sorted_orgs:
        lines.append("## %s (%s)" % (org_label(org), len(org_repos)))
        lines.append("")
        lines.append("| Repository | Description | Deleted On |")
        lines.append("| --- | --- | --- |")
        for r in sorted(org_repos, key=lambda x: x.get("deleted_on") or "", reverse=True):
            name = r.get("name") or r.get("mirror_name")
            url = r.get("mirror_url")
            description = r.get("description") or ""

            repo_label = "[`%s`](%s)" % (name, url) if url else "`%s`" % name
            deleted_on = deleted_on_label(r.get("deleted_on")) or ""

            lines.append("| %s | %s | %s |" % (repo_label, description, deleted_on))
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to the JSON file produced by fetch_source_repos.py")
    parser.add_argument(
        "--org-counts",
        default="org_repo_counts.json",
        help="Path to the org repo counts JSON file produced by fetch_source_repos.py",
    )
    parser.add_argument("-o", "--output", default="deleted_repos_report.md", help="Output markdown file path")
    args = parser.parse_args()

    repos = load_repos(args.input)
    org_totals = load_repos(args.org_counts)
    report = build_report(repos, org_totals)

    with open(args.output, "w") as f:
        f.write(report)

    print("Wrote report to %s" % args.output, file=sys.stderr)


if __name__ == "__main__":
    main()
