# Cascade Protocol Conformance Test Suite

Version: 1.1
Date: 2026-08-03

## Overview

The Cascade Protocol Conformance Test Suite validates that SDK implementations correctly serialize health data to RDF/Turtle format according to the Cascade Protocol specification. It provides a standardized set of test fixtures that any SDK (Swift, Python, JavaScript, etc.) can run against to verify conformance.

The suite also ships its own runner (`scripts/run_conformance.py`), which executes every fixture against the SHACL shapes published by `spec`. See [Running the suite](#running-the-suite) and [Current status](#current-status).

### Record fixtures (`fixtures/*.json`)

Every count below is derived from the fixture files themselves, not maintained by hand.

| Data Type | Fixture Prefix | Count | Description |
|---|---|---|---|
| Medication | `med-` | 11 | Prescription drugs, OTC medications |
| Condition | `cond-` | 7 | Medical conditions, diagnoses |
| Lab Result | `lab-` | 7 | Laboratory test observations |
| Vital Sign | `vital-` | 7 | Clinical vital sign observations |
| Allergy | `allergy-` | 6 | Allergies and intolerances |
| Patient Profile | `profile-` | 5 | Demographics and identity |
| Coverage | `coverage-` | 4 | Insurance and coverage |
| Pod Structure | `pod-` | 4 | LDP containers and manifests |
| Immunization | `imm-` | 3 | Vaccine records |
| Family History | `fam-` | 3 | Family medical history |
| Procedure | `proc-` | 3 | Procedures and surgical history |
| Social History | `social-` | 2 | Consumer-reported social/behavioral history (health v2.4) |
| Proxy Agent | `proxy-` | 2 | Caregiver-proxy actor operating a patient's Pod (core v3.3) |
| Benefit Statement | `benefit-` | 1 | Explanation of benefits |
| Claim Record | `claim-` | 1 | Insurance claim records |
| Denial Notice | `denial-` | 1 | Coverage denial notices |
| Implanted Device | `device-` | 1 | Implanted medical devices |
| Encounter | `encounter-` | 1 | Clinical encounters and visits |
| Imaging Study | `imaging-` | 1 | Imaging studies and results |
| Medication Administration | `medadmin-` | 1 | Medication administration events |
| **Total** | | **71** | 20 data types |

### RDF fixtures (`fixtures/**/*.ttl`)

40 further fixtures are Turtle files rather than JSON records. They carry their polarity in the filename (`*.INVALID.ttl` is a negative fixture, everything else is positive) and are executed by the same runner.

| Directory | Count | Positive | Negative | What it covers |
|---|---|---|---|---|
| `genomics/phenopackets/` | 9 | 9 | 0 | GA4GH Phenopacket conversion oracles |
| `genomics/fhir-genomics-ig/` | 7 | 7 | 0 | HL7 Genomics Reporting IG bundle conversion oracles |
| `evidence/` | 7 | 3 | 4 | Assertion facet / evidence grounding rules (evidence v1-draft) |
| `workbench/` | 7 | 4 | 3 | Filing, notes and follow-ups (workbench v1-draft) |
| `genomics/clinvar/` | 4 | 4 | 0 | ClinVar VCV conversion oracles |
| `advisory/` | 2 | 2 | 0 | Advisory reclassification oracles (advisory v1-draft) |
| `clinical/` | 1 | 1 | 0 | Social history in Turtle form |
| `core/` | 1 | 1 | 0 | AIExtracted provenance in Turtle form |
| `genomics/vcf/` | 1 | 1 | 0 | VCF conversion oracle |
| `genomics/vrs/` | 1 | 1 | 0 | GA4GH VRS allele conversion oracle |
| **Total** | **40** | **33** | **7** | |

**Grand total: 111 executable fixtures.**

A further 92 files under `fixtures/` are the source side of those conversion oracles (`*.input.xml`, `*.input.json`, `*.input.ldpatch`, `*.input.vcf.gz`), their `*.gaps.json` sidecars, and `INVENTORY.md` files. They carry no RDF of their own, so the SHACL runner does not execute them; each has a corresponding `*.expected.ttl` that it does execute. The runner reports them by category on every run so the number is auditable rather than assumed.

## Running the suite

```bash
python3 -m pip install -r scripts/requirements.txt

# Clone the pinned spec revision (see scripts/SPEC_PIN for the commit)
git clone https://github.com/the-cascade-protocol/spec.git ../spec
git -C ../spec checkout "$(grep '^commit=' scripts/SPEC_PIN | cut -d= -f2)"

python3 scripts/run_conformance.py --spec-dir ../spec
```

`--spec-dir` also reads from `$CASCADE_SPEC_DIR`, and defaults to `../spec`. Useful flags: `--json PATH` writes machine-readable results, `--select GLOB` restricts the run while debugging (CI never uses it), `--quiet` suppresses the text report.

Exit codes: `0` every fixture passed, `1` one or more failed, `2` the runner's own self-checks failed and no fixture result should be believed.

### What the runner actually does

There is no SDK under test here, so the runner takes the second of the two mechanisms described under [Testing Strategy](#testing-strategy): it validates the Turtle each fixture declares (`expectedOutput.turtle` for a JSON fixture, the file body for a `.ttl` fixture) against the union of every `*.shapes.ttl` in the pinned `spec` checkout.

Loading all shapes at once rather than one file per `vocabulary` field is deliberate. A single record routinely spans namespaces (a `clinical:Medication` also carries `cascade:` provenance), and SHACL only fires a shape whose target actually matches, so a wider shapes graph can only ever evaluate more constraints, never fewer.

`rdfs:subClassOf` axioms are extracted from the ontology files and supplied as the ontology graph, because `sh:targetClass` is subclass-aware ([SHACL 2.1.3.1](https://www.w3.org/TR/shacl/#targetClass)). Only the subclass triples are mixed in, not whole ontologies, so ontology terms cannot themselves become focus nodes.

### Why a fixture with no applicable shape is a failure, not a pass

Validating a record whose class no shape targets returns `conforms = true` after evaluating zero constraints. That result is indistinguishable from real conformance, and it is the failure mode this runner exists to prevent.

So the runner computes, independently of the SHACL engine, how many constraint parameters were reachable from a matched focus node, and reports `UNSHAPED` when that count is zero. Failure reasons are:

| Reason | Meaning |
|---|---|
| `VIOLATIONS` | Positive fixture; the shapes reported at least one `sh:Violation` |
| `NO_VIOLATION` | Negative fixture; the shapes reported none, so nothing rejected it |
| `UNSHAPED` | No shape targets any subject, so zero constraints ran |
| `NO_TURTLE` | The fixture declares no RDF body, so there is nothing to validate |
| `PARSE_ERROR` | The fixture's RDF does not parse |
| `READ_ERROR` | The file could not be read or decoded |
| `SCHEMA_INVALID` | The fixture JSON does not satisfy `schema/fixture-schema.json` |

The runner aborts the whole run (exit 2) rather than reporting anything if the shapes graph is empty, if a shapes or ontology file fails to parse, if no shape declares a constraint, or if zero constraints were evaluated across the entire suite. Each of those is a way a runner can report PASS while testing nothing.

`scripts/selftest_runner.py` is the proof that the above holds. It mutates fixtures and shapes in temporary directories and asserts the runner notices: that breaking one constraint produces exactly one violation naming that constraint, that repairing a negative fixture is reported as unexpectedly conforming, and that deleting a shape yields `UNSHAPED` rather than `PASS`. No mutated copy is ever written inside the repository. Run it with `python3 scripts/selftest_runner.py --spec-dir ../spec`.

### The spec pin

`scripts/SPEC_PIN` names the exact `spec` commit the suite is validated against, and the runner refuses to run against any other checkout. Without a pin the suite silently tracks whatever is on `spec` `main`, so a run that passed yesterday can pass today for a different reason, or start failing because of a vocabulary change nobody in this repository chose to adopt.

To re-pin:

1. Check out the new `spec` revision and note its full SHA and its `VOCAB_VERSIONS` line.
2. Update `commit=` and `vocab=` in `scripts/SPEC_PIN`.
3. Run `python3 scripts/run_conformance.py --spec-dir ../spec` and record the before and after counts in the pull request. A re-pin that changes the pass count is a vocabulary change with consequences, and the pull request should say what they are.
4. Update `VOCAB_VERSIONS` at the repository root only once fixtures actually cover the new vocabulary. The pin and `VOCAB_VERSIONS` answer different questions: the pin says what the shapes came from, `VOCAB_VERSIONS` says what the fixtures cover.

`--allow-spec-drift` bypasses the check for local experiments against unreleased vocabulary. CI never passes it.

### Continuous integration

`.github/workflows/conformance.yml` runs on every push to `main` and every pull request, in two jobs:

- **runner mutation tests** runs `scripts/selftest_runner.py`. This job is green and must stay green. If it goes red, no result from the other job means anything.
- **fixture suite** runs every fixture. This job is currently red; see below.

## Current status

As of the pinned revision in `scripts/SPEC_PIN` (`spec` at core 3.3, health 2.4, clinical 1.12):

```
passed  43
failed  68
skipped  0
total   111        60,212 constraint checks evaluated
```

This is the first time these fixtures have been executed by anything. The 68 failures are pre-existing and were latent, not caused by the runner. They break down as:

| Reason | Count | Notes |
|---|---|---|
| `UNSHAPED` | 27 | 21 of these are `health:LabResultRecord`, `health:ConditionRecord`, `health:AllergyRecord`, `health:ImmunizationRecord`, `health:FamilyHistoryRecord` and `health:ProcedureRecord`, which are asserted by fixtures but not defined as classes or targeted by any shape. The rest are `clinical:Encounter`, `clinical:ImplantedDevice`, `clinical:MedicationAdministration`, `clinical:CoverageRecord`, `coverage:DenialNotice`, `ldp:BasicContainer`, `cascade:ExportManifest` and `cascade:RecordSummary`. |
| `NO_TURTLE` | 22 | 19 negative fixtures declare `expectedOutput.turtle: ""`. A shapes-only runner can only exercise the post-validation path, which needs the invalid serialization to exist. The other 3 are comment-only placeholder `.ttl` files. |
| `VIOLATIONS` | 16 | Conversion oracles under `fixtures/genomics/` and one under `fixtures/core/` whose expected output does not satisfy the shapes it is supposed to produce. |
| `PARSE_ERROR` | 3 | `benefit-001`, `claim-001` and `imaging-001` contain Turtle that no parser accepts: a numeric literal cannot carry an explicit datatype (`450.00^^xsd:decimal` must be `"450.00"^^xsd:decimal`). |

One further file, `fixtures/genomics/vrs/example-allele-BRCA2-deletion.input.json`, is not valid JSON (it opens with `#` comment lines), and is reported as a discovery error.

**These failures must not be resolved by weakening the runner.** Do not skip a fixture, relax an assertion, or add a baseline of known failures. A runner that passes everything on its first run is a runner that tests nothing, which is the state this repository was in before it had one. Fix the fixture or fix the vocabulary.

The two directories that pass cleanly, `fixtures/evidence/` (7 of 7) and `fixtures/workbench/` (7 of 7), are worth noting: both include negative fixtures that the shapes correctly reject, which is what a healthy fixture set looks like.

## Fixture Format

Each fixture is a JSON file conforming to `schema/fixture-schema.json`. Here is an annotated example:

```json
{
  "id": "med-001",
  "description": "Happy path: Active prescription medication (Lisinopril) with core required fields from EHR import",
  "dataType": "Medication",
  "vocabulary": "clinical",
  "input": {
    "id": "urn:uuid:med0-0001-aaaa-bbbb-ccccddddeeee",
    "type": "MedicationRecord",
    "medicationName": "Lisinopril",
    "isActive": true,
    "dataProvenance": "ClinicalGenerated",
    "schemaVersion": "1.3",
    "dose": "20 mg",
    "frequency": "once daily",
    "route": "oral",
    "provenanceClass": "healthKitFHIR"
  },
  "expectedOutput": {
    "turtle": "@prefix cascade: <https://ns.cascadeprotocol.org/core/v1#> ...",
    "validationMode": "shacl-valid"
  },
  "shouldAccept": true,
  "tags": ["happy-path", "clinical", "ehr-import"]
}
```

### Field Reference

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique fixture ID in format `{prefix}-{number}` (e.g., `med-001`) |
| `description` | Yes | Human-readable description of what this fixture tests |
| `dataType` | Yes | One of: `Medication`, `Condition`, `Allergy`, `LabResult`, `VitalSign`, `PatientProfile`, `Immunization`, `Coverage`, `PodStructure`, `SocialHistoryRecord`, `ProxyAgent`, ... (full enum in `schema/fixture-schema.json`) |
| `vocabulary` | Yes | Primary namespace: `health`, `clinical`, `core`, `coverage`, `cascade` |
| `input` | Yes | Plain JSON object representing the data an SDK would receive before serialization |
| `expectedOutput.turtle` | Yes | Expected RDF/Turtle output with namespace prefix declarations |
| `expectedOutput.validationMode` | Yes | `shacl-valid` or `exact-match` |
| `shouldAccept` | Yes | `true` for valid inputs, `false` for inputs that should be rejected |
| `tags` | Yes | Array of classification tags for filtering |
| `shaclConstraintViolated` | Conditional | Required when `shouldAccept` is `false`; describes which SHACL constraint is violated |
| `notes` | No | Optional explanatory notes |

### Input JSON Format

The `input` field represents data as a plain JSON object that an SDK would receive before serialization. Field names use camelCase mappings of the Turtle predicates:

- `clinical:drugName` becomes `medicationName`
- `cascade:dataProvenance` becomes `dataProvenance` (value is the local name, e.g., `"ClinicalGenerated"`)
- `cascade:schemaVersion` becomes `schemaVersion`
- `clinical:drugCode` (multiple values) becomes `drugCodes` (array of URIs)
- `health:affectsVitalSigns` (RDF list) becomes `affectsVitalSigns` (array of strings)

Nested blank nodes (e.g., emergency contacts, addresses) are represented as nested JSON objects.

### Namespace Prefixes

All Turtle output uses these canonical namespace prefixes:

```turtle
@prefix cascade: <https://ns.cascadeprotocol.org/core/v1#> .
@prefix health:  <https://ns.cascadeprotocol.org/health/v1#> .
@prefix clinical: <https://ns.cascadeprotocol.org/clinical/v1#> .
@prefix coverage: <https://ns.cascadeprotocol.org/coverage/v1#> .
@prefix fhir:    <http://hl7.org/fhir/> .
@prefix sct:     <http://snomed.info/sct/> .
@prefix loinc:   <http://loinc.org/rdf#> .
@prefix rxnorm:  <http://www.nlm.nih.gov/research/umls/rxnorm/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
```

## Running Fixtures Against an SDK

The pseudocode below is for SDK implementers wiring these fixtures into their own test suite. It is not what `scripts/run_conformance.py` does: that runner has no SDK to call, so it takes the post-validation branch only. See [What the runner actually does](#what-the-runner-actually-does).

### General Algorithm

```
for each fixture file in fixtures/:
    fixture = parse JSON file

    if fixture.shouldAccept:
        # Positive test case
        output = sdk.serialize(fixture.input)

        if fixture.expectedOutput.validationMode == "shacl-valid":
            assert shacl_validate(output, appropriate_shapes_file) has no Violations
        else if fixture.expectedOutput.validationMode == "exact-match":
            assert normalize(output) == normalize(fixture.expectedOutput.turtle)
    else:
        # Negative test case
        assert sdk.serialize(fixture.input) raises ValidationError
        # OR
        output = sdk.serialize(fixture.input)
        assert shacl_validate(output, appropriate_shapes_file) reports Violation
```

### Pseudocode (Python)

```python
import json
import glob
from pathlib import Path

def run_conformance_suite(sdk, shapes_dir, fixtures_dir):
    """Run all conformance fixtures against an SDK implementation."""
    results = {"passed": 0, "failed": 0, "errors": []}

    for fixture_path in sorted(glob.glob(f"{fixtures_dir}/*.json")):
        with open(fixture_path) as f:
            fixture = json.load(f)

        try:
            if fixture["shouldAccept"]:
                # Serialize the input
                turtle_output = sdk.serialize(
                    data_type=fixture["dataType"],
                    data=fixture["input"]
                )

                if fixture["expectedOutput"]["validationMode"] == "shacl-valid":
                    # Validate against SHACL shapes
                    shapes_file = get_shapes_file(fixture["vocabulary"], shapes_dir)
                    violations = shacl_validate(turtle_output, shapes_file)
                    assert len(violations) == 0, f"SHACL violations: {violations}"

                elif fixture["expectedOutput"]["validationMode"] == "exact-match":
                    # Normalize and compare
                    expected = normalize_turtle(fixture["expectedOutput"]["turtle"])
                    actual = normalize_turtle(turtle_output)
                    assert expected == actual, f"Output mismatch"

                results["passed"] += 1
            else:
                # Negative test: expect failure
                try:
                    turtle_output = sdk.serialize(
                        data_type=fixture["dataType"],
                        data=fixture["input"]
                    )
                    # If serialization succeeds, SHACL validation should fail
                    shapes_file = get_shapes_file(fixture["vocabulary"], shapes_dir)
                    violations = shacl_validate(turtle_output, shapes_file)
                    assert len(violations) > 0, \
                        f"Expected SHACL violation: {fixture['shaclConstraintViolated']}"
                    results["passed"] += 1
                except ValidationError:
                    # SDK correctly rejected invalid input
                    results["passed"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "fixture": fixture["id"],
                "error": str(e)
            })

    return results

def get_shapes_file(vocabulary, shapes_dir):
    """Map vocabulary to SHACL shapes file."""
    mapping = {
        "health": "health.shapes.ttl",
        "clinical": "clinical.shapes.ttl",
        "core": "core.shapes.ttl",
        "coverage": "coverage.shapes.ttl",
        "cascade": "core.shapes.ttl",
    }
    return Path(shapes_dir) / mapping[vocabulary]
```

### Pseudocode (Swift)

```swift
func runConformanceSuite(fixtures: [URL], serializer: CascadeSerializer) -> TestResults {
    var results = TestResults()

    for fixtureURL in fixtures {
        let fixture = try JSONDecoder().decode(ConformanceFixture.self, from: Data(contentsOf: fixtureURL))

        if fixture.shouldAccept {
            // Positive test: serialization should succeed and output should be SHACL-valid
            let turtleOutput = try serializer.serialize(dataType: fixture.dataType, input: fixture.input)

            switch fixture.expectedOutput.validationMode {
            case .shaclValid:
                let violations = SHACLValidator.validate(turtleOutput, shapes: shapesFile(for: fixture.vocabulary))
                XCTAssertTrue(violations.isEmpty, "Fixture \(fixture.id): \(violations)")
            case .exactMatch:
                let expected = normalizeTurtle(fixture.expectedOutput.turtle)
                let actual = normalizeTurtle(turtleOutput)
                XCTAssertEqual(expected, actual, "Fixture \(fixture.id): output mismatch")
            }
            results.passed += 1
        } else {
            // Negative test: serialization should fail or produce SHACL-invalid output
            XCTAssertThrowsError(try serializer.serialize(dataType: fixture.dataType, input: fixture.input))
            results.passed += 1
        }
    }
    return results
}
```

## Normalization Algorithm for Exact-Match Mode

When `validationMode` is `"exact-match"`, the test runner must normalize both the expected and actual Turtle output before comparison. This prevents false failures due to whitespace differences, triple ordering, or blank node label differences.

The normalization algorithm follows **RDFC-1.0** (RDF Dataset Canonicalization):

### Steps

1. **Parse to quads.** Parse both Turtle strings into sets of RDF quads (subject, predicate, object, graph). Use any standards-compliant Turtle parser.

2. **Canonicalize blank nodes.** Apply the RDFC-1.0 algorithm (formerly URDNA2015) to assign deterministic identifiers to blank nodes. This ensures that blank node labels like `_:b0` and `_:b1` are assigned consistently based on the graph structure, not the order they appear in the serialization.

3. **Sort triples.** Sort all quads lexicographically by (subject, predicate, object, graph). For URI terms, sort by the full URI string. For literals, sort by (value, datatype, language tag).

4. **Normalize whitespace.** Remove trailing whitespace from each line. Normalize line endings to `\n`. Remove empty lines between triples.

5. **Compare.** The normalized quad sets must be identical.

### Reference Implementations

- **JavaScript:** Use the `rdf-canonize` npm package (implements RDFC-1.0)
- **Python:** Use `rdflib` with `rdflib.compare.isomorphic()` for graph comparison
- **Java:** Use Apache Jena's `IsoMatcher` for graph isomorphism
- **Swift:** Parse with a Turtle parser and compare sorted triple sets

### Example

Given two serializations of the same data:

```turtle
# Serialization A
<urn:uuid:abc> a clinical:Medication ;
    clinical:drugName "Aspirin" ;
    clinical:status "active" .

# Serialization B (different triple order, extra whitespace)
<urn:uuid:abc> clinical:status "active" ;
    a clinical:Medication ;
    clinical:drugName "Aspirin" .
```

After normalization, both produce the same canonical form and the comparison passes.

## Negative Test Cases

Negative fixtures (`shouldAccept: false`) verify that an SDK correctly rejects invalid input or produces output that fails SHACL validation. Each negative fixture includes a `shaclConstraintViolated` field describing which constraint is violated.

### Derivation from SHACL Shapes

Negative test cases are systematically derived from the SHACL shapes files:

1. **Required field violations:** For each `sh:minCount 1` constraint, create a fixture missing that field.
   - Example: `med-008` omits `medicationName` (maps to `clinical:drugName`, required by `MedicationShape`)

2. **Pattern violations:** For each `sh:pattern` constraint, create a fixture with an invalid format.
   - Example: `med-010` uses `schemaVersion: "1"` instead of `"1.3"` (violates `^[0-9]+\.[0-9]+$`)

3. **Enumeration violations:** For each `sh:in` constraint, create a fixture with a value not in the allowed list.
   - Example: `vital-007` uses `vitalType: "painScore"` (not in the enumerated vital types)

4. **Length violations:** For each `sh:minLength` constraint, create a fixture with an empty string.
   - Example: `allergy-006` uses `allergen: ""` (violates `sh:minLength 1`)

### SHACL Shapes Reference

The SHACL shapes files that define validation constraints live in the `spec` repository, at the commit named in `scripts/SPEC_PIN`:

- `ontologies/clinical/v1/clinical.shapes.ttl` -- Medication, Allergy, LabResult, Condition, VitalSign, Immunization
- `ontologies/health/v1/health.shapes.ttl` -- HealthProfile, wellness statistics
- `ontologies/core/v1/core.shapes.ttl` -- PatientProfile, Address, EmergencyContact, PharmacyInfo, ProxyAgent
- `ontologies/coverage/v1/coverage.shapes.ttl` -- InsurancePlan
- `ontologies/{advisory,evidence,genomics,workbench}/v1-draft/*.shapes.ttl` -- draft vocabularies exercised by the RDF fixtures

The runner loads all of them. Ten shapes files, 5,485 triples, 99 node shapes at the pinned revision.

### Testing Strategy

SDKs may handle negative cases in two ways:

1. **Pre-validation:** The SDK validates input before serialization and throws a `ValidationError` (or equivalent) for invalid data. The test passes if the error is raised.

2. **Post-validation:** The SDK serializes the data regardless, and a SHACL validator detects the violation. The test passes if SHACL validation reports at least one `sh:Violation`.

Both approaches are acceptable. The conformance suite verifies the outcome (invalid data is detected), not the mechanism.

## Coverage Matrix

Categories per data type, for the 71 record fixtures. Each fixture carries exactly one of these five tags, so the columns sum to the row total. Counts are derived from the fixtures' own `tags` arrays.

| Data Type | Happy Path | Full Fields | Multi-Code | Provenance | Negative | Total |
|---|---|---|---|---|---|---|
| Medication | 2 | 1 | 2 | 3 | 3 | 11 |
| Condition | 2 | 1 | 1 | 1 | 2 | 7 |
| Lab Result | 2 | 1 | 1 | 1 | 2 | 7 |
| Vital Sign | 2 | 1 | 1 | 1 | 2 | 7 |
| Allergy | 2 | 1 | -- | 1 | 2 | 6 |
| Patient Profile | 1 | 1 | -- | 1 | 2 | 5 |
| Coverage | 1 | 1 | -- | 1 | 1 | 4 |
| Pod Structure | 2 | -- | -- | -- | 2 | 4 |
| Immunization | 2 | -- | -- | -- | 1 | 3 |
| Family History | 1 | 1 | -- | -- | 1 | 3 |
| Procedure | 1 | 1 | -- | -- | 1 | 3 |
| Social History | 1 | 1 | -- | 1 | -- | 2 |
| Proxy Agent | 1 | -- | -- | -- | 1 | 2 |
| Benefit Statement | 1 | -- | -- | -- | -- | 1 |
| Claim Record | 1 | -- | -- | -- | -- | 1 |
| Denial Notice | 1 | -- | -- | -- | -- | 1 |
| Implanted Device | 1 | -- | -- | -- | -- | 1 |
| Encounter | 1 | -- | -- | -- | -- | 1 |
| Imaging Study | 1 | -- | -- | -- | -- | 1 |
| Medication Administration | 1 | -- | -- | -- | -- | 1 |
| **Total** | **27** | **10** | **5** | **10** | **20** | **71** |

The 40 RDF fixtures are not tagged this way; their split is 33 positive and 7 negative, tabulated above.

### Tag Descriptions

- **happy-path**: Minimal valid record with required fields and common optional fields
- **full-fields**: Record with all possible properties populated
- **multi-code**: Record with multiple terminology system codes (e.g., RxNorm + SNOMED CT)
- **provenance**: Tests specific provenance scenarios (EHRVerified, SelfReported, DeviceGenerated)
- **negative**: Invalid input that should be rejected or fail SHACL validation
- **required-field**: Negative test missing a required field (`sh:minCount 1`)
- **enum-constraint**: Negative test with an invalid enumerated value (`sh:in`)
- **pattern-constraint**: Negative test with an invalid format (`sh:pattern` or `sh:minLength`)

## Data Sources

Test data is derived from two sources:

1. **Reference Patient Pod** (`reference-patient-pod/`): Realistic synthetic patient data for Alex Rivera, a 52-year-old male with hypertension, diabetes, asthma, and hyperlipidemia. Positive fixtures extract real records from these TTL files.

2. **SHACL Shapes Files** (`docs/*/v1/*.shapes.ttl`): Machine-readable validation constraints. Negative fixtures are systematically derived by violating each `sh:Violation`-severity constraint.

## Adding New Fixtures

To add a new fixture:

1. Create a JSON file in `fixtures/` following the naming convention `{prefix}-{NNN}.json`
2. Validate the fixture against `schema/fixture-schema.json`
3. For positive fixtures, ensure the Turtle output is SHACL-valid against the appropriate shapes file
4. For negative fixtures, include the `shaclConstraintViolated` field **and** populate `expectedOutput.turtle` with the invalid serialization. An empty `turtle` gives a shapes-based runner nothing to reject, which is why 19 existing negative fixtures currently fail.
5. Update the coverage matrix in this README
6. Run `python3 scripts/run_conformance.py --spec-dir ../spec` and confirm the new fixture is reported, with a non-zero constraint check count. A new fixture that lands in `UNSHAPED` is not testing anything yet.

Fixture IDs must be unique and follow the pattern `^[a-z]+-[0-9]{3}$`.
