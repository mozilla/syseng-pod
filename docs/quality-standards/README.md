# Quality Standards

This folder is the source of https://mozilla.github.io/syseng-pod/quality-standards/


## Audit projects

Start or resume audit with:

```
./manage.py audit Socorro
```

And commit the changes to the `scorecards.yaml` file. 


## Publish updates

Generate the updated page locally, with the `quality-standards/` subfolder:

```
./manage.py html -o html/quality-standards/
```

Publish it to Github Pages using [ghp-import](https://pypi.org/project/ghp-import/):

```
ghp-import --push -m "Generate HTML page for quality standards" html/
```
