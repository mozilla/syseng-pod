import os
from enum import StrEnum

import click

SEMVER_UPDATE_TYPE_PREFIX = "version-update:semver-"


class SemverUpdateType(StrEnum):
    major = f"{SEMVER_UPDATE_TYPE_PREFIX}major"
    minor = f"{SEMVER_UPDATE_TYPE_PREFIX}minor"
    patch = f"{SEMVER_UPDATE_TYPE_PREFIX}patch"


class DependencyType(StrEnum):
    development = "direct:development"
    production = "direct:production"
    indirect = "indirect"


def set_output(outputs):
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for name, value in outputs.items():
            f.write(f"{name}={value}\n")


def parse_semver_update_type(ctx, option, value):
    return SemverUpdateType(value)


def parse_dependency_type(ctx, option, value):
    return DependencyType(value)


def parse_semver_autoapprovals(ctx, option, value):
    try:
        return [
            SemverUpdateType(SEMVER_UPDATE_TYPE_PREFIX + v.strip())
            for v in value.split(",")
        ]
    except ValueError:
        message = (
            "format must be a comma-separated list of semver values, e.g. "
            f"{','.join([e.name for e in SemverUpdateType])}"
        )
        raise click.BadParameter(message)


approval_message_template = (
    "The `{semver_level}` update of this `{dependency_type}` "
    "dependency was automatically approved."
)
denial_message_template = (
    "The `{semver_level}` update of this `{dependency_type}` "
    "dependency was not automatically approved. For `{dependency_type}` dependencies, "
    "these semver updates can be automatically approved: {auto_approvals}"
)


def review_pr(
    *,
    dependency_type: DependencyType,
    semver_level: SemverUpdateType,
    prod_semver_autoapprovals: list[SemverUpdateType],
    dev_semver_autoapprovals: list[SemverUpdateType],
) -> tuple[bool, str]:
    # There's not an easy way to determine which direct dependencies an indirect
    # dependency will affect through the metadata provided by Dependabot. An
    # indirect dependency could be used by a production dependency, development
    # dependency, or both. We could possibly find out which dependencies are affected
    # by other means, but for now, the simple option is to just not automatically
    # approve indirect updates.
    if dependency_type == DependencyType.indirect:
        message = (
            "This `indirect` dependency was not automatically approved. Only `direct` "
            "dependencies may be automatically approved."
        )
        return (False, message)

    auto_approvals = (
        prod_semver_autoapprovals
        if dependency_type == DependencyType.production
        else dev_semver_autoapprovals
    )
    should_approve = semver_level in auto_approvals
    message = (
        approval_message_template.format(
            semver_level=semver_level.name,
            dependency_type=dependency_type.name,
        )
        if should_approve
        else denial_message_template.format(
            semver_level=semver_level.name,
            dependency_type=dependency_type.name,
            auto_approvals=", ".join((f"`{level.name}`" for level in auto_approvals)),
        )
    )
    return should_approve, message


@click.command()
@click.option(
    "--semver-level",
    type=click.Choice([e.value for e in SemverUpdateType]),
    callback=parse_semver_update_type,
)
@click.option(
    "--dependency-type",
    type=click.Choice([e.value for e in DependencyType]),
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
