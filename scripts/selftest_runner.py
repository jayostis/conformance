#!/usr/bin/env python3
"""Mutation tests for run_conformance.py.

The question this file exists to answer is: *what would the runner report if the
thing it claims to check were absent?* A conformance runner that reports PASS
because it loaded no shapes, matched no focus nodes, or swallowed a parse error
is worse than no runner at all, because it manufactures confidence.

Every case below builds its input in a temporary directory, runs the real runner
against it, and asserts on the runner's machine-readable output. **Nothing here
mutates a tracked file**, and no mutated copy is ever written inside the repo.

Run:  python3 scripts/selftest_runner.py --spec-dir /path/to/spec
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rdflib import BNode

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "run_conformance.py"

# The fixture the positive-direction mutation tests operate on. Chosen because
# clinical:MedicationShape is one of the most constrained shapes in the suite,
# so a single removed triple is unambiguously attributable.
POSITIVE_FIXTURE = "med-001.json"
POSITIVE_MUTATION_TARGET = 'clinical:drugName "Lisinopril" ;'
POSITIVE_EXPECTED_CONSTRAINT = "clinical:MedicationShape / path clinical:drugName / MinCountConstraintComponent"

# The negative fixture the inverse-direction test repairs. proxy-002 is the only
# negative fixture in the suite that carries Turtle at all (see README).
NEGATIVE_FIXTURE = "proxy-002.json"
NEGATIVE_REPAIR_ANCHOR = 'cascade:proxyScope "read-only" ;'
NEGATIVE_REPAIR = 'cascade:proxyScope "read-only" ;\n    cascade:proxyRelationship "spouse" ;'

# An unrelated, independently-shaped fixture staged alongside a mutated one. The
# runner aborts a whole run that evaluates zero constraints, so a single-fixture
# tree whose only fixture is unshaped never reaches per-fixture reporting. The
# companion keeps the suite-level guard honest while the per-fixture assertion
# is made.
COMPANION_FIXTURE = "profile-001.json"


class SelfTestFailure(AssertionError):
    pass


def run_runner(spec_dir: Path, fixtures_dir: Path, extra=()) -> tuple[int, dict, str]:
    """Invoke the runner and return (exit code, parsed JSON results, stderr)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        json_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                "--spec-dir", str(spec_dir),
                "--fixtures-dir", str(fixtures_dir),
                "--json", str(json_path),
                "--quiet", "--allow-spec-drift",
                *extra,
            ],
            capture_output=True, text=True,
        )
        payload = {}
        if json_path.exists() and json_path.stat().st_size:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        return proc.returncode, payload, proc.stderr
    finally:
        json_path.unlink(missing_ok=True)


def result_for(payload: dict, path: str) -> dict:
    for entry in payload.get("fixtures", []):
        if entry["path"] == path:
            return entry
    raise SelfTestFailure(f"runner returned no result for {path}")


def stage_fixture(tmp: Path, name: str, transform=None, companion: str | None = None) -> Path:
    """Copy one fixture into an isolated tree, optionally mutating its Turtle."""
    fixtures = tmp / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    names = [name] + ([companion] if companion else [])
    for candidate in names:
        doc = json.loads((REPO / "fixtures" / candidate).read_text(encoding="utf-8"))
        if transform is not None and candidate == name:
            doc["expectedOutput"]["turtle"] = transform(doc["expectedOutput"]["turtle"])
        (fixtures / candidate).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return fixtures


def stage_spec(tmp: Path, spec_dir: Path, transform=None) -> Path:
    """Copy the spec ontologies into an isolated tree, optionally mutating them."""
    dest = tmp / "spec"
    shutil.copytree(spec_dir / "ontologies", dest / "ontologies")
    if transform is not None:
        transform(dest)
    return dest


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------

def case_unmutated_positive_passes(spec_dir, tmp):
    """Control for the positive mutation: the fixture as authored must pass."""
    fixtures = stage_fixture(tmp, POSITIVE_FIXTURE)
    code, payload, _ = run_runner(spec_dir, fixtures)
    entry = result_for(payload, POSITIVE_FIXTURE)
    if entry["outcome"] != "pass":
        raise SelfTestFailure(f"{POSITIVE_FIXTURE} should pass unmutated, got {entry['reason']}")
    if entry["constraintChecks"] <= 0:
        raise SelfTestFailure(
            f"{POSITIVE_FIXTURE} passed with {entry['constraintChecks']} constraint checks. "
            "A pass that evaluated nothing is the defect this runner exists to catch."
        )
    if code != 0:
        raise SelfTestFailure(f"expected exit 0 on an all-pass tree, got {code}")
    return f"{POSITIVE_FIXTURE} passes with {entry['constraintChecks']} constraint checks"


def case_positive_mutation_is_caught(spec_dir, tmp):
    """Break exactly one constraint: the runner must name that constraint."""
    fixtures = stage_fixture(
        tmp, POSITIVE_FIXTURE,
        transform=lambda t: t.replace(POSITIVE_MUTATION_TARGET, "", 1),
    )
    code, payload, _ = run_runner(spec_dir, fixtures)
    entry = result_for(payload, POSITIVE_FIXTURE)
    if entry["outcome"] != "fail" or entry["reason"] != "VIOLATIONS":
        raise SelfTestFailure(
            f"removing {POSITIVE_MUTATION_TARGET!r} should fail with VIOLATIONS, "
            f"got {entry['outcome']}/{entry['reason']}"
        )
    if not any(POSITIVE_EXPECTED_CONSTRAINT in v for v in entry["violations"]):
        raise SelfTestFailure(
            f"failure did not name the broken constraint. Expected "
            f"{POSITIVE_EXPECTED_CONSTRAINT!r}, got {entry['violations']}"
        )
    if len(entry["violations"]) != 1:
        raise SelfTestFailure(
            "one broken constraint should produce exactly one violation, got "
            f"{len(entry['violations'])}: {entry['violations']}"
        )
    if code == 0:
        raise SelfTestFailure("runner exited 0 on a tree containing a failure")
    return f"1 constraint broken, 1 violation reported, named: {POSITIVE_EXPECTED_CONSTRAINT}"


def case_unrepaired_negative_passes(spec_dir, tmp):
    """Control for the inverse mutation: the negative fixture is rejected today."""
    fixtures = stage_fixture(tmp, NEGATIVE_FIXTURE)
    _code, payload, _ = run_runner(spec_dir, fixtures)
    entry = result_for(payload, NEGATIVE_FIXTURE)
    if entry["outcome"] != "pass":
        raise SelfTestFailure(f"{NEGATIVE_FIXTURE} should pass, got {entry['reason']}")
    if not entry["violations"]:
        raise SelfTestFailure("a negative fixture that passes must have violated something")
    return f"{NEGATIVE_FIXTURE} rejected by: {entry['violations'][0].split(' :: ')[0]}"


def case_repaired_negative_is_reported(spec_dir, tmp):
    """Repair what the negative fixture is negative about: it must be flagged."""
    fixtures = stage_fixture(
        tmp, NEGATIVE_FIXTURE,
        transform=lambda t: t.replace(NEGATIVE_REPAIR_ANCHOR, NEGATIVE_REPAIR, 1),
    )
    _code, payload, _ = run_runner(spec_dir, fixtures)
    entry = result_for(payload, NEGATIVE_FIXTURE)
    if entry["outcome"] != "fail" or entry["reason"] != "NO_VIOLATION":
        raise SelfTestFailure(
            "repairing the violated constraint should be reported as unexpectedly "
            f"conforming (NO_VIOLATION), got {entry['outcome']}/{entry['reason']}"
        )
    return "repaired negative reported as NO_VIOLATION (unexpectedly conforming)"


def case_absent_shape_is_not_a_pass(spec_dir, tmp):
    """The standing review question, executed.

    Delete the shape that constrains the fixture and re-run. If the runner still
    said PASS, every green result in this suite would be meaningless.
    """
    def strip_medication_shape(dest: Path):
        # Remove the shape at the RDF level rather than by text surgery: the
        # shape spans blank lines, so cutting on whitespace leaves broken Turtle
        # and the run aborts for the wrong reason.
        from rdflib import Graph, URIRef

        path = dest / "ontologies" / "clinical" / "v1" / "clinical.shapes.ttl"
        graph = Graph()
        graph.parse(path, format="turtle")
        shape = URIRef("https://ns.cascadeprotocol.org/clinical/v1#MedicationShape")
        pending = [shape]
        seen = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            for _p, obj in list(graph.predicate_objects(node)):
                if isinstance(obj, BNode):
                    pending.append(obj)
            graph.remove((node, None, None))
        path.write_text(graph.serialize(format="turtle"), encoding="utf-8")

    fixtures = stage_fixture(tmp, POSITIVE_FIXTURE, companion=COMPANION_FIXTURE)
    spec_copy = stage_spec(tmp, spec_dir, strip_medication_shape)
    code, payload, _ = run_runner(spec_copy, fixtures)
    entry = result_for(payload, POSITIVE_FIXTURE)
    if entry["outcome"] == "pass":
        raise SelfTestFailure(
            "removing clinical:MedicationShape still produced PASS. The runner is "
            "reporting conformance it never checked."
        )
    if entry["reason"] != "UNSHAPED" or entry["constraintChecks"] != 0:
        raise SelfTestFailure(
            f"expected UNSHAPED with 0 constraint checks, got {entry['reason']} "
            f"with {entry['constraintChecks']}"
        )
    if code == 0:
        raise SelfTestFailure("runner exited 0 with an unshaped fixture")
    return "shape removed -> UNSHAPED (0 checks), not PASS"


def case_unparseable_fixture_is_an_error(spec_dir, tmp):
    """A fixture whose RDF does not parse must fail, never count as a pass."""
    fixtures = stage_fixture(
        tmp, POSITIVE_FIXTURE,
        transform=lambda t: t + "\n<urn:broken> clinical:drugName \n",
        companion=COMPANION_FIXTURE,
    )
    _code, payload, _ = run_runner(spec_dir, fixtures)
    entry = result_for(payload, POSITIVE_FIXTURE)
    if entry["outcome"] != "fail" or entry["reason"] != "PARSE_ERROR":
        raise SelfTestFailure(
            f"unparseable Turtle should be PARSE_ERROR, got {entry['outcome']}/{entry['reason']}"
        )
    return "unparseable Turtle -> PARSE_ERROR"


def case_empty_shapes_aborts(spec_dir, tmp):
    """No shapes loaded must abort the run, not validate everything vacuously."""
    def empty_all_shapes(dest: Path):
        for path in dest.glob("ontologies/*/*/*.shapes.ttl"):
            path.write_text("# emptied by selftest\n", encoding="utf-8")

    fixtures = stage_fixture(tmp, POSITIVE_FIXTURE)
    spec_copy = stage_spec(tmp, spec_dir, empty_all_shapes)
    code, _payload, stderr = run_runner(spec_copy, fixtures)
    if code != 2:
        raise SelfTestFailure(f"empty shapes should abort with exit 2, got {code}")
    if "SELF-CHECK FAILED" not in stderr:
        raise SelfTestFailure(f"abort did not explain itself: {stderr!r}")
    return "empty shapes -> exit 2, SELF-CHECK FAILED"


def case_malformed_shapes_aborts(spec_dir, tmp):
    """A shapes file that does not parse must abort, not silently shrink the constraint set."""
    def corrupt(dest: Path):
        path = dest / "ontologies" / "clinical" / "v1" / "clinical.shapes.ttl"
        path.write_text(path.read_text(encoding="utf-8") + "\nclinical:Broken a sh:NodeShape \n",
                        encoding="utf-8")

    fixtures = stage_fixture(tmp, POSITIVE_FIXTURE)
    spec_copy = stage_spec(tmp, spec_dir, corrupt)
    code, _payload, stderr = run_runner(spec_copy, fixtures)
    if code != 2 or "does not parse" not in stderr:
        raise SelfTestFailure(
            f"a malformed shapes file should abort with exit 2, got {code}: {stderr[:200]!r}"
        )
    return "malformed shapes file -> exit 2, named the file"


def case_spec_pin_is_enforced(spec_dir, tmp):
    """A spec checkout that is not at the pinned commit must be refused."""
    fixtures = stage_fixture(tmp, POSITIVE_FIXTURE)
    proc = subprocess.run(
        [
            sys.executable, str(RUNNER),
            "--spec-dir", str(spec_dir),
            "--fixtures-dir", str(fixtures),
            "--quiet",
        ],
        capture_output=True, text=True,
        env={**os.environ, "CASCADE_SPEC_DIR": ""},
    )
    pinned = (REPO / "scripts" / "SPEC_PIN").read_text(encoding="utf-8")
    commit = next(l.split("=", 1)[1].strip() for l in pinned.splitlines() if l.startswith("commit="))
    head = subprocess.run(
        ["git", "-C", str(spec_dir), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    if head and head != commit:
        if proc.returncode != 2 or "SPEC_PIN" not in proc.stderr:
            raise SelfTestFailure(
                f"spec at {head} differs from pin {commit} but the runner did not refuse it"
            )
        return f"drifted spec checkout ({head[:7]}) refused"
    if proc.returncode == 2 and "SPEC_PIN" in proc.stderr:
        raise SelfTestFailure("spec checkout matches the pin but the runner refused it anyway")
    return f"spec checkout matches pin {commit[:7]}, accepted"


CASES = [
    ("unmutated positive fixture passes", case_unmutated_positive_passes),
    ("one broken constraint is caught and named", case_positive_mutation_is_caught),
    ("unrepaired negative fixture passes", case_unrepaired_negative_passes),
    ("repaired negative is reported as conforming", case_repaired_negative_is_reported),
    ("absent shape yields UNSHAPED, not PASS", case_absent_shape_is_not_a_pass),
    ("unparseable fixture is an error", case_unparseable_fixture_is_an_error),
    ("empty shapes graph aborts the run", case_empty_shapes_aborts),
    ("malformed shapes file aborts the run", case_malformed_shapes_aborts),
    ("spec pin is enforced", case_spec_pin_is_enforced),
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec-dir", default=os.environ.get("CASCADE_SPEC_DIR"))
    args = parser.parse_args(argv)

    spec_dir = Path(args.spec_dir).resolve() if args.spec_dir else (REPO.parent / "spec")
    if not spec_dir.is_dir():
        sys.stderr.write(f"selftest: spec checkout not found at {spec_dir}\n")
        return 2

    print("run_conformance.py mutation tests")
    print("=" * 72)
    failures = 0
    for name, fn in CASES:
        with tempfile.TemporaryDirectory(prefix="cascade-conf-selftest-") as tmpdir:
            try:
                detail = fn(spec_dir, Path(tmpdir))
                print(f"  PASS  {name}")
                print(f"          {detail}")
            except SelfTestFailure as exc:
                failures += 1
                print(f"  FAIL  {name}")
                print(f"          {exc}")
    print("-" * 72)
    print(f"{len(CASES) - failures} passed / {failures} failed / {len(CASES)} total")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
