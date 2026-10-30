#!/usr/bin/env python3
import sys
import json
import argparse
import urllib.parse
from collections import defaultdict


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


def deleted_on_display(r):
    deleted_on = r.get("deleted_on") or ""
    if deleted_on and r.get("approximate_date_source"):
        return deleted_on + "*"
    return deleted_on


def deletion_chart(repos):
    by_month = defaultdict(int)
    for r in repos:
        deleted_on = r.get("deleted_on")
        if deleted_on:
            by_month[(int(deleted_on[:4]), int(deleted_on[5:7]))] += 1

    if not by_month:
        return []

    months = []
    year, month = min(by_month)
    while (year, month) <= max(by_month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

    # We only show labels on January because otherwise the graph legend is
    # unreadable, but Mermaid will merge labels with the same name (including
    # null) so we do a truly cursed thing and give each month a unique number
    # of zero-width spaces as a label.
    labels = ", ".join(
        '"%s"' % (year if month == 1 else "\u200b" * (i + 1)) for i, (year, month) in enumerate(months)
    )
    counts = ", ".join(str(by_month[m]) for m in months)

    return [
        "```mermaid",
        "xychart-beta",
        '    title "Repositories deleted per month"',
        "    x-axis [%s]" % labels,
        '    y-axis "Deleted repos"',
        "    bar [%s]" % counts,
        "```",
    ]


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
    chart = deletion_chart(repos)
    if chart:
        lines.extend(chart)
        lines.append("")
    lines.append("Deleted dates with a \\* are approximate, inferred from the last commit or archive.org snapshot. This is the last date we know it was available.")
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
            deleted_on = deleted_on_display(r)

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
