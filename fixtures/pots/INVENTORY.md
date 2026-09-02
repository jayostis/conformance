# POTS Conformance Fixtures (Inventory)

**Vocabulary covered:** `pots` v1.4 — the whole of it that can be reached. These are the
first fixtures this vocabulary has ever had.

## Why this directory exists

`pots` has been released since Phase 4 (2026-02-18), is listed in `VOCAB_VERSIONS`, and is
vendored and applied by `cascade-cli`, so `cascade validate` has been enforcing its shapes
against real pods. Until this batch **no fixture anywhere asserted a `pots:` class**, so not
one of its Violation constraints had ever executed. Whether they fired correctly, or fired at
all, was unknown. See jayostis/conformance#10.

The cause is that coverage followed the producers. `clinical` and `health` are where imported
data flows and they hold most of the corpus; `pots` is a Layer 3 patient-facing vocabulary that
no public tool in the project can write — `sdk-typescript` registers no `pots:` types in
`TYPE_MAPPING` — so nothing ever failed in a way that demanded a fixture.

## Fixture kind

Standalone SHACL-validation fixtures, not conversion oracles. Each file is validated directly
and carries its polarity in its name:

- `<slug>.VALID.ttl` MUST pass: no `sh:Violation`.
- `<slug>.INVALID.ttl` MUST be rejected: at least one `sh:Violation`.
- `<slug>.WARN.ttl` MUST be **noticed but not rejected**: at least one `sh:Warning` AND no
  `sh:Violation`.

**Not the root JSON format, deliberately.** The `fixtures/*.json` fixtures assert a *producer
contract* — `input` → `expectedOutput.turtle` — and no SDK implements a `pots:` mapping. A JSON
fixture here would invent a contract nobody implements and become a red test for an unrequested
feature. The `.ttl` format asks the question actually wanted: do these constraints fire?

## What is reachable, and what is not

`pots.shapes.ttl` declares seven `sh:NodeShape`s. **Five carry `sh:targetClass` and are
reachable; two do not, and the file contains no `sh:node` site to reach them by.** Measured by
parsing the graph and reading each `sh:property`'s effective severity — an absent `sh:severity`
means SHACL's default, `sh:Violation`:

| shape | Violation | Warning | Info | fixtures here |
|---|---|---|---|---|
| `pots:POTSCheckResultShape` | 5 | 3 | 11 | 1 valid, 2 invalid |
| `pots:HeartRateMeasurementShape` | 2 | — | 2 | 1 valid, 1 invalid |
| `pots:BloodPressureMeasurementShape` | 1 | — | 1 | 1 valid, 1 invalid |
| `pots:SymptomEventShape` | 1 | — | 2 | 1 valid, 1 invalid |
| `pots:PostureStabilityShape` | **0** | 1 | 2 | 1 valid, 1 **warn** |
| **reachable total** | **9** | **4** | **18** | 11 files |
| `pots:SystolicComponentShape` | 1 | — | — | **none possible** |
| `pots:DiastolicComponentShape` | 1 | — | — | **none possible** |

The two unreachable shapes hold the mmHg range checks (40–300 systolic, 20–200 diastolic) and
**can never fire**, so a blood-pressure component of any value validates clean. That is a `spec`
defect, reported as jayostis/spec#40, and it is why this batch is scoped to the five reachable
classes: scoping it that way means it did not have to wait on `spec` picking a route.

**Do not add fixtures for those two shapes until spec#40 lands.** There is no constraint to
violate, so a negative would fail with `NO_VIOLATION` and a positive would pass vacuously.

### Executed is not asserted, and the gap is 4 constraints

All 9 reachable Violation constraints in the table above are **executed** — each evaluates
against a focus node in this batch, which is why the `pots` row in `VOCAB_VERSIONS` stopped
saying NO FIXTURE COVERAGE. Only **5 are ever violated**, and that is the stronger property: a
constraint no fixture breaks would go on passing if `spec` deleted or deactivated it, and
nothing here would notice.

| Negatively asserted (5) | Fixture that breaks it |
|---|---|
| `pots:protocol` / `sh:in` | `potscheck-protocol-out-of-set.INVALID.ttl` |
| `pots:supineHeartRate` / `sh:class` | `potscheck-untyped-supine-heartrate.INVALID.ttl` |
| `( fhir:valueQuantity fhir:value )` / `sh:maxInclusive` | `heartrate-above-range.INVALID.ttl` |
| `fhir:component` / `sh:minCount` | `bloodpressure-no-component.INVALID.ttl` |
| `pots:symptom` / `sh:minLength` | `symptomevent-empty-symptom.INVALID.ttl` |

**Only ever satisfied (4):** `pots:date`, `pots:potsThresholdMet`, `cascade:schemaVersion` (the
`^[0-9]+\.[0-9]+$` pattern), and `fhir:valueQuantity` / `sh:minCount` on
`pots:HeartRateMeasurementShape`. Delete any one of those four in `spec` and all 11 fixtures
here still pass with no change in the suite. Four more negative fixtures would close that, and
unlike the two unreachable shapes above **nothing blocks them** — they are simply not written
yet. Do not read the "all 9" in `README.md` as more than execution.

The list is derived from the run, not from reading the shapes: every violation the suite reports
for `pots/*` is in the table's right-hand column and there are exactly five of them.

## Fixtures

### POTS check result (the top-level bundle)

| Fixture | Expect | Scenario |
|---|---|---|
| `potscheck-nasalean-full.VALID.ttl` | PASS | A complete NASA Lean check carrying **all five reachable classes in one graph**, because that is the shape the data takes: a check result REQUIRES a supine heart rate of class `pots:HeartRateMeasurement`, so it cannot be written standalone. All five Violation constraints and all three Warning constraints are satisfied. 72 bpm supine rising to 118 bpm standing is a +46 bpm delta, past the adult ≥30 bpm threshold, which is why `potsThresholdMet` is true — the numbers mean something rather than merely being in range. |
| `potscheck-protocol-out-of-set.INVALID.ttl` | FAIL | `pots:protocol "tiltTable"` against a value set of exactly one member, `"nasaLean"`. **Violation and not Warning is the point**, and the contrast is with `../clinical/coverage-record-legacy-type-vocabulary.WARN.ttl`: there the FHIR binding is extensible so a local code is flagged, here the value names *which measurement procedure produced the numbers*. A tilt-table result read against NASA Lean thresholds is a wrong answer, not a diminished one. |
| `potscheck-untyped-supine-heartrate.INVALID.ttl` | FAIL | The supine heart rate node is structurally perfect and carries **no `rdf:type`**, so `sh:class` rejects it. Worth more than its own constraint: `pots:HeartRateMeasurementShape` never fires on that node *at all*, because it reaches focus nodes by `sh:targetClass`. **The untyped node carries 350.0 bpm** — the same out-of-range value `heartrate-above-range.INVALID.ttl` carries — so the silence is *observable*: the typed sibling reports a `MaxInclusiveConstraintComponent` for that number and this file reports nothing but the `sh:class` failure. An in-range value could not state that, since a missing range violation would be equally explained by the number being legal. The two files are a controlled pair, differing only in `rdf:type`. That is the mechanism jayostis/spec#14 is blocked on, shown where it can be shown. |

### Heart rate

| Fixture | Expect | Scenario |
|---|---|---|
| `heartrate-standing.VALID.ttl` | PASS | A standing measurement on its own. Cascade validates a pod file by file and the shape targets the class, so a measurement written to a different file from its check arrives exactly like this — the same argument `../clinical/encounter-participant-standalone.VALID.ttl` makes. The value is reached by a **sequence path** `( fhir:valueQuantity fhir:value )`, not a property on the measurement. |
| `heartrate-above-range.INVALID.ttl` | FAIL | 350 bpm, outside the 20–300 bound. The runner prints this constraint's path as `_:blank`, because a SHACL sequence path is an RDF list; the `sh:message` is what identifies it. Noted in the fixture so the next reader does not go hunting for a property of that name. Its graph is byte-identical to `heartrate-standing.VALID.ttl` apart from the subject and the value — both timing properties included — so `diff` on the two shows exactly the two lines the header claims. |

### Blood pressure

| Fixture | Expect | Scenario |
|---|---|---|
| `bloodpressure-supine.VALID.ttl` | PASS | The FHIR component pattern: one observation, two components, each with its own code and quantity. Its header states plainly that **neither component's value is checked by anything** — see spec#40 above — because the natural reading of a passing BP fixture is that the numbers were validated, and they were not. |
| `bloodpressure-no-component.INVALID.ttl` | FAIL | No `fhir:component`, which is the whole of this shape's Violation surface. Written as the **realistic producer error**: it carries `fhir:valueQuantity` directly on the observation — the shape a *heart rate* takes — so the systolic reading has quietly become the observation's own value and the diastolic is gone. Nothing rejects the stray quantity; the missing component is what fails. |

### Symptom event

| Fixture | Expect | Scenario |
|---|---|---|
| `symptomevent-lightheadedness.VALID.ttl` | PASS | Lightheadedness on standing is the cardinal POTS symptom and the reason someone runs the check. Two of this shape's four constraints are `sh:Info` and so unobservable by this runner in either direction. |
| `symptomevent-empty-symptom.INVALID.ttl` | FAIL | `pots:symptom ""`. **The empty string rather than a missing property**, because `sh:minLength 1` is the half a shape author is most likely to omit and an empty value is far more likely from a producer than an absent field. Carries a warning for anyone writing a sibling: `sh:minLength` does not trim, so `" "` has length 1 and passes — jayostis/spec#26 and jayostis/spec#33 track that across the specification. |

### Posture stability

| Fixture | Expect | Scenario |
|---|---|---|
| `posturestability-stable.VALID.ttl` | PASS | A clean standing phase. Its header states what it does *not* prove: with no Violation constraint on this shape, a `.VALID.` fixture here would pass whether or not the shape existed. |
| `posturestability-isstable-repeated.WARN.ttl` | WARN | **The only fixture that can prove this shape fires.** `pots:isStable` is `sh:Warning`, the other two constraints are `sh:Info`, so `.INVALID.` is impossible (`NO_VIOLATION`) and `.VALID.` asserts nothing. Note the trap: `isStable` has `sh:maxCount 1` and **no `sh:minCount`**, so *omitting* it reports nothing and a fixture written that way would fail with `NO_WARNING`. This one repeats the property with contradicting values — what a read-modify-write cycle produces when the writer appends a correction instead of replacing (jayostis/sdk-typescript#38). |

## Conventions this batch establishes

**Collection properties are RDF lists.** `pots.ttl` declares `rdfs:range rdf:List` on
`pots:standingHeartRates` (`:118`), `pots:symptomEvents` (`:156`) and `pots:postureStability`
(`:224`). The SHACL shape does **not** enforce it — `standingHeartRates` carries only
`sh:minCount 1` at `sh:Warning`, and repeated plain properties would satisfy it equally. The
list form is used because it is the documented intent and nothing contradicts it. No producer
exists for this vocabulary, so these fixtures are the first artefact to state a convention, and
they state the one the ontology already declares rather than inventing a second.

List members stay individually typed, so each is still reached by its own `sh:targetClass`.
Wrapping them in a list hides nothing from validation.

**If the private Swift producer turns out to emit repeated properties instead, change these
fixtures and say so** — do not add a rival convention beside them.

**Subject IRIs are well-formed UUIDs, and that is load-bearing rather than cosmetic.** Every
subject here is `urn:uuid:` followed by a real 8-4-4-4-12 hex UUID with the version-4 nibble and
the RFC 4122 variant nibble in their proper places, so a consumer that parses the URN gets a
UUID rather than an exception. `cascade-cli` does exactly that: a node whose URN does not match
`UUID_RE` (`src/lib/literal-lifting.ts`) is silently absent from its reference-lifting index, and
`UUID_V4_REGEX` (`src/lib/fhir-converter/types.ts`) is stricter still. Both accept every
identifier in this directory.

The values are systematic so a failure can be traced back to a file, and the structure uses hex
digits only:

```
urn:uuid:b075NNNN-0000-4a00-8000-RRRRRRRRRTTS
         ^^^^     ^^^^      ^                ^
         |        |         |                serial within role
         |        |         version 4 / variant 8, as any v4 UUID
         |        fixture serial, 0001..0011, matching the order below
         fixed hex tag shared by every subject in this directory
```

`TT` is the role: `00` check result, `10` heart rate, `20` blood pressure, `30` symptom event,
`40` posture stability. **Do not go back to mnemonic-but-invalid identifiers.** An earlier draft
of this batch used `urn:uuid:p0t5-0001-4a00-8000-00000000hr01`, which reads better and is not a
UUID — wrong grouping and non-hex characters in every group that carries a tag. Roughly 89
identifiers elsewhere in `fixtures/` and most of `reference-patient-pod/` still have that defect;
they are not this batch's to fix, but new fixtures should not join them.

## Verification

```bash
python3 scripts/run_conformance.py --spec-dir ../spec --select 'pots/*'
#   Expect: 11 passed / 0 failed / 11 total, 349 constraint checks.
#   Each INVALID reports exactly one violation and each WARN exactly one warning,
#   naming the constraint its header claims.
```

Against a `spec` revision that predates the shapes, every fixture here reports `UNSHAPED` with
zero constraint checks, because `pots.shapes.ttl` would not exist.
