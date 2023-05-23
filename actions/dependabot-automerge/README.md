# Dependabot Autoapproval and Automerge

This GitHub custom action enables automatic approval and merging of Dependabot pull requests (PRs) based on specified conditions.

## Inputs

- `merge-strategy`: The merge strategy to use when enabling automerge. Possible values are `merge`, `rebase`, and `squash`. Defaults to `squash`.
- `prod-semver-autoapprovals`: Comma-delimited list of semver levels for which to automatically approve the PR for production dependencies. Defaults to `patch`.
- `dev-semver-autoapprovals`: Comma-delimited list of semver levels for which to automatically approve the PR for development dependencies. Defaults to `major,minor,patch`.

## Usage

To use this action, include the following YAML configuration in a workflow file (e.g., `.github/workflows/dependabot_auto_merge.yml`):

```yaml
name: Dependabot auto-merge

on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot-automerge:
    runs-on: ubuntu-latest
    if: ${{ github.actor == 'dependabot[bot]' }}
    steps:
      - name: Enable Dependabot automation
        uses: mozilla/syseng-pod/actions/dependabot-automerge
```

the `contents` and `pull-requests` [token](https://docs.github.com/en/actions/security-guides/automatic-token-authentication) permissions (used by the action) need to be set to `write` so that the automation can leave comments, approve the PR, and enable auto-merge.

## Repo Configuration:

- `Allow Github Actions to create and approve pull requests` should be checked ([docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#preventing-github-actions-from-creating-or-approving-pull-requests))
- the chosen merge strategy should be enabled on the repo ([docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges))
- [Requiring reviews](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-pull-request-reviews-before-merging) from Codeowners should be disabled for files that Dependabot would update (e.g. `poetry.lock`), since bots can't be listed as Codeowners
- It's best to use required status checks with this action (e.g. for linting and tests) and require that those status checks are successful before merging is allowed ([docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging))

## How It Works

- It fetches the metadata of the Dependabot PR
- The action executes the `review_pr.py` script, which reviews the PR and action inputs to determine if it should be automatically approved or not
- The action enables auto-merge on the PR
- If the PR should be approved, the action approves the PR
- If the PR should not be approved, the action adds a comment on the PR explaining why it wasn't approved
