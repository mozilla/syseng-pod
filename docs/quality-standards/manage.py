#! /usr/bin/env python3
from collections import defaultdict
import datetime
import os
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


@click.group()
def cli():
    pass


@cli.command()
def html():
    with open("criteria.yaml") as f:
        root = ruamel.yaml.load(f, Loader=ruamel.yaml.Loader)

    def render_markdown(value):
        return markdown.markdown(value)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
    )
    env.filters["markdown"] = render_markdown

    template = env.get_template("template.html")
    context = {"standard": root["standard"]}
    rendered = template.render(**context)

    os.makedirs("html", exist_ok=True)
    output = os.path.abspath(os.path.join("html", "index.html"))
    with open(output, "w") as f:
        f.write(rendered)
    click.echo(f"Rendered {output}")


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

    points_for = {
        "Yes": 2,
        "Partially": 1,
        "No": 0,
    }

    max_score = 0
    for category in root["standard"]["categories"]:
        for name in category["rules"].items():
            max_score += points_for["Yes"]

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

        choice = questionary.select(
            message=f"Score card already exists for {service}. Do you want to:",
            choices=[
                {
                    "name": f"Resume last audit ({latest_audit_date}, {last_score}/{max_score})",
                    "value": 1,
                },
                {
                    "name": f"Start new audit from previous (skip compliant checks)",
                    "value": 2,
                },
                {"name": f"Start new audit from scratch", "value": 3},
                {"name": f"Abort", "value": 4},
            ],
        ).ask()

        if choice == 1:
            # The new audit will be saved with today's date.
            del scorecards[service][latest_audit_date]
        if choice == 2:
            previous_audit = {
                rule: v for rule, v in previous_audit.items() if v == "Yes"
            }
        if choice == 4:
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
                choices=points_for.keys(),
                instruction="\n" + rule["description"].strip() + "\n",
            ).ask()
            if compliance is None:
                aborted = True
                break
            # Offer ability to add notes if not compliant.
            notes = ""
            if compliance != "Yes":
                notes = questionary.text(
                    message="Notes?",
                    multiline=True,
                ).ask()
            if notes is None:
                aborted = True
                break
            answers[name] = {
                "compliant": compliance,
                "notes": notes,
            }

    # Compute scores.
    score = sum(points_for[details["compliant"]] for details in answers.values())
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
    click.echo(f"Wrote {scorecards_filename}")


if __name__ == "__main__":
    cli(obj={})
