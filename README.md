# Cascade Protocol Conformance Test Suite

Version: 1.0
Date: 2026-02-19

## Overview

The Cascade Protocol Conformance Test Suite validates that SDK implementations correctly serialize health data to RDF/Turtle format according to the Cascade Protocol specification. It provides a standardized set of test fixtures that any SDK (Swift, Python, JavaScript, etc.) can run against to verify conformance.

The suite covers all Phase 1 data types:

| Data Type | Fixture Prefix | Count | Description |
|---|---|---|---|
| Medication | `med-` | 10 | Prescription drugs, OTC medications |
| Condition | `cond-` | 7 | Medical conditions, diagnoses |
| Allergy | `allergy-` | 6 | Allergies and intolerances |
| Lab Result | `lab-` | 7 | Laboratory test observations |
| Vital Sign | `vital-` | 7 | Clinical vital sign observations |
| Patient Profile | `profile-` | 5 | Demographics and identity |
| Immunization | `imm-` | 3 | Vaccine records |
| Coverage | `coverage-` | 4 | Insurance and coverage |
| Pod Structure | `pod-` | 4 | LDP containers and manifests |
| **Total** | | **53** | |

## Fixture Format

Each fixture is a JSON file conforming to `schema/fixture-schema.json`. Here is an annotated example:

```json
{
  "id": "med-001",
  "description": "Happy path: Active prescription medication (Lisinopril) with core required fields from EHR import",
  "dataType": "Medication",
  "vocabulary": "health",
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
| `dataType` | Yes | One of: `Medication`, `Condition`, `Allergy`, `LabResult`, `VitalSign`, `PatientProfile`, `Immunization`, `Coverage`, `PodStructure` |
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

- `health:medicationName` becomes `medicationName`
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
<urn:uuid:abc> a health:MedicationRecord ;
    health:medicationName "Aspirin" ;
    health:isActive true .

# Serialization B (different triple order, extra whitespace)
<urn:uuid:abc> health:isActive true ;
    a health:MedicationRecord ;
    health:medicationName "Aspirin" .
```

After normalization, both produce the same canonical form and the comparison passes.

## Negative Test Cases

Negative fixtures (`shouldAccept: false`) verify that an SDK correctly rejects invalid input or produces output that fails SHACL validation. Each negative fixture includes a `shaclConstraintViolated` field describing which constraint is violated.

### Derivation from SHACL Shapes

Negative test cases are systematically derived from the SHACL shapes files:

1. **Required field violations:** For each `sh:minCount 1` constraint, create a fixture missing that field.
   - Example: `med-008` omits `medicationName` (required by `MedicationShape`)

2. **Pattern violations:** For each `sh:pattern` constraint, create a fixture with an invalid format.
   - Example: `med-010` uses `schemaVersion: "1"` instead of `"1.3"` (violates `^[0-9]+\.[0-9]+$`)

3. **Enumeration violations:** For each `sh:in` constraint, create a fixture with a value not in the allowed list.
   - Example: `vital-007` uses `vitalType: "painScore"` (not in the enumerated vital types)

4. **Length violations:** For each `sh:minLength` constraint, create a fixture with an empty string.
   - Example: `allergy-006` uses `allergen: ""` (violates `sh:minLength 1`)

### SHACL Shapes Reference

The SHACL shapes files that define validation constraints are located at:

- `docs/clinical/v1/clinical.shapes.ttl` -- Medication, Allergy, LabResult, Condition, VitalSign, Immunization
- `docs/health/v1/health.shapes.ttl` -- HealthProfile, wellness statistics
- `docs/core/v1/core.shapes.ttl` -- PatientProfile, Address, EmergencyContact, PharmacyInfo
- `docs/coverage/v1/coverage.shapes.ttl` -- InsurancePlan

### Testing Strategy

SDKs may handle negative cases in two ways:

1. **Pre-validation:** The SDK validates input before serialization and throws a `ValidationError` (or equivalent) for invalid data. The test passes if the error is raised.

2. **Post-validation:** The SDK serializes the data regardless, and a SHACL validator detects the violation. The test passes if SHACL validation reports at least one `sh:Violation`.

Both approaches are acceptable. The conformance suite verifies the outcome (invalid data is detected), not the mechanism.

## Coverage Matrix

The fixture suite covers these test categories per data type:

| Data Type | Happy Path | Full Fields | Multi-Code | Provenance | Negative | Total |
|---|---|---|---|---|---|---|
| Medication | 2 | 1 | 2 | 2 | 3 | 10 |
| Condition | 2 | 1 | 1 | 1 | 2 | 7 |
| Allergy | 2 | 1 | -- | 1 | 2 | 6 |
| Lab Result | 2 | 1 | 1 | 1 | 2 | 7 |
| Vital Sign | 2 | 1 | 1 | 1 | 2 | 7 |
| Patient Profile | 1 | 1 | -- | 1 | 2 | 5 |
| Immunization | 2 | -- | -- | -- | 1 | 3 |
| Coverage | 1 | 1 | -- | 1 | 1 | 4 |
| Pod Structure | 2 | -- | -- | -- | 2 | 4 |
| **Total** | **16** | **7** | **5** | **8** | **17** | **53** |

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
4. For negative fixtures, include the `shaclConstraintViolated` field
5. Update the coverage matrix in this README

Fixture IDs must be unique and follow the pattern `^[a-z]+-[0-9]{3}$`.
