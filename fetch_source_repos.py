#!/usr/bin/env python3
import sys
import os
import time
import datetime
import json
import argparse

from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException

RATE_BUFFER = 30
EXTRA_WAIT = 60


def check_rate_limiting(rl):
    remaining, total = rl._requester.rate_limiting

    if remaining < RATE_BUFFER:
        reset_time = rl._requester.rate_limiting_resettime
        reset_time_human = datetime.datetime.fromtimestamp(
            int(reset_time)
        ) + datetime.timedelta(seconds=EXTRA_WAIT)

        print(
            "\nWAITING: Remaining rate limit is %s of %s. Waiting %s mins for reset at %s before continuing.\n"
            % (remaining, total, int((reset_time - time.time()) / 60), reset_time_human),
            file=sys.stderr,
        )

        while time.time() <= (reset_time + EXTRA_WAIT):
            time.sleep(60)
            print(".", end="", file=sys.stderr)

        print("", file=sys.stderr)


def load_previously_deleted(path):
    if not os.path.exists(path):
        return {}

    with open(path) as f:
        previous = json.load(f)

    return {
        entry["mirror_name"]: {
            "deleted_on": entry.get("deleted_on"),
            "approximate_date_source": entry.get("approximate_date_source"),
        }
        for entry in previous
    }


def fetch_org_totals(g, org_names):
    totals = {}
    for name in sorted(org_names):
        while True:
            try:
                source_org = g.get_organization(name)
                check_rate_limiting(source_org)
                totals[name] = source_org.public_repos
                print("* %s has %s public repos" % (name, totals[name]), file=sys.stderr)
                break
            except RateLimitExceededException:
                print("Rate limited, sleeping 60s...", file=sys.stderr)
                time.sleep(60)
            except UnknownObjectException:
                print("* could not look up org %s (renamed or deleted)" % name, file=sys.stderr)
                totals[name] = None
                break

    return totals


def fetch_source_repos(token, org_name, previously_deleted):
    g = Github(token, per_page=100)
    org = g.get_organization(org_name)
    today = datetime.date.today().isoformat()

    results = []
    for repo in org.get_repos(type="sources"):
        while True:
            try:
                check_rate_limiting(repo)
                break
            except RateLimitExceededException:
                print("Rate limited, sleeping 60s...", file=sys.stderr)
                time.sleep(60)

        if "." not in repo.name:
            print("* skipping %s (does not match orgname.reponame)" % repo.full_name, file=sys.stderr)
            continue

        org_part, name = repo.name.split(".", 1)
        if repo.name in previously_deleted:
            deleted_on = previously_deleted[repo.name]["deleted_on"]
            approximate_date_source = previously_deleted[repo.name]["approximate_date_source"]
        else:
            deleted_on = today
            approximate_date_source = None

        entry = {
            "mirror_name": repo.name,
            "full_name": repo.full_name,
            "org": org_part,
            "name": name,
            "description": repo.description,
            "mirror_url": repo.html_url,
            "original_url": "https://github.com/%s/%s" % (org_part, name),
            "deleted_on": deleted_on,
        }
        if approximate_date_source:
            entry["approximate_date_source"] = approximate_date_source
        results.append(entry)
        print("* %s" % repo.full_name, file=sys.stderr)

    org_totals = fetch_org_totals(g, {r["org"] for r in results})
    results.sort(key=lambda r: r["mirror_name"])

    return results, org_totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("org", help="Name of the mirror org to scan")
    parser.add_argument("-o", "--output", default="source_repos.json", help="Output JSON file path")
    parser.add_argument(
        "--org-counts-output",
        default="org_repo_counts.json",
        help="Output JSON file path for each source org's current public repo count",
    )
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("No GITHUB_TOKEN supplied in env", file=sys.stderr)
        sys.exit(1)

    previously_deleted = load_previously_deleted(args.output)
    results, org_totals = fetch_source_repos(token, args.org, previously_deleted)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)

    with open(args.org_counts_output, "w") as f:
        json.dump(org_totals, f, indent=2, sort_keys=True)

    print("Wrote %s source repos to %s" % (len(results), args.output), file=sys.stderr)
    print("Wrote %s org repo counts to %s" % (len(org_totals), args.org_counts_output), file=sys.stderr)


if __name__ == "__main__":
    main()
