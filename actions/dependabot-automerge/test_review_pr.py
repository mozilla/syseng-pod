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
        # Test for indirect dependency
        (
            "version-update:semver-major",
            "indirect",
            "patch",
            "major",
            False,
            "This `indirect` dependency was not automatically approved. Only `direct` dependencies may be automatically approved.",
        ),
        # Test for development dependency with minor update (approved)
        (
            "version-update:semver-minor",
            "direct:development",
            "patch",
            "major,minor",
            True,
            "The `minor` update of this `development` dependency was automatically approved.",
        ),
        # Test for production dependency with a minor update (denied)
        (
            "version-update:semver-minor",
            "direct:production",
            "patch",
            "major,minor,patch",
            False,
            "The `minor` update of this `production` dependency was not automatically approved. For `production` dependencies, these semver updates can be automatically approved: `patch`",
        ),
        # Add more test cases as needed.
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
    assert parsed_output["should-approve"] == str(should_approve).lower()
    assert review_message == parsed_output["review-message"]


@pytest.mark.parametrize(
    "semver_level, dependency_type, prod_auto_approvals, dev_auto_approvals, error_message",
    [
        # Bad semver level
        (
            "BOOM",
            "indirect",
            "major",
            "major",
            "'BOOM' is not one of 'version-update:semver-major', 'version-update:semver-minor', 'version-update:semver-patch'",
        ),
        # Bad update type
        (
            "version-update:semver-minor",
            "BOOM",
            "major",
            "major",
            "'BOOM' is not one of 'direct:development', 'direct:production', 'indirect'",
        ),
        # Bad semver autoapprovals (prod)
        (
            "version-update:semver-minor",
            "indirect",
            "BOOM",
            "major",
            "format must be a comma-separated list of semver values, e.g. major,minor,patch",
        ),
        # Bad semver autoapprovals (dev)
        (
            "version-update:semver-minor",
            "indirect",
            "major",
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
