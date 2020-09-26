import datetime
import json as Json
import packaging.version
import pathlib, pickle
import re
import requests

import iso8601
from tabulate import tabulate

FILE_HEAD = """Plugins List
============

The plugins are listed automatically from PyPI.
Only PyPI projects that match "pytest-\\*" are considered plugins.
"""

DEVELOPMENT_STATUS_CLASSIFIERS = (
    "Development Status :: 1 - Planning",
    "Development Status :: 2 - Pre-Alpha",
    "Development Status :: 3 - Alpha",
    "Development Status :: 4 - Beta",
    "Development Status :: 5 - Production/Stable",
    "Development Status :: 6 - Mature",
    "Development Status :: 7 - Inactive",
)

PLUGIN_COUNT = 0

def filter_development_status(plugin_classifiers):
    for classifier in DEVELOPMENT_STATUS_CLASSIFIERS:
        if classifier in plugin_classifiers:
            return classifier


def iter_plugins():
    global PLUGIN_COUNT
    regex = r">([\d\w-]*)</a>"
    response = requests.get("https://pypi.org/simple")
    for match in re.finditer(regex, response.text):
        name = match.groups()[0]
        if not name.startswith("pytest-"):
            continue
        if pathlib.Path(f"/workspaces/{name}.json").is_file():
            with pathlib.Path(f"/workspaces/{name}.json").open() as f:
                print(name)
                json = Json.load(f)
            response = lambda: None
            response.ok = lambda: True
        else:
            response = requests.get(f"https://pypi.org/pypi/{name}/json")
            if not response.ok:
                continue
            json = response.json()
        if not pathlib.Path(f"/workspaces/{name}.json").exists():
            with pathlib.Path(f"/workspaces/{name}.json").open("w") as f:
                Json.dump(json, f)
        project_url = json["info"]["project_url"]
        name_with_link = f"`{name} <{project_url}>`_"
        summary = json["info"]["summary"]

        classifiers = set(json["info"]["classifiers"])
        development_status = filter_development_status(classifiers)
        if development_status:
            continue
        releases = json["releases"]
        for version in sorted(releases, key=lambda v: packaging.version.parse(v), reverse=True):
            try:
                released = iso8601.parse_date(
                    json["releases"][version][-1]["upload_time_iso_8601"]
                ).strftime("%Y")
                break
            except IndexError:
                pass
        else:
            released = None

        if int(released) >= 2018:
            continue

        pyversions_badge = f".. image:: https://img.shields.io/pypi/pyversions/{name}"
        PLUGIN_COUNT += 1
        yield {
            "name": name_with_link,
            "summary": summary,
            "released": released,
            "pyversion": pyversions_badge,
            "status": development_status[22:] if development_status else "NA"
        }


def main():
    plugins_table = tabulate(iter_plugins(), headers="keys", tablefmt="rst")
    with open("plugins_list.rst", "w") as f:
        f.write(FILE_HEAD)
        f.write(f"In this list are {PLUGIN_COUNT} plugins.\n\n")
        f.write(plugins_table)
        f.write("\n")


if __name__ == "__main__":
    main()
