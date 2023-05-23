import os
from enum import StrEnum, auto

import click

UPDATE_TYPE_PREFIX = "version-update:semver-"
DEPENDENCY_TYPE_PREFIX = "direct:"


class DependencyType(StrEnum):
    DEVELOPMENT = auto()
    PRODUCTION = auto()


class SemverLevel(StrEnum):
    MAJOR = auto()
    MINOR = auto()
    PATCH = auto()


def set_output(outputs):
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for name, value in outputs.items():
            f.write(f"{name}={value}\n")


def parse_semver_level(ctx, option, value: str):
    return SemverLevel(value.removeprefix(UPDATE_TYPE_PREFIX))


def parse_dependency_type(ctx, option, value: str):
    return DependencyType(value.removeprefix(DEPENDENCY_TYPE_PREFIX))


def parse_semver_autoapprovals(ctx, option, value):
    try:
        return [SemverLevel(v.strip()) for v in value.split(",")]
    except ValueError:
        raise click.BadParameter(
            f"format must be a comma-separated list of semver values, e.g. {','.join([e.value for e in SemverLevel])}"
        )


approval_message_template = "The {semver_level} update of this {dependency_type} dependency was automatically approved."
denial_message_template = "The {semver_level} update of this {dependency_type} dependency was not automatically approved. For {dependency_type} dependencies, these semver updates can be automatically approved: {auto_approvals}"


def review_pr(
    *,
    dependency_type: DependencyType,
    semver_level: SemverLevel,
    prod_semver_autoapprovals: list[SemverLevel],
    dev_semver_autoapprovals: list[SemverLevel],
) -> tuple[bool, str]:
    auto_approvals = (
        prod_semver_autoapprovals
        if dependency_type == DependencyType.PRODUCTION
        else dev_semver_autoapprovals
    )
    is_semver_allowed = semver_level in auto_approvals
    message = (
        approval_message_template.format(
            semver_level=semver_level, dependency_type=dependency_type
        )
        if is_semver_allowed
        else denial_message_template.format(
            semver_level=semver_level,
            dependency_type=dependency_type,
            auto_approvals=",".join(auto_approvals),
        )
    )
    return is_semver_allowed, message


@click.command()
@click.option(
    "--semver-level",
    type=click.Choice([UPDATE_TYPE_PREFIX + e.value for e in SemverLevel]),
    callback=parse_semver_level,
)
@click.option(
    "--dependency-type",
    type=click.Choice([DEPENDENCY_TYPE_PREFIX + e.value for e in DependencyType]),
    callback=parse_dependency_type,
)
@click.option("--prod-semver-autoapprovals", callback=parse_semver_autoapprovals)
@click.option("--dev-semver-autoapprovals", callback=parse_semver_autoapprovals)
def main(
    semver_level,
    dependency_type,
    prod_semver_autoapprovals,
    dev_semver_autoapprovals,
):
    should_approve, review_message = review_pr(
        dependency_type=dependency_type,
        semver_level=semver_level,
        prod_semver_autoapprovals=prod_semver_autoapprovals,
        dev_semver_autoapprovals=dev_semver_autoapprovals,
    )
    set_output(
        {
            "should-approve": str(should_approve).lower(),
            "review-message": review_message,
        }
    )


if __name__ == "__main__":
    main()
