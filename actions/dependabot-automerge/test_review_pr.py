from pathlib import Path

import pytest
import review_pr
from click.testing import CliRunner


@pytest.fixture()
def github_output(monkeypatch, tmp_path):
    output_path = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    return output_path


def parse_output(output: Path):
    return dict(l.split("=") for l in output.read_text().splitlines())


@pytest.mark.parametrize(
    "semver_level, dependency_type, prod_auto_approvals, dev_auto_approvals, should_approve, review_message",
    [
        # Indirect dependency
        (
            "version-update:semver-major",
            "indirect",
            "patch",
            "major,minor,patch",
            "false",
            "This `indirect` dependency was not automatically approved. Only `direct` dependencies may be automatically approved.",
        ),
        # Development dependency with minor update (approved)
        (
            "version-update:semver-minor",
            "direct:development",
            "patch",
            "minor,patch",
            "true",
            "The `minor` update of this `development` dependency was automatically approved.",
        ),
        # Development dependency with major update (denied)
        (
            "version-update:semver-major",
            "direct:development",
            "patch",
            "minor,patch",
            "false",
            "The `major` update of this `development` dependency was not automatically approved. For `development` dependencies, these semver updates can be automatically approved: `minor`, `patch`",
        ),
        # Production dependency with a patch update (approved)
        (
            "version-update:semver-patch",
            "direct:production",
            "patch",
            "major,minor,patch",
            "true",
            "The `patch` update of this `production` dependency was automatically approved.",
        ),
        # Production dependency with a major update (denied)
        (
            "version-update:semver-major",
            "direct:production",
            "patch",
            "major,minor,patch",
            "false",
            "The `major` update of this `production` dependency was not automatically approved. For `production` dependencies, these semver updates can be automatically approved: `patch`",
        ),
    ],
)
def test_main(
    semver_level,
    dependency_type,
    prod_auto_approvals,
    dev_auto_approvals,
    should_approve,
    review_message,
    github_output,
):
    args = [
        "--semver-level",
        semver_level,
        "--dependency-type",
        dependency_type,
        "--prod-semver-autoapprovals",
        prod_auto_approvals,
        "--dev-semver-autoapprovals",
        dev_auto_approvals,
    ]
    runner = CliRunner()
    result = runner.invoke(review_pr.main, args)
    assert result.exit_code == 0

    parsed_output = parse_output(github_output)
    assert parsed_output["should-approve"] == should_approve
    assert parsed_output["review-message"] == review_message


@pytest.mark.parametrize(
    "semver_level, dependency_type, prod_auto_approvals, dev_auto_approvals, error_message",
    [
        # Bad semver level
        (
            "BOOM",
            "indirect",
            "patch",
            "major,minor,patch",
            "'BOOM' is not one of 'version-update:semver-major', 'version-update:semver-minor', 'version-update:semver-patch'",
        ),
        # Bad update type
        (
            "version-update:semver-minor",
            "BOOM",
            "patch",
            "major,minor,patch",
            "'BOOM' is not one of 'direct:development', 'direct:production', 'indirect'",
        ),
        # Bad semver autoapprovals (prod)
        (
            "version-update:semver-minor",
            "indirect",
            "BOOM",
            "major,minor,patch",
            "format must be a comma-separated list of semver values, e.g. major,minor,patch",
        ),
        # Bad semver autoapprovals (dev)
        (
            "version-update:semver-minor",
            "indirect",
            "patch",
            "BOOM",
            "format must be a comma-separated list of semver values, e.g. major,minor,patch",
        ),
    ],
)
def test_main_bad_semver(
    semver_level,
    dependency_type,
    prod_auto_approvals,
    dev_auto_approvals,
    error_message,
):
    args = [
        "--semver-level",
        semver_level,
        "--dependency-type",
        dependency_type,
        "--prod-semver-autoapprovals",
        prod_auto_approvals,
        "--dev-semver-autoapprovals",
        dev_auto_approvals,
    ]
    runner = CliRunner()
    result = runner.invoke(review_pr.main, args)
    assert result.exit_code != 0
    assert error_message in result.output
