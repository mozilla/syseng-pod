#!/usr/bin/env python3
import os
import sys

try:
    from github import Github
except ImportError:
    print("Please install the `PyGithub` package first")
    sys.exit(1)


def main():
    g = Github(os.getenv("TOKEN"))

    repos = [tuple(repo.split("/", 1)) for repo in os.getenv("REPOS").split(",")]

    for owner, name in repos:
        org = g.get_organization(owner)
        repo = org.get_repo(name)
        for pr in repo.get_pulls(state="open"):
            if "dependabot" not in pr.user.login:
                continue

            print(f"{pr.html_url} {pr.title}", end=" ")

            commit = pr.get_commits().reversed[0]
            states = [run.conclusion == "success" for run in commit.get_check_runs()]

            if len(states) == 0:
                status = commit.get_combined_status()
                states = [status.state == "success"]

            if len(states) == 0:
                print("SKIP (no tests)")
                continue

            if not all(states):
                print("SKIP (failing)")
                continue

            check = str(input("(y/N): ")).lower().strip()
            if check != "y":
                continue

            pr.create_review(commit=commit, event="APPROVE")
            print(f"OK")


if __name__ == "__main__":
    # TOKEN=ac6d1f0...dfd REPOS=mozilla-it/ctms-api,mozilla-services/telescope,mozilla/jira-bugzilla-integration python dependabot-approve.py
    main()
