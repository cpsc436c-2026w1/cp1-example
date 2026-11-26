#!/usr/bin/env python3
"""Traceability check: does every ID appear where it must?

    python3 tools/check_trace.py [folder]     # folder: the repository root (default: the current folder)

It reads docs/requirements.md, docs/design.md and features/*.feature, prints one line for each problem, then a
table ID -> where defined -> where used. Exit code 1 if there is a problem, else 0. Standard library only.

The rules:
  1. Every JS, R, RF and RQ ID is defined once in docs/requirements.md: a JS where its heading starts with it
     (## JS01 ...), an R, RF or RQ where a list item starts with it (- **R010** ..., - **RF010** ...).
  2. Every R or RF line that ends with a Scenario link (`[Scenario](../features/<file>.feature)`) is the tag of a
     Rule in that feature file. An R or RF line that ends with "Read: ..." (or "Read at Checkpoint 2: ...") must not
     get a rule. An RF line with neither a Scenario link, a Reply [R...] nor Read: is a problem (a testable RF needs
     a rule). An R line without a link and without a rule is listed as "no rule yet", not a problem. (An RF with "Read: ..." and an RQ do not get a rule;
     an RF line names the R lines that meet it as Reply [R080]: ...)
  3. Every ID used as a tag in features/ or named in docs/design.md is defined in docs/requirements.md
     (in design.md the IDs an item serves are in brackets after its name: ### Counting requests [R010, R020],
     - **SIM01 Rush hour** [RF010]; and in the IDs column of Resources; an ID elsewhere in a sentence is not read).
     A tag line belongs to the keyword line under it: Feature, Rule, Background, Example, Scenario, Scenario
     Outline, Scenario Template, Examples.
  4. An ID is the tag of one Rule only.
  5. Every DS and SIM id is defined once in docs/design.md, section Data: a DS where "Our data" first names it,
     a SIM as a bullet under "Simulated data" that starts with its id (- **SIM01 Rush hour** [RF010] ...).
  6. Every DS or SIM id used in features/ or in docs/requirements.md is defined there.
  7. A DS that a SIM bullet names ("from DS01") is defined. A SIM bullet need not name one: simulated data can be
     made up (the Checkpoint 1 page does not ask for a source).
  8. Every Rule has at least one Example (or Scenario) under it.

Tables: an RF or RQ (or R) may also be defined by a table row whose first cell is its ID, as some teams write
`## Stakeholder input` (| RF010 | ... |); the row is read like a list line (Scenario link, Reply [R...], Read:).

Decisions: a team records its decisions on what a check listed in docs/requirements.md only, one line each, indented
under the requirement, RF or RQ it concerns, or under a section `## Decisions` naming the item when no requirement
fits (a resource, a SIM, the budget alert):
    Decision (<check> <question id>[, <item>], PR #<n>): keep | later, <checkpoint> | check is wrong. <reason>
The script lists every decision as DECISION with the line it is under. A decision never hides a problem: a PROBLEM
about an ID the decision concerns (the requirement it is under, or the item it names) is still printed, with the
decision beside it, and counted apart. A decision never changes the exit code: 1 while any problem is printed, so
a person reads each decision against the exact problem it sits beside. A decision line in another file, or a line starting "Decision (" in another form, is a problem.
"""
import re
import sys
from pathlib import Path

CODE = r"\b(?:JS|RF|RQ|R)\d+\b"       # JS01, R010, RF010, RQ010
DATA_ID = r"\b(?:DS|SIM)\d+\b"        # DS01, SIM01
KEYWORDS = ("Feature:", "Rule:", "Background:", "Example:", "Scenario:", "Scenario Outline:", "Scenario Template:",
            "Examples:", "Scenarios:")


REQ_LINE = re.compile(r"^\s*[-*+]\s+(?:\*\*`?|`)(R[FQ]?\d+)\b")       # - **R010**, * **R010**, - **`R010`**, - `R010`
PLAIN_REQ = re.compile(r"^\s*(?:[-*+]\s+|#{2,4}\s+)(R[FQ]?\d+)\b")        # - R010 ..., ### R010 ...: a mention, not a definition
JS_LINE = re.compile(r"^#{1,3}\s+\**`?(JS\d+)\b")                         # ## JS01 Driver: ..., # JS01, ### JS01
READ = re.compile(r"\bRead(?: at Checkpoint 2)?:")
TABLE_ROW = re.compile(r"^\s*\|\s*(?:\*\*`?|`)?(R[FQ]?\d+)\b")             # | RF010 | ... | or | **RF010** | ...
DECISION_START = re.compile(r"^\s*(?:[-*+]\s+|#\s*)?Decision\s*\(", re.I)
DECISION = re.compile(r"^\s*(?:[-*+]\s+|#\s*)?Decision \((?P<check>[\w-]+) (?P<question>[A-Z]{2}\d+)(?:, (?!PR #)(?P<about>[^,)]+))?(?:, PR #(?P<pr>\d+))?\):"
                      r"\s*(?P<kind>keep|later, [^.]+|check is wrong)\.\s*(?P<reason>\S.*)$")
DECISION_FORM = ('Decision (<check> <question id>, PR #<n>): keep | later, <checkpoint> | check is wrong. <reason>')


def read_decision(line: str, place: str, under: str, decisions: list, problems: list) -> bool:
    """True when the line is a decision note (well formed or not): its IDs are then not read as Gherkin or design."""
    if not DECISION_START.match(line):
        return False
    m = DECISION.match(line)
    if m:
        decisions.append((place, under, m))
    else:
        problems.append(f"{place}: this decision line is not in the form {DECISION_FORM}")
    return True


def read_text(path: Path) -> str:
    """A file's text, without a byte-order mark (Notepad adds one)."""
    return path.read_text(encoding="utf-8-sig")


def read_requirements(path: Path, problems: list[str]) -> tuple[dict, dict, dict]:
    """Returns ({code: "requirements.md:12"}, {code that must have a Rule: the feature file its Scenario link, or None},
    {code whose line ends with Read: and must not have a Rule: its place})."""
    defined, needs_rule, read_only = {}, {}, {}
    plain = {}                                                      # IDs that start a plain line: for the hint

    def define(code, n):
        if code in defined:
            problems.append(f"requirements.md:{n}: {code} is defined twice (first at {defined[code]})")
        defined.setdefault(code, f"requirements.md:{n}")

    last = ""
    stakeholder_input = False
    for n, line in enumerate(read_text(path).splitlines(), 1):
        if line.startswith(("# ", "## ")):
            stakeholder_input = line.strip().casefold() == "## stakeholder input"
        if DECISION_START.match(line):
            place = f"requirements.md:{n}"
            before = len(DECISIONS)
            read_decision(line, place, last, DECISIONS, problems)
            if len(DECISIONS) > before:
                m = DECISIONS[-1][2]
                if not last:
                    DECISIONS.pop()
                    problems.append(f"{place}: this decision line is not under a requirement, RF or RQ, nor under "
                                    "## Decisions: put it under the line it concerns")
                elif last == "## Decisions" and not m["about"]:
                    problems.append(f"{place}: a decision under ## Decisions must name its item: "
                                    "Decision (<check> <question id>, <item>, PR #<n>): …")
            continue
        if line.startswith("## "):
            last = "## Decisions" if line.strip().lower() == "## decisions" else ""
        elif m := (REQ_LINE.match(line) or (stakeholder_input and TABLE_ROW.match(line)) or JS_LINE.match(line)):
            last = f"{m.group(1)} (requirements.md:{n})"
        if m := JS_LINE.match(line):
            define(m.group(1), n)
        elif (m := PLAIN_REQ.match(line)) and not REQ_LINE.match(line):
            plain.setdefault(m.group(1), f"requirements.md:{n}")
        if m := (REQ_LINE.match(line) or (stakeholder_input and TABLE_ROW.match(line))):
            code = m.group(1)
            define(code, n)
            if code.startswith("RQ"):                               # a request: a Reply, no rule
                continue
            link = re.search(r"\[Scenario\]\((?:\.\./)?features/([^)]+\.feature)\)", line)
            if READ.search(line) and not link:
                read_only[code] = f"requirements.md:{n}"            # a test cannot check it: no rule
            elif link:
                needs_rule[code] = link.group(1)
            elif code.startswith("RF") and not re.search(r"Reply \[R\d+", line):
                problems.append(f"requirements.md:{n}: {code} has no [Scenario](...) link, no Reply [R...] and no "
                                "Read: (a testable RF needs a rule and a Scenario link; one a test cannot check ends "
                                "with Read:)")
    for code, place in plain.items():
        if code not in defined:
            problems.append(f"{place}: {code} starts a line but is not bold, so it is not read as a definition: "
                            f"write it as - **{code}** ...")
    return defined, needs_rule, read_only


def read_features(folder: Path, problems: list[str]) -> tuple[dict, dict, dict]:
    """Returns ({code: [places where it is a tag]}, {code: [places where it tags a Rule]}, {data id: [places]})."""
    tags, rules, data_used = {}, {}, {}
    for path in sorted(folder.rglob("*.feature")):
        waiting = []                                                # tags read, not yet attached to a keyword
        open_rule = None                                            # [place of the Rule line, examples under it]
        doc_delimiter = None
        doc_start = None
        for n, line in enumerate(read_text(path).splitlines(), 1):
            text, place = line.strip(), f"{path.relative_to(folder)}:{n}"
            if doc_delimiter:
                if text.startswith(doc_delimiter):
                    doc_delimiter = None
                continue
            if text.startswith(('"""', "'''", "```")):
                doc_delimiter = text[:3]
                doc_start = place
                continue
            if text.startswith("#"):
                if DECISION_START.match(text):
                    problems.append(f"{place}: decision lines go in docs/requirements.md, under the requirement they "
                                    "concern (or under ## Decisions), not in a feature file")
                continue
            for data_id in re.findall(DATA_ID, text):
                data_used.setdefault(data_id, []).append(place)
            if text.startswith("@"):
                waiting += [t[1:] for t in text.split()]
            elif text.startswith(KEYWORDS):                         # every keyword line takes the tags above it
                if text.startswith(("Rule:", "Feature:")):          # rule 8: a Rule ends where the next starts
                    if open_rule and open_rule[1] == 0:
                        problems.append(f"{open_rule[0]}: this Rule has no Example")
                    open_rule = [place, 0] if text.startswith("Rule:") else None
                elif text.startswith(("Example:", "Scenario:", "Scenario Outline:", "Scenario Template:")) and open_rule:
                    open_rule[1] += 1
                for tag in waiting:
                    if re.fullmatch(CODE, tag):                     # @live, @eval and other labels are not codes
                        tags.setdefault(tag, []).append(place)
                        if text.startswith("Rule:"):
                            rules.setdefault(tag, []).append(place)
                waiting = []
        if open_rule and open_rule[1] == 0:
            problems.append(f"{open_rule[0]}: this Rule has no Example")
        if doc_delimiter:
            problems.append(f"{doc_start}: this docstring is not closed, so the rest of the file was not read")
    return tags, rules, data_used


def read_design(path: Path, problems: list[str]) -> tuple[dict, dict, dict]:
    """Returns ({DS or SIM id: place}, {SIM id: the rest of its bullet}, {code: [places in design.md]})."""
    defined, sim_from, codes_used, in_data, part, last = {}, {}, {}, False, "", ""
    part_is_resources, ids_col = False, None
    prev = ""
    for n, line in enumerate(read_text(path).splitlines(), 1):
        place = f"design.md:{n}"
        if DECISION_START.match(line):
            problems.append(f"{place}: decision lines go in docs/requirements.md, under the requirement they concern "
                            "(or under ## Decisions naming this item), not in docs/design.md")
            continue                                                # not part of a SIM bullet or the design text
        if line.strip():
            prev = place
        if line.startswith("## "):
            in_data = line.strip().lower() == "## data"
            part_is_resources = line.strip().lower() == "## resources"
        elif line.startswith("### "):
            part = line.lower()
        if line.startswith("## "):
            ids_col = None
        if part_is_resources and line.startswith("|"):            # the IDs column of the Resources table
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if ids_col is None and "IDs" in cells:
                ids_col = cells.index("IDs")
            elif ids_col is not None and ids_col < len(cells):
                for code in re.findall(CODE, cells[ids_col]):
                    codes_used.setdefault(code, []).append(place)
        for bracket in re.findall(r"\[([^\]]*)\](?!\()", line):     # [R010, R020] after a name; not [text](link)
            for code in re.findall(CODE, bracket):
                codes_used.setdefault(code, []).append(place)
        if not in_data:
            continue
        if "our data" in part:                                      # a DS is defined where the text first names it
            for ds in re.findall(r"\bDS\d+\b", line):
                defined.setdefault(ds, place)
        elif "simulated data" in part and (m := re.match(r"\s*[-*+]\s+\**`?(SIM\d+)\b", line)):
            sim, last = m.group(1), m.group(1)                      # - **SIM01 Rush hour** [RF010] ... from DS01 ...
            if sim in defined:
                problems.append(f"{place}: {sim} is defined twice (first at {defined[sim]})")
            defined.setdefault(sim, place)
            sim_from[sim] = line[m.end():]
        elif "simulated data" in part and line.startswith("  ") and sim_from:
            sim_from[last] += " " + line                            # the bullet's next lines
    return defined, sim_from, codes_used


DECISIONS: list = []                                                # (place, the line it is under, match)


def check(root: Path) -> tuple[list[str], list[tuple]]:
    """Returns (problems, rows of the table)."""
    problems = []
    DECISIONS.clear()
    missing = [p for p in ("docs/requirements.md", "docs/design.md", "features") if not (root / p).exists()]
    if missing:
        return [f"{root.resolve()}: {', '.join(missing)} not found. Run it at the root of your team repository "
                "(the folder with docs/ and features/), or give that folder: python3 tools/check_trace.py <folder>"], []
    codes, needs_rule, read_only = read_requirements(root / "docs/requirements.md", problems)
    tags, rules, data_in_features = read_features(root / "features", problems)
    data_ids, sim_from, codes_in_design = read_design(root / "docs/design.md", problems)
    for path in sorted((root / "scripts").rglob("*")) if (root / "scripts").is_dir() else []:
        if path.is_file() and path.suffix in (".sh", ".py", ".toml", ".yml", ".yaml", ".md", ".txt", ""):
            try:
                lines = read_text(path).splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(lines, 1):
                if DECISION_START.match(line.lstrip("#/ ")):
                    problems.append(f"{path.relative_to(root)}:{n}: decision lines go in docs/requirements.md, under "
                                    "the requirement they concern (or under ## Decisions naming this item)")

    for code, file in sorted(needs_rule.items()):                   # rule 2
        if code not in rules:
            where = f" in {file}" if file else ""
            problems.append(f"{codes[code]}: {code} is not the tag of a Rule in features/: add @{code} above its "
                            f"Rule{where}, or write the Rule")
        elif file and not any(place.startswith(file + ":") for place in rules[code]):
            problems.append(f"{codes[code]}: {code} links {file}, but its Rule is at {rules[code][0]}")
    for code, place in sorted(read_only.items()):                   # rule 2: Read: lines get no rule
        if code in rules:
            problems.append(f"{place}: {code} ends with Read:, so it must not get a rule, but it tags the Rule at "
                            f"{rules[code][0]}")
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
    for n, line in enumerate(read_text(root / "docs/requirements.md").splitlines(), 1):
        if DECISION_START.match(line):
            continue
        for data_id in re.findall(DATA_ID, line):
            data_used.setdefault(data_id, []).append(f"requirements.md:{n}")
    for data_id, places in sorted(data_used.items()):
        if data_id not in data_ids:
            problems.append(f"{places[0]}: {data_id} is not defined in docs/design.md, section Data")
    for sim_id, source in sorted(sim_from.items()):                 # rule 7
        for ds in re.findall(r"DS\d+", source):
            if ds not in data_ids:
                problems.append(f"{data_ids[sim_id]}: {sim_id} is built from {ds}, which is not defined under Our data")
            else:
                data_used.setdefault(ds, []).append(sim_id)

    table = []
    for code, place in codes.items():
        used = list(tags.get(code, []))
        if code in codes_in_design:
            used.append(f"design.md ({len(codes_in_design[code])} lines)")
        if code.startswith("R") and not code.startswith(("RF", "RQ")) and code not in rules and code not in read_only:
            used.append("no rule yet")                              # shown even when design.md names it
        if not used:
            used = ["read, not run" if code.startswith(("RF", "RQ")) else "no rule yet"]
        table.append((code, place, ", ".join(used)))
    for data_id, place in data_ids.items():
        table.append((data_id, place, ", ".join(dict.fromkeys(data_used.get(data_id, ["not used"])))))
    return problems, table


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".")
    problems, table = check(root)
    about = []                                                      # (IDs a decision concerns, its text)
    for place, at, m in DECISIONS:
        pr = f", PR #{m['pr']}" if m["pr"] else ""
        ids = set(re.findall(CODE + "|" + DATA_ID, at.split(" (")[0] + " " + (m["about"] or "")))
        if m["about"]:
            ids.add(m["about"].strip())
        about.append((ids, f"{m['kind']}. {m['reason']} ({m['check']} {m['question']}{pr}, {place})"))
    decided = 0
    for problem in problems:
        text = problem.split(": ", 1)[-1]
        if "decision line" in text:
            note = None
        else:
            note = next((t for ids, t in about
                         if any(re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text) for i in ids if i)), None)
        decided += bool(note)
        print("PROBLEM", problem + (f"  [a team decision names this ID: {note}]" if note else ""))
    for place, under, m in DECISIONS:
        item = f", {m['about']}" if m["about"] else ""
        pr = f" PR #{m['pr']}" if m["pr"] else ""
        print(f"DECISION {place} (under {under or 'the start of the file'}) {m['check']} {m['question']}{item}{pr}: "
              f"{m['kind']}. {m['reason']}")
    print(f"{'ID':6} {'Defined':22} Used")
    for code, place, used in table:
        print(f"{code:6} {place:22} {used}")
    d = f", {len(DECISIONS)} decision{'' if len(DECISIONS) == 1 else 's'}" if DECISIONS else ""
    k = f" ({decided} with a team decision beside it: read it against the problem)" if decided else ""
    print(f"\n{len(table)} IDs, {len(problems)} problem{'' if len(problems) == 1 else 's'}{k}{d}")
    return 1 if problems else 0                                     # a decision never changes the exit code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
