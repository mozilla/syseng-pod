#! /usr/bin/env python3
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

    points_for = {
        "Yes": 2,
        "Partially": 1,
        "No": 0,
    }
    max_score = 0
    score_card = []
    for category in root["standard"]["categories"]:
        for name, rule in category["rules"].items():
            score_card.append(
                {
                    "type": "select",
                    "name": name,
                    "message": f"{name} ?",
                    "choices": points_for.keys(),
                    "instruction": "\n" + rule["description"].strip() + "\n",
                }
            )
            max_score += 2

    answers = questionary.prompt(score_card)

    score = 100 * sum(points_for[v] for v in answers.values()) / max_score
    click.echo(f"Service score is {score}")

    # Save score cards
    yaml = ruamel.yaml.YAML()
    output = f"scorecards-{service}.yaml"
    try:
        with open(output) as existing:
            scorecards = yaml.load(existing)
    except IOError:
        scorecards = {}
    today = datetime.date.today().isoformat()
    scorecards[today] = {
        "score": score,
        "rules": answers,
    }
    with open(output, "w") as out:
        yaml.dump(scorecards, out)
    click.echo(f"Rendered {output}")


if __name__ == "__main__":
    cli(obj={})
