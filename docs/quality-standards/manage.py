#! /usr/bin/env python3
from collections import defaultdict
import datetime
import os
import shutil
import sys

try:
    import click
    import markdown
    import questionary
    import ruamel.yaml
    import jinja2
except ImportError as e:
    print(
        f"Python package(s) missing ({e}). Install them with:\n\npip install -r requirements.txt"
    )
    sys.exit(2)


POINTS_FOR = {
    "Yes": 2,
    "Partially": 1,
    "No": 0,
    "Unknown": 0,
}


@click.group()
def cli():
    pass


@cli.command()
@click.option("-o", "--output", help="Destination folder", default="html")
def html(output):
    with open("criteria.yaml") as f:
        root_criteria = ruamel.yaml.load(f, Loader=ruamel.yaml.Loader)

    with open("scorecards.yaml") as f:
        root_scorecards = ruamel.yaml.load(f, Loader=ruamel.yaml.Loader)

    def render_markdown(value):
        return markdown.markdown(value, extensions=["tables"])

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
    )
    env.filters["markdown"] = render_markdown

    rules_details = {}
    for category in root_criteria["standard"]["categories"]:
        for rule, details in category["rules"].items():
            rules_details[rule] = details

    # Categorize rules and compute max score by category.
    category_for_rule = {}
    max_score_for_category = defaultdict(int)
    for category in root_criteria["standard"]["categories"]:
        for name in category["rules"]:
            category_for_rule[name] = category["title"]
            max_score_for_category[category["title"]] += POINTS_FOR["Yes"]

    # Compute score by category for each score card.
    for service, scorecards in root_scorecards.items():
        for scorecard in scorecards.values():
            score_by_category = defaultdict(int)
            for rule, details in scorecard["rules"].items():
                category = category_for_rule[rule]
                score_by_category[category] += POINTS_FOR[details["compliant"]]
            scorecard["score_by_category"] = score_by_category

    # Compute popularity of each rule.
    total_compliant_by_rule = defaultdict(int)
    compliant_services_by_rule = defaultdict(list)
    for service, scorecards in root_scorecards.items():
        latest_audit_date = max(scorecards.keys())
        scorecard = scorecards[latest_audit_date]
        for rule, details in scorecard["rules"].items():
            points = POINTS_FOR[details["compliant"]]
            total_compliant_by_rule[rule] += points
            if points > 0:
                compliant_services_by_rule[rule].append(service)
    max_points_compliant = POINTS_FOR["Yes"] * len(root_scorecards)
    rules_popularity = {
        rule: {
            "percent": int(total / max_points_compliant * 100),
            "services": compliant_services_by_rule[rule],
        }
        for rule, total in total_compliant_by_rule.items()
    }

    template = env.get_template("template.html")
    context = {
        "standard": root_criteria["standard"],
        "scorecards": root_scorecards,
        "max_score_for_category": max_score_for_category,
        "rules_details": rules_details,
        "rules_popularity": rules_popularity,
        "criteria_last_update": datetime.datetime.fromtimestamp(
            os.path.getmtime("criteria.yaml")
        ),
    }
    rendered = template.render(**context)

    shutil.copytree(
        "assets", os.path.abspath(os.path.join(output, "assets")), dirs_exist_ok=True
    )
    output_index = os.path.abspath(os.path.join(output, "index.html"))
    with open(output_index, "w") as f:
        f.write(rendered)
    click.echo(f"Rendered {output_index}")


@cli.command()
@click.option(
    "--service",
    help="Service name",
)
def audit(service):
    from questionary.prompts.common import print_formatted_text

    criteria = os.path.join(os.path.dirname(__file__), "criteria.yaml")
    with open(criteria) as f:
        root = ruamel.yaml.load(f, Loader=ruamel.yaml.Loader)

    max_score = 0
    for category in root["standard"]["categories"]:
        for name in category["rules"].items():
            max_score += POINTS_FOR["Yes"]

    if not service:
        service = questionary.text(
            "What is the service name?", validate=lambda text: len(text) > 0
        ).ask()
        if service is None:
            sys.exit(1)

    scorecards_filename = f"scorecards.yaml"
    yaml = ruamel.yaml.YAML()
    try:
        with open(scorecards_filename) as existing:
            scorecards = yaml.load(existing) or {}
    except IOError as exc:
        click.echo(exc, err=True)
        scorecards = {}

    previous_audit = {}
    if service in scorecards:
        latest_audit_date = max(scorecards[service].keys())
        last_score = scorecards[service][latest_audit_date]["score"]
        previous_audit = scorecards[service][latest_audit_date]["rules"]
        unknown_count = len(
            [
                v
                for v in scorecards[service][latest_audit_date]["rules"].values()
                if v["compliant"] == "Unknown"
            ]
        )

        choice = questionary.select(
            message=f"Score card already exists for {service}. Do you want to:",
            choices=[
                {
                    "name": f"Resume last audit ({latest_audit_date}, {last_score}/{max_score})",
                    "value": 1,
                },
                {
                    "name": f"Complete {unknown_count} unknown{'s'[:unknown_count^1]} in last audit",
                    "value": 2,
                },
                {
                    "name": f"Start new audit from previous (skip compliant checks)",
                    "value": 3,
                },
                {"name": f"Start new audit from scratch", "value": 4},
                {"name": f"Abort", "value": 5},
            ],
        ).ask()

        if choice == 1:
            # The new audit will be saved with today's date.
            del scorecards[service][latest_audit_date]
        if choice == 2:
            # The new audit will be saved with today's date, and
            # we only keep known answers to prompt again for unknowns.
            del scorecards[service][latest_audit_date]
            previous_audit = {
                rule: v.copy()
                for rule, v in previous_audit.items()
                if v["compliant"] != "Unknown"
            }
        if choice == 3:
            # Equivalent of resuming an audit ignoring all non compliant rules.
            # Note: we copy to avoid ruamel to use anchors.
            previous_audit = {
                rule: v.copy()
                for rule, v in previous_audit.items()
                if v["compliant"] == "Yes"
            }
        if not choice or choice == 5:
            click.echo("Cancelled.")
            sys.exit(1)

    aborted = False
    answers = previous_audit.copy()
    for category in root["standard"]["categories"]:
        # If user aborted one question, we exit the form.
        if aborted:
            break

        shown_intro = False
        for name, rule in category["rules"].items():
            if name in previous_audit:
                # Do not prompt if already answered in previous audit.
                continue

            if not shown_intro:
                print_formatted_text(
                    f"\n\nAbout {category['title']}\n", style="bold ansiwhite"
                )
                if description := category.get("description"):
                    print_formatted_text(description.strip() + "\n...")
                shown_intro = True

            # Prompt for compliance.
            compliance = questionary.select(
                message=f"{name} ?",
                choices=POINTS_FOR.keys(),
                instruction="\n" + rule["description"].strip() + "\n",
            ).ask()
            if not compliance:
                aborted = True
                break
            # Offer ability to add notes if not compliant.
            notes = ""
            if compliance != "Yes":
                notes = questionary.text(
                    message="Notes?",
                    multiline=True,
                ).ask()
            answers[name] = {
                "compliant": compliance,
            }
            if notes is None:
                aborted = True
                break
            elif notes := notes.strip():
                answers[name]["notes"] = notes

    # Compute scores.
    score = sum(POINTS_FOR[details["compliant"]] for details in answers.values())
    score_percent = score * 100 / max_score
    click.echo(f"Service new score is {score_percent:.2f}% ({score}/{max_score})")

    # Save score cards
    today = datetime.date.today().isoformat()
    scorecards.setdefault(service, {})[today] = {
        "version": root["standard"]["version"],
        "score": score,
        "max_score": max_score,
        "rules": answers,
    }
    with open(scorecards_filename, "w") as out:
        yaml.dump(scorecards, out)
    click.echo(f"Wrote {scorecards_filename!r}")


if __name__ == "__main__":
    cli(obj={})
