#!/usr/bin/env python3
"""Execute every Cascade Protocol conformance fixture against the SHACL shapes.

This runner is the automated form of the algorithm documented in README.md under
"Running Fixtures Against an SDK", specialised to the case where there is no SDK
under test: instead of serialising `fixture.input`, it validates the Turtle the
fixture itself declares (`expectedOutput.turtle` for JSON fixtures, the file body
for `.ttl` fixtures) against the SHACL shapes published by `spec`.

Design notes, and the reason each one exists:

* Shapes come from a PINNED `spec` checkout (see `scripts/SPEC_PIN`). An unpinned
  runner silently tracks whatever vocabulary happens to be on `spec` `main`, so a
  suite that passed yesterday can pass today for a different reason.

* A fixture that no shape targets is NOT a pass. SHACL validation of an unshaped
  class reports `conforms=true` while evaluating zero constraints, which is
  indistinguishable from real conformance. The runner computes, independently of
  pyshacl, how many constraint parameters were actually reachable from a matched
  focus node, and reports `UNSHAPED` when that count is zero.

* An unreadable, unparseable, or schema-invalid fixture is an error, never a pass.

* The suite as a whole aborts (exit 2) if the shapes graph is empty, declares no
  `sh:targetClass`, or if zero constraint checks were evaluated across all
  fixtures. Those are the three ways this runner could report a meaningless PASS.

Exit codes: 0 all fixtures passed, 1 one or more failed, 2 runner self-check failed.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

try:
    import pyshacl
    from rdflib import BNode, Graph, Literal, URIRef
    from rdflib.namespace import RDF, RDFS, SH
except ImportError as exc:  # pragma: no cover - environment problem, not a fixture problem
    sys.stderr.write(
        f"runner: missing dependency ({exc}).\n"
        "Install with: python3 -m pip install -r scripts/requirements.txt\n"
    )
    raise SystemExit(2)

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

# Every SHACL core constraint parameter, plus the shape-valued ones the runner
# recurses through. Used to count how many constraints a matched shape actually
# brings to bear on a focus node.
CONSTRAINT_PARAMS = frozenset(
    SH[name]
    for name in (
        "class", "datatype", "nodeKind",
        "minCount", "maxCount",
        "minExclusive", "minInclusive", "maxExclusive", "maxInclusive",
        "minLength", "maxLength", "pattern", "flags",
        "languageIn", "uniqueLang",
        "equals", "disjoint", "lessThan", "lessThanOrEquals",
        "not", "and", "or", "xone",
        "node", "qualifiedValueShape", "qualifiedMinCount", "qualifiedMaxCount",
        "closed", "hasValue", "in", "sparql",
    )
)

# Shape-valued parameters the runner walks into when counting constraints.
NESTED_SHAPE_PARAMS = (SH["property"], SH["node"], SH["not"], SH["qualifiedValueShape"])

# Stable prefix table for rendering terms in the report. Deterministic by
# construction: it is a literal, ordered table, not derived from any graph's
# namespace bindings (which vary with parse order).
PREFIXES = (
    ("cascade", "https://ns.cascadeprotocol.org/core/v1#"),
    ("health", "https://ns.cascadeprotocol.org/health/v1#"),
    ("clinical", "https://ns.cascadeprotocol.org/clinical/v1#"),
    ("coverage", "https://ns.cascadeprotocol.org/coverage/v1#"),
    ("checkup", "https://ns.cascadeprotocol.org/checkup/v1#"),
    ("pots", "https://ns.cascadeprotocol.org/pots/v1#"),
    ("advisory", "https://ns.cascadeprotocol.org/advisory/v1#"),
    ("evidence", "https://ns.cascadeprotocol.org/evidence/v1#"),
    ("genomics", "https://ns.cascadeprotocol.org/genomics/v1#"),
    ("workbench", "https://ns.cascadeprotocol.org/workbench/v1#"),
    ("diabetes", "https://ns.cascadeprotocol.org/diabetes/v1#"),
    ("sh", "http://www.w3.org/ns/shacl#"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("owl", "http://www.w3.org/2002/07/owl#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
    ("foaf", "http://xmlns.com/foaf/0.1/"),
    ("prov", "http://www.w3.org/ns/prov#"),
    ("ldp", "http://www.w3.org/ns/ldp#"),
    ("dcterms", "http://purl.org/dc/terms/"),
    ("dcat", "http://www.w3.org/ns/dcat#"),
    ("void", "http://rdfs.org/ns/void#"),
    ("vcard", "http://www.w3.org/2006/vcard/ns#"),
    ("schema", "https://schema.org/"),
    ("fhir", "http://hl7.org/fhir/"),
    ("sct", "http://snomed.info/sct/"),
    ("loinc", "http://loinc.org/rdf#"),
    ("rxnorm", "http://www.nlm.nih.gov/research/umls/rxnorm/"),
)

# Files under fixtures/ that are inputs to a converter rather than RDF this
# runner can validate. Each is reported by category so the count is auditable.
NON_RDF_SUFFIXES = {
    ".xml": "converter input (C-CDA / ClinVar XML)",
    ".ldpatch": "converter input (LD Patch)",
    ".gz": "converter input (compressed VCF)",
    ".vcf": "converter input (VCF)",
    ".md": "inventory / documentation",
}

# Outcome reason codes.
R_OK = "OK"
R_VIOLATIONS = "VIOLATIONS"            # positive fixture: shapes reported violations
R_NO_VIOLATION = "NO_VIOLATION"        # negative fixture: shapes reported none
R_UNSHAPED = "UNSHAPED"                # zero constraints reachable; validation was vacuous
R_NO_TURTLE = "NO_TURTLE"              # fixture declares no RDF to validate
R_PARSE_ERROR = "PARSE_ERROR"
R_READ_ERROR = "READ_ERROR"
R_SCHEMA_INVALID = "SCHEMA_INVALID"

REASON_HELP = {
    R_VIOLATIONS: "positive fixture, shapes reported at least one sh:Violation",
    R_NO_VIOLATION: "negative fixture, shapes reported no sh:Violation so nothing rejected it",
    R_UNSHAPED: "no shape targets any subject in the fixture, so zero constraints ran",
    R_NO_TURTLE: "fixture declares no RDF body, so there is nothing to validate",
    R_PARSE_ERROR: "fixture RDF could not be parsed",
    R_READ_ERROR: "fixture file could not be read or decoded",
    R_SCHEMA_INVALID: "fixture JSON does not validate against schema/fixture-schema.json",
}


# --------------------------------------------------------------------------
# Term rendering (deterministic)
# --------------------------------------------------------------------------

def qname(term) -> str:
    """Render an RDF term deterministically.

    Blank nodes render as `_:blank` on purpose: rdflib assigns blank node labels
    from a process-local counter, so echoing them would make the report differ
    between runs. Determinism is a hard requirement here.
    """
    if term is None:
        return "-"
    if isinstance(term, BNode):
        return "_:blank"
    if isinstance(term, Literal):
        text = str(term)
        if len(text) > 60:
            text = text[:57] + "..."
        return json.dumps(text)
    if isinstance(term, URIRef):
        uri = str(term)
        for prefix, base in PREFIXES:
            if uri.startswith(base):
                return f"{prefix}:{uri[len(base):]}"
        return f"<{uri}>"
    return str(term)


# --------------------------------------------------------------------------
# Shapes loading and self-checks
# --------------------------------------------------------------------------

class Shapes:
    def __init__(self, graph: Graph, files: list[str], axioms: Graph, axiom_files: list[str]):
        self.graph = graph
        self.files = files
        self.axioms = axioms
        self.axiom_files = axiom_files
        self.node_shapes = self._collect_node_shapes()
        self.subclass_closure = self._build_subclass_closure()
        self._constraint_cache: dict = {}

    def _collect_node_shapes(self) -> list:
        shapes = set(self.graph.subjects(RDF.type, SH.NodeShape))
        # A subject carrying sh:targetClass is a shape whether or not it is typed.
        shapes |= set(self.graph.subjects(SH.targetClass, None))
        shapes |= set(self.graph.subjects(SH.targetSubjectsOf, None))
        shapes |= set(self.graph.subjects(SH.targetObjectsOf, None))
        shapes |= set(self.graph.subjects(SH.targetNode, None))
        live = []
        for s in shapes:
            if (s, SH.deactivated, Literal(True)) in self.graph:
                continue
            live.append(s)
        return sorted(live, key=str)

    def _build_subclass_closure(self) -> dict:
        """Map each class to the set of classes that are its subclasses (reflexive).

        SHACL sh:targetClass is subclass-aware (SHACL 2.1.3.1), so a shape
        targeting a superclass must match instances of its subclasses.
        """
        children = defaultdict(set)
        for source in (self.axioms, self.graph):
            for sub, _, sup in source.triples((None, RDFS.subClassOf, None)):
                if isinstance(sub, URIRef) and isinstance(sup, URIRef):
                    children[sup].add(sub)
        closure: dict = {}
        for parent in list(children):
            seen = {parent}
            stack = [parent]
            while stack:
                node = stack.pop()
                for child in children.get(node, ()):
                    if child not in seen:
                        seen.add(child)
                        stack.append(child)
            closure[parent] = seen
        return closure

    def subclasses_of(self, cls):
        return self.subclass_closure.get(cls, {cls})

    def constraint_count(self, shape, depth: int = 0, seen=None) -> int:
        """Number of SHACL constraint parameters reachable from `shape`.

        This is the runner's independent measure of "did anything actually get
        checked". It deliberately does not consult pyshacl's report, because a
        report with zero results is exactly what a vacuous validation produces.
        """
        if shape in self._constraint_cache and depth == 0:
            return self._constraint_cache[shape]
        if seen is None:
            seen = set()
        if shape in seen or depth > 8:
            return 0
        seen = seen | {shape}
        total = 0
        for pred, obj in self.graph.predicate_objects(shape):
            if pred in CONSTRAINT_PARAMS:
                total += 1
            if pred in NESTED_SHAPE_PARAMS and not isinstance(obj, Literal):
                total += self.constraint_count(obj, depth + 1, seen)
        if depth == 0:
            self._constraint_cache[shape] = total
        return total

    def match(self, data: Graph):
        """Return (matched pairs, constraint check count) for a data graph.

        Implements the SHACL target selectors the Cascade shapes actually use:
        sh:targetClass (subclass-aware), implicit class targets, sh:targetNode,
        sh:targetSubjectsOf and sh:targetObjectsOf.
        """
        pairs = set()
        checks = 0
        for shape in self.node_shapes:
            focus = set()
            targets = set(self.graph.objects(shape, SH.targetClass))
            if (shape, RDF.type, RDFS.Class) in self.graph:
                targets.add(shape)
            for cls in targets:
                for concrete in self.subclasses_of(cls):
                    focus |= set(data.subjects(RDF.type, concrete))
            for pred in self.graph.objects(shape, SH.targetSubjectsOf):
                focus |= set(data.subjects(pred, None))
            for pred in self.graph.objects(shape, SH.targetObjectsOf):
                focus |= set(data.objects(None, pred))
            for node in self.graph.objects(shape, SH.targetNode):
                if node in set(data.subjects(None, None)) or node in set(data.objects(None, None)):
                    focus.add(node)
            if not focus:
                continue
            per_shape = self.constraint_count(shape)
            for node in focus:
                pairs.add((shape, node))
            checks += per_shape * len(focus)
        return pairs, checks


def load_shapes(spec_dir: Path) -> Shapes:
    shape_paths = sorted(spec_dir.glob("ontologies/*/*/*.shapes.ttl"))
    if not shape_paths:
        abort(f"no *.shapes.ttl found under {spec_dir}/ontologies. Wrong --spec-dir?")
    graph = Graph()
    for path in shape_paths:
        try:
            graph.parse(path, format="turtle")
        except Exception as exc:
            # A shapes file that does not parse must stop the run. Continuing
            # would validate every fixture against a partial constraint set and
            # report the resulting silence as conformance.
            abort(f"shapes file {path.relative_to(spec_dir)} does not parse: "
                  f"{str(exc).replace(chr(10), ' ')[:200]}")

    ontology_paths = sorted(
        p for p in spec_dir.glob("ontologies/*/*/*.ttl") if not p.name.endswith(".shapes.ttl")
    )
    axioms = Graph()
    for path in ontology_paths:
        ont = Graph()
        try:
            ont.parse(path, format="turtle")
        except Exception as exc:
            abort(f"ontology {path.relative_to(spec_dir)} does not parse: "
                  f"{str(exc).replace(chr(10), ' ')[:200]}")
        for triple in ont.triples((None, RDFS.subClassOf, None)):
            axioms.add(triple)

    shapes = Shapes(
        graph,
        [str(p.relative_to(spec_dir)) for p in shape_paths],
        axioms,
        [str(p.relative_to(spec_dir)) for p in ontology_paths],
    )

    # Self-check 1: the shapes graph must not be empty.
    if len(graph) == 0:
        abort("shapes graph is empty. A runner with no shapes reports PASS on everything.")
    # Self-check 2: something must actually declare a target.
    targeted = [s for s in shapes.node_shapes if shapes.constraint_count(s) > 0]
    if not targeted:
        abort("no shape declares any constraint parameter. Nothing could ever be checked.")
    return shapes


def abort(message: str):
    sys.stderr.write(f"runner: SELF-CHECK FAILED: {message}\n")
    raise SystemExit(2)


# --------------------------------------------------------------------------
# Spec pin
# --------------------------------------------------------------------------

def read_pin(repo_root: Path) -> dict:
    pin_path = repo_root / "scripts" / "SPEC_PIN"
    values = {}
    for line in pin_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    if "commit" not in values:
        abort(f"{pin_path} does not define commit=")
    return values


def spec_head(spec_dir: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(spec_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# --------------------------------------------------------------------------
# Fixture discovery
# --------------------------------------------------------------------------

class Fixture:
    def __init__(self, fid, relpath, kind, positive, turtle, constraint_note, mode):
        self.id = fid
        self.relpath = relpath
        self.kind = kind
        self.positive = positive
        self.turtle = turtle
        self.constraint_note = constraint_note
        self.mode = mode
        self.outcome = None
        self.reason = None
        self.detail = ""
        self.checks = 0
        self.types = []
        self.violations = []


def discover(fixtures_dir: Path, schema: dict | None):
    """Walk fixtures/ and classify every file. Nothing is silently ignored."""
    fixtures = []
    non_rdf = []
    errors = []

    for path in sorted(fixtures_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(fixtures_dir))
        suffix = path.suffix.lower()

        if suffix == ".json":
            try:
                raw = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append((rel, R_READ_ERROR, str(exc)))
                continue
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append((rel, R_READ_ERROR, f"invalid JSON: {exc}"))
                continue
            if isinstance(doc, dict) and {"id", "shouldAccept", "expectedOutput"} <= set(doc):
                fixture = Fixture(
                    fid=str(doc["id"]),
                    relpath=rel,
                    kind="json",
                    positive=bool(doc["shouldAccept"]),
                    turtle=(doc.get("expectedOutput") or {}).get("turtle", ""),
                    constraint_note=doc.get("shaclConstraintViolated", ""),
                    mode=(doc.get("expectedOutput") or {}).get("validationMode", ""),
                )
                if schema is not None and jsonschema is not None:
                    try:
                        jsonschema.validate(doc, schema)
                    except jsonschema.ValidationError as exc:
                        fixture.outcome = "fail"
                        fixture.reason = R_SCHEMA_INVALID
                        fixture.detail = exc.message.split("\n")[0][:160]
                fixtures.append(fixture)
            else:
                non_rdf.append((rel, "converter input / expectation sidecar (JSON)"))
            continue

        if suffix == ".ttl":
            name = path.name
            if ".INVALID." in name:
                positive = False
            else:
                positive = True
            fixtures.append(
                Fixture(
                    fid=rel,
                    relpath=rel,
                    kind="ttl",
                    positive=positive,
                    turtle=None,  # read at execution time so read errors are reported per fixture
                    constraint_note="",
                    mode="shacl-valid",
                )
            )
            continue

        non_rdf.append((rel, NON_RDF_SUFFIXES.get(suffix, f"unrecognised file type '{suffix}'")))

    return fixtures, non_rdf, errors


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def base_uri(fixture: Fixture) -> str:
    """Stable base for relative IRIs (pod-* fixtures use `<>` as the subject)."""
    return f"https://conformance.cascadeprotocol.org/fixtures/{fixture.relpath}#"


def extract_violations(report: Graph, shapes: Shapes) -> list[str]:
    """Render each sh:Violation as a stable, human-readable constraint name."""
    out = set()
    for result in report.subjects(RDF.type, SH.ValidationResult):
        severity = report.value(result, SH.resultSeverity)
        if severity is not None and severity != SH.Violation:
            continue
        source = report.value(result, SH.sourceShape)
        component = report.value(result, SH.sourceConstraintComponent)
        path = report.value(result, SH.resultPath)
        focus = report.value(result, SH.focusNode)
        message = report.value(result, SH.resultMessage)

        shape_label = qname(source)
        if isinstance(source, BNode):
            parents = sorted(
                (p for p in shapes.graph.subjects(SH["property"], source) if isinstance(p, URIRef)),
                key=str,
            )
            if parents:
                shape_label = qname(parents[0])
        component_label = qname(component).replace("sh:", "")
        parts = [f"{shape_label}"]
        if path is not None:
            parts.append(f"path {qname(path)}")
        parts.append(component_label)
        line = " / ".join(parts)
        if message is not None:
            line += f' :: "{str(message).strip()[:100]}"'
        line += f"  [focus {qname(focus)}]"
        out.add(line)
    return sorted(out)


def run_fixture(fixture: Fixture, shapes: Shapes, fixtures_dir: Path):
    if fixture.outcome is not None:  # already failed schema validation
        return

    turtle = fixture.turtle
    if turtle is None:
        try:
            turtle = (fixtures_dir / fixture.relpath).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            fixture.outcome = "fail"
            fixture.reason = R_READ_ERROR
            fixture.detail = str(exc)[:160]
            return

    if not turtle.strip():
        fixture.outcome = "fail"
        fixture.reason = R_NO_TURTLE
        fixture.detail = (
            "expectedOutput.turtle is empty" if fixture.kind == "json" else "file is empty"
        )
        return

    if not any(line.strip() and not line.strip().startswith("#") for line in turtle.splitlines()):
        # Comment-only file. Quote its own first comment so the report explains itself.
        first = next(l.strip().lstrip("# ").strip() for l in turtle.splitlines() if l.strip())
        fixture.outcome = "fail"
        fixture.reason = R_NO_TURTLE
        fixture.detail = f"file is comment-only; it says: {first[:140]!r}"
        return

    data = Graph()
    try:
        data.parse(data=turtle, format="turtle", publicID=base_uri(fixture))
    except Exception as exc:  # rdflib raises a family of parse errors
        fixture.outcome = "fail"
        fixture.reason = R_PARSE_ERROR
        fixture.detail = str(exc).replace("\n", " ")[:200]
        return

    if len(data) == 0:
        fixture.outcome = "fail"
        fixture.reason = R_NO_TURTLE
        fixture.detail = "parsed to zero triples"
        return

    fixture.types = sorted({qname(t) for t in data.objects(None, RDF.type)})
    _pairs, checks = shapes.match(data)
    fixture.checks = checks

    if checks == 0:
        fixture.outcome = "fail"
        fixture.reason = R_UNSHAPED
        fixture.detail = "types present: " + (", ".join(fixture.types) or "(none)")
        return

    conforms, report, _text = pyshacl.validate(
        data,
        shacl_graph=shapes.graph,
        ont_graph=shapes.axioms,
        advanced=True,
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        debug=False,
    )
    fixture.violations = extract_violations(report, shapes)

    if fixture.positive:
        if conforms and not fixture.violations:
            fixture.outcome = "pass"
            fixture.reason = R_OK
        else:
            fixture.outcome = "fail"
            fixture.reason = R_VIOLATIONS
    else:
        if fixture.violations:
            fixture.outcome = "pass"
            fixture.reason = R_OK
        else:
            fixture.outcome = "fail"
            fixture.reason = R_NO_VIOLATION
            fixture.detail = (
                fixture.constraint_note.strip()[:160]
                or "fixture declares shouldAccept=false but nothing rejects it"
            )


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def build_report(fixtures, non_rdf, discovery_errors, shapes, pin, spec_actual, total_checks):
    lines = []
    add = lines.append

    add("Cascade Protocol conformance runner")
    add("=" * 72)
    add(f"  spec pin           : {pin['commit']}")
    if pin.get("vocab"):
        add(f"  pinned vocabulary  : {pin['vocab']}")
    add(f"  spec checkout HEAD : {spec_actual or '(not a git checkout)'}")
    add(f"  shapes files       : {len(shapes.files)}")
    add(f"  shapes triples     : {len(shapes.graph)}")
    add(f"  node shapes        : {len(shapes.node_shapes)}")
    add(f"  subclass axioms    : {len(shapes.axioms)} (from {len(shapes.axiom_files)} ontologies)")
    add("")

    kinds = defaultdict(int)
    for f in fixtures:
        kinds[f.kind] += 1
    add("Fixtures discovered")
    add("-" * 72)
    add(f"  conformance JSON   : {kinds['json']}")
    add(f"  RDF (.ttl)         : {kinds['ttl']}")
    add(f"  total executed     : {len(fixtures)}")
    add("")

    add(f"Not executed: {len(non_rdf)} file(s) under fixtures/ carry no RDF of their own.")
    add("  These are the source side of converter oracles and their sidecars. Each has a")
    add("  corresponding *.expected.ttl that IS executed. Grouped by reason:")
    grouped = defaultdict(list)
    for rel, why in non_rdf:
        grouped[why].append(rel)
    for why in sorted(grouped):
        add(f"    {len(grouped[why]):3d}  {why}")
    add("")

    passed = [f for f in fixtures if f.outcome == "pass"]
    failed = [f for f in fixtures if f.outcome == "fail"]
    skipped = [f for f in fixtures if f.outcome is None]

    add("Results")
    add("-" * 72)
    add(f"  passed             : {len(passed)}")
    add(f"  failed             : {len(failed)}")
    add(f"  skipped            : {len(skipped)}")
    add(f"  total              : {len(fixtures)}")
    add(f"  constraint checks  : {total_checks}")
    add("")

    if discovery_errors:
        add(f"Discovery errors: {len(discovery_errors)}")
        for rel, reason, detail in sorted(discovery_errors):
            add(f"  [{reason}] {rel}: {detail}")
        add("")

    by_reason = defaultdict(list)
    for f in failed:
        by_reason[f.reason].append(f)

    if failed:
        add(f"Failures: {len(failed)}")
        add("-" * 72)
        for reason in sorted(by_reason):
            group = sorted(by_reason[reason], key=lambda f: f.relpath)
            add(f"  {reason} ({len(group)}): {REASON_HELP.get(reason, '')}")
            for f in group:
                polarity = "positive" if f.positive else "negative"
                add(f"    - {f.relpath}  [{polarity}, {f.checks} constraint checks]")
                if f.detail:
                    add(f"        {f.detail}")
                for v in f.violations[:6]:
                    add(f"        violated: {v}")
                if len(f.violations) > 6:
                    add(f"        ... and {len(f.violations) - 6} more violations")
            add("")

    add("Passing fixtures by constraint checks evaluated (lowest first)")
    add("-" * 72)
    for f in sorted(passed, key=lambda f: (f.checks, f.relpath))[:10]:
        add(f"  {f.checks:5d}  {f.relpath}")
    if len(passed) > 10:
        add(f"  ... {len(passed) - 10} more")
    add("")

    verdict = "ALL FIXTURES PASSED" if not failed and not skipped else "SUITE HAS FAILURES"
    add(f"Verdict: {verdict}  ({len(passed)} passed / {len(failed)} failed / "
        f"{len(skipped)} skipped / {len(fixtures)} total)")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run every Cascade Protocol conformance fixture against the SHACL shapes."
    )
    parser.add_argument(
        "--spec-dir",
        default=os.environ.get("CASCADE_SPEC_DIR"),
        help="Path to a spec checkout. Defaults to $CASCADE_SPEC_DIR, then ../spec.",
    )
    parser.add_argument(
        "--allow-spec-drift",
        action="store_true",
        help="Permit a spec checkout whose HEAD differs from scripts/SPEC_PIN. "
             "Use only when deliberately testing against unreleased vocabulary.",
    )
    parser.add_argument(
        "--select", action="append", default=None, metavar="GLOB",
        help="Only run fixtures whose path matches GLOB (repeatable). Debugging aid. "
             "CI always runs the full suite.",
    )
    parser.add_argument(
        "--fixtures-dir", default=None, metavar="DIR",
        help="Fixture tree to execute. Defaults to fixtures/ next to this script's repo. "
             "Only scripts/selftest_runner.py overrides this, to run deliberately mutated copies.",
    )
    parser.add_argument("--json", dest="json_out", metavar="PATH", help="Write machine-readable results.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the text report.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    fixtures_dir = Path(args.fixtures_dir).resolve() if args.fixtures_dir else repo_root / "fixtures"
    if not fixtures_dir.is_dir():
        abort(f"fixtures directory not found at {fixtures_dir}")

    pin = read_pin(repo_root)

    spec_dir = Path(args.spec_dir).resolve() if args.spec_dir else (repo_root.parent / "spec")
    if not spec_dir.is_dir():
        abort(
            f"spec checkout not found at {spec_dir}. Pass --spec-dir or set CASCADE_SPEC_DIR. "
            f"The pinned commit is {pin['commit']}."
        )

    actual = spec_head(spec_dir)
    if actual and actual != pin["commit"] and not args.allow_spec_drift:
        abort(
            f"spec checkout is at {actual} but scripts/SPEC_PIN expects {pin['commit']}.\n"
            "  Re-pin deliberately (edit scripts/SPEC_PIN) or pass --allow-spec-drift.\n"
            "  An unpinned runner silently tracks a moving vocabulary."
        )

    shapes = load_shapes(spec_dir)

    schema = None
    schema_path = repo_root / "schema" / "fixture-schema.json"
    if schema_path.is_file() and jsonschema is not None:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

    fixtures, non_rdf, discovery_errors = discover(fixtures_dir, schema)

    if args.select:
        fixtures = [
            f for f in fixtures
            if any(fnmatch.fnmatch(f.relpath, pat) for pat in args.select)
        ]

    if not fixtures:
        abort("zero fixtures discovered. A suite with no fixtures cannot fail.")

    for fixture in fixtures:
        run_fixture(fixture, shapes, fixtures_dir)

    total_checks = sum(f.checks for f in fixtures)

    # Self-check 3: if the whole suite evaluated zero constraints, every PASS in
    # it is vacuous. That is the defect this runner exists to prevent.
    if total_checks == 0:
        abort(
            "zero constraint checks evaluated across the entire suite. "
            "Any PASS reported here would be meaningless."
        )

    fixtures.sort(key=lambda f: f.relpath)
    report = build_report(fixtures, non_rdf, discovery_errors, shapes, pin, actual, total_checks)

    if not args.quiet:
        print(report)

    if args.json_out:
        payload = {
            "specPin": pin["commit"],
            "shapesFiles": shapes.files,
            "constraintChecks": total_checks,
            "counts": {
                "passed": sum(1 for f in fixtures if f.outcome == "pass"),
                "failed": sum(1 for f in fixtures if f.outcome == "fail"),
                "skipped": sum(1 for f in fixtures if f.outcome is None),
                "total": len(fixtures),
                "notExecuted": len(non_rdf),
            },
            "fixtures": [
                {
                    "path": f.relpath,
                    "id": f.id,
                    "polarity": "positive" if f.positive else "negative",
                    "outcome": f.outcome,
                    "reason": f.reason,
                    "constraintChecks": f.checks,
                    "types": f.types,
                    "violations": f.violations,
                    "detail": f.detail,
                }
                for f in fixtures
            ],
        }
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    failures = sum(1 for f in fixtures if f.outcome != "pass")
    return 1 if (failures or discovery_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
