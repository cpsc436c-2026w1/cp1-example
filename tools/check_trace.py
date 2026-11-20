#!/usr/bin/env python3
"""Traceability check: does every code appear where it must?

    python3 tools/check_trace.py [folder]     # folder: the repository root (default: the current folder)

It reads docs/requirements.md, docs/design.md and features/*.feature, prints one line for each problem, then a
table code -> where defined -> where used. Exit code 1 if there is a problem, else 0. Standard library only.

The rules:
  1. Every JS, R, RF and RQ code is defined once in docs/requirements.md: a JS where its heading starts with it
     (## JS01 ...), an R, RF or RQ where a list item starts with it (- **R010** ..., - **RF010** ...).
  2. Every R or RF line that ends with a Scenario link (`[Scenario](../features/<file>.feature)`) is the tag of a
     Rule in that feature file. (An RF with "Read: ..." and an RQ do not get a rule.)
  3. Every code used as a tag in features/ or named in docs/design.md is defined in docs/requirements.md.
  4. A code is the tag of one Rule only.
  5. Every DS and SIM id is defined once in docs/design.md, section Data: a DS where "Our data" first names it,
     a SIM as a bullet under "Simulated data" that starts with its id (- **SIM01 Rush hour** [RF010] ...).
  6. Every DS or SIM id used in features/ or in docs/requirements.md is defined there.
  7. Every SIM bullet names a DS that is defined ("from DS01").
"""
import re
import sys
from pathlib import Path

CODE = r"\b(?:JS|RF|RQ|R)\d+\b"       # JS01, R010, RF010, RQ010
DATA_ID = r"\b(?:DS|SIM)\d+\b"        # DS01, SIM01


def read_requirements(path: Path, problems: list[str]) -> tuple[dict, dict]:
    """Returns ({code: "requirements.md:12"}, {code that must have a Rule: the feature file its Scenario link names})."""
    defined, needs_rule = {}, {}

    def define(code, n):
        if code in defined:
            problems.append(f"requirements.md:{n}: {code} is defined twice (first at {defined[code]})")
        defined.setdefault(code, f"requirements.md:{n}")

    for n, line in enumerate(path.read_text().splitlines(), 1):
        if m := re.match(r"## (JS\d+)\b", line):                    # ## JS01 Driver: ...
            define(m.group(1), n)
        elif m := re.match(r"- \*\*(R[FQ]?\d+)\b", line):          # - **R010** WHEN ...   - **RF010** wording ...
            code = m.group(1)
            define(code, n)
            link = re.search(r"\[Scenario\]\((?:\.\./)?features/([^)]+\.feature)\)", line)
            if link and not code.startswith("RQ"):
                needs_rule[code] = link.group(1)
    return defined, needs_rule


def read_features(folder: Path, problems: list[str]) -> tuple[dict, dict, dict]:
    """Returns ({code: [places where it is a tag]}, {code: [places where it tags a Rule]}, {data id: [places]})."""
    tags, rules, data_used = {}, {}, {}
    for path in sorted(folder.glob("*.feature")):
        waiting = []                                                # tags read, not yet attached to a keyword
        for n, line in enumerate(path.read_text().splitlines(), 1):
            text, place = line.strip(), f"{path.name}:{n}"
            for data_id in re.findall(DATA_ID, text):
                data_used.setdefault(data_id, []).append(place)
            if text.startswith("@"):
                waiting += [t[1:] for t in text.split()]
            elif text.startswith(("Feature:", "Rule:", "Example:", "Scenario:")):
                for tag in waiting:
                    if re.fullmatch(CODE, tag):                     # @live, @eval and other labels are not codes
                        tags.setdefault(tag, []).append(place)
                        if text.startswith("Rule:"):
                            rules.setdefault(tag, []).append(place)
                waiting = []
    return tags, rules, data_used


def read_design(path: Path, problems: list[str]) -> tuple[dict, dict, dict]:
    """Returns ({DS or SIM id: place}, {SIM id: the rest of its bullet}, {code: [places in design.md]})."""
    defined, sim_from, codes_used, in_data, part, last = {}, {}, {}, False, "", ""
    for n, line in enumerate(path.read_text().splitlines(), 1):
        place = f"design.md:{n}"
        if line.startswith("## "):
            in_data = line.strip() == "## Data"
        elif line.startswith("### "):
            part = line
        for code in re.findall(CODE, line):
            codes_used.setdefault(code, []).append(place)
        if not in_data:
            continue
        if "Our data" in part:                                      # a DS is defined where the text first names it
            for ds in re.findall(r"\bDS\d+\b", line):
                defined.setdefault(ds, place)
        elif "Simulated data" in part and (m := re.match(r"- \*\*(SIM\d+)\b", line)):
            sim, last = m.group(1), m.group(1)                      # - **SIM01 Rush hour** [RF010] ... from DS01 ...
            if sim in defined:
                problems.append(f"{place}: {sim} is defined twice (first at {defined[sim]})")
            defined.setdefault(sim, place)
            sim_from[sim] = line[m.end():]
        elif "Simulated data" in part and line.startswith("  ") and sim_from:
            sim_from[last] += " " + line                            # the bullet's next lines
    return defined, sim_from, codes_used


def check(root: Path) -> tuple[list[str], list[tuple]]:
    """Returns (problems, rows of the table)."""
    problems = []
    codes, needs_rule = read_requirements(root / "docs/requirements.md", problems)
    tags, rules, data_in_features = read_features(root / "features", problems)
    data_ids, sim_from, codes_in_design = read_design(root / "docs/design.md", problems)

    for code, file in sorted(needs_rule.items()):                   # rule 2
        if code not in rules:
            problems.append(f"{codes[code]}: {code} is not the tag of a Rule in features/")
        elif not any(place.startswith(file + ":") for place in rules[code]):
            problems.append(f"{codes[code]}: {code} links {file}, but its Rule is at {rules[code][0]}")
    for code, places in sorted(tags.items()):                       # rule 3, tags
        if code not in codes:
            problems.append(f"{places[0]}: @{code} is not defined in docs/requirements.md")
    for code, places in sorted(codes_in_design.items()):            # rule 3, design
        if code not in codes:
            problems.append(f"{places[0]}: {code} is not defined in docs/requirements.md")
    for code, places in sorted(rules.items()):                      # rule 4
        if len(places) > 1:
            problems.append(f"{places[1]}: @{code} is already the tag of the Rule at {places[0]}")

    data_used = {k: list(v) for k, v in data_in_features.items()}   # rule 6
    for n, line in enumerate((root / "docs/requirements.md").read_text().splitlines(), 1):
        for data_id in re.findall(DATA_ID, line):
            data_used.setdefault(data_id, []).append(f"requirements.md:{n}")
    for data_id, places in sorted(data_used.items()):
        if data_id not in data_ids:
            problems.append(f"{places[0]}: {data_id} is not defined in docs/design.md, section Data")
    for sim_id, source in sorted(sim_from.items()):                 # rule 7
        named = re.findall(r"DS\d+", source)
        if not named:
            problems.append(f"{data_ids[sim_id]}: {sim_id} does not name a DS in its bullet")
        for ds in named:
            if ds not in data_ids:
                problems.append(f"{data_ids[sim_id]}: {sim_id} is built from {ds}, which is not defined under Our data")
            else:
                data_used.setdefault(ds, []).append(sim_id)

    table = []
    for code, place in codes.items():
        used = list(tags.get(code, []))
        if code in codes_in_design:
            used.append(f"design.md ({len(codes_in_design[code])} lines)")
        if not used:
            used = ["read, not run" if code.startswith(("RF", "RQ")) else "no rule yet"]
        table.append((code, place, ", ".join(used)))
    for data_id, place in data_ids.items():
        table.append((data_id, place, ", ".join(dict.fromkeys(data_used.get(data_id, ["not used"])))))
    return problems, table


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".")
    problems, table = check(root)
    for problem in problems:
        print("PROBLEM", problem)
    print(f"{'Code':6} {'Defined':22} Used")
    for code, place, used in table:
        print(f"{code:6} {place:22} {used}")
    print(f"\n{len(table)} codes and data ids, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
