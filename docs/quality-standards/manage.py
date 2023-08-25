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
    with open("criterias.yaml") as f:
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
def audit():
    criteria = os.path.join(os.path.dirname(__file__), "criterias.yaml")
    with open(criteria) as f:
        root = ruamel.yaml.load(f, Loader=ruamel.yaml.Loader)

    service = questionary.text("What is the service name?").ask()
    output = f"scorecards-{service}.yaml"
    yaml = ruamel.yaml.YAML()
    try:
        with open(output) as existing:
            scorecards = yaml.load(existing)
    except IOError:
        scorecards = {}
    today = datetime.date.today().isoformat()
    if today in scorecards:
        confirmation = f"Score card of {today} already exists for {service}. Overwrite?"
        if not questionary.confirm(confirmation).ask():
            click.echo("Cancelled.")
            sys.exit(1)

    points_for = {
        "Yes": 2,
        "Partially": 1,
        "No": 0,
    }
    max_score = 0
    score_card = []
    for category in root["standard"]["categories"]:
        score_card.append(
            {
                "type": "confirm",
                "name": category["title"],
                "message": f"About {category['title']}",
                "instruction": "\n"
                + category.get("description", "").strip()
                + "\nPress Enter...",
            }
        )
        for name, rule in category["rules"].items():
            score_card.append(
                {
                    "type": "select",
                    "name": f"compliant:{name}",
                    "message": f"{name} ?",
                    "choices": points_for.keys(),
                    "instruction": "\n" + rule["description"].strip() + "\n",
                }
            )
            score_card.append(
                {
                    "type": "text",
                    "name": f"notes:{name}",
                    "message": f"Notes?",
                    "multiline": True,
                }
            )
            max_score += 2

    answers = questionary.prompt(score_card)
    by_rule = defaultdict(dict)
    for name, answer in answers.items():
        if ":" not in name:
            continue
        field, rule = name.split(":")
        if answer := answer.strip():
            by_rule[rule][field] = answer

    score = (
        100
        * sum(points_for[details["compliant"]] for details in by_rule.values())
        / max_score
    )
    click.echo(f"Service score is {score}")

    # Save score cards
    scorecards[today] = {
        "score": score,
        "rules": dict(by_rule),
    }
    with open(output, "w") as out:
        yaml.dump(scorecards, out)
    click.echo(f"Rendered {output}")


if __name__ == "__main__":
    cli(obj={})
