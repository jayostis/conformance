# conformance — Agent Context

## Repository Purpose

Conformance test fixtures and reference Patient Pod for the Cascade Protocol.
Downstream SDKs (sdk-typescript, sdk-python) and tools (cascade-cli) must pass all fixtures here before releasing.

## Key Architecture

- `fixtures/` — JSON fixture files, one per record instance. Named `{type}-{id}.json`. Also 40 `.ttl` fixtures in subdirectories, with polarity in the filename (`*.INVALID.ttl`).
- `schema/fixture-schema.json` — JSON Schema for the fixture format (includes `dataType` enum).
- `scripts/run_conformance.py` — executes every fixture against the SHACL shapes from a pinned `spec` checkout. `scripts/SPEC_PIN` names the commit.
- `scripts/selftest_runner.py` — mutation tests proving the runner can fail.
- `reference-patient-pod/` — Example Turtle files showing real schema usage.

## MANDATORY: run the suite before claiming a fixture works

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/run_conformance.py --spec-dir ../spec
```

Against the revision in `scripts/SPEC_PIN` (`spec` at core 3.4 / health 2.5 /
clinical 1.13), which is what CI executes: **86 passed / 32 failed / 0 skipped /
118 total**, 61,391 constraint checks.

The result depends on which `spec` revision you point it at, so **always say which**,
and never quote a number obtained with `--allow-spec-drift` as the suite's result.
The same 118 fixtures score 52/66 against the pre-2026-08-03 vocabulary, because 14
of them evaluate zero constraints where the shapes that target them do not exist and
the runner counts a zero-constraint pass as a failure. Moving the pin is what moves
that number, so re-pin deliberately and record both counts in the PR.

**Never resolve a failure by weakening the runner.** Do not skip a fixture, relax an assertion, or add a baseline of known failures. A new fixture that the runner reports as `UNSHAPED` is not testing anything: no shape targets it, so zero constraints ran and its PASS would be vacuous.

## MANDATORY: Deployment Discipline

### Conformance is the gate between spec and SDKs

When `spec` tags a new vocabulary version, conformance fixtures must be added **before** SDK releases can happen. The release sequence is:

```
spec tag → conformance fixtures added → SDK releases
```

### When adding fixtures for a new vocabulary class, you MUST:

- [ ] Add at least one **valid** fixture: `fixtures/{type}-{id}-valid.json`
- [ ] Add at least one **invalid** fixture (e.g., missing required field): `fixtures/{type}-{id}-invalid.json`
- [ ] Update `schema/fixture-schema.json` — add new `dataType` enum value(s)
- [ ] Add fixtures for any new properties on existing classes (not just new classes)
- [ ] Update `VOCAB_VERSIONS` to reflect the vocabulary versions now covered
- [ ] Tag the release: `conformance-v{YYYY-MM-DD}`

### Current vocabulary coverage

Check `VOCAB_VERSIONS` at the repo root. Compare against `spec/VOCAB_VERSIONS` to see what's missing.

### Vocabulary coverage (as of 2026-08-03)

Covered up to core=3.4, health=2.5, clinical=1.13, coverage=1.3. Read the comments in
`VOCAB_VERSIONS`: each row now names what a fixture actually exercises and what it does
not, measured by recording which node shapes matched a focus node across the whole suite.
- core v3.4: `cascade:ExportManifest` and `cascade:RecordSummary` shaped (`pod-002` valid, `pod-004` negative).
- health v2.5: five record classes and three daily-snapshot classes shaped. 26 existing fixtures that had evaluated zero constraints became live; `dailyvital-*`, `dailyactivity-*`, `dailysleep-*` added.
- clinical v1.13: four duplicated record classes deprecated. Deprecation is not a SHACL constraint, so no fixture asserts it; the clinical fixtures are executed against the v1.13 shapes.

### Known gaps

Each of these is a class that fixtures assert and no shape targets, so the fixture
evaluates zero constraints and the runner reports it `UNSHAPED`. A **negative** fixture
for any of them is impossible until a shape exists: there is no constraint to violate.

- `health:ProcedureRecord` — asserted by `proc-001/002/003`, not defined in `health.ttl`
- `clinical:Encounter`, `clinical:MedicationAdministration`, `clinical:ImplantedDevice`, `clinical:ImagingStudy` — defined in `clinical.ttl`, no shape
- `coverage:ClaimRecord`, `coverage:BenefitStatement`, `coverage:DenialNotice`, `coverage:AppealRecord` — defined in `coverage.ttl`, no shape
- `clinical:CoverageRecord` — asserted by `coverage-001`; `coverage:InsurancePlan` is the shaped spelling
- `ldp:BasicContainer` — asserted by `pod-001`/`pod-003`, external vocabulary, no Cascade shape
- `cascade:InteractionScenario` — shaped, but no fixture instantiates it
- `checkup:` and `pots:` — `VOCAB_VERSIONS` carries a version row for each and no fixture instantiates any class either vocabulary shapes
- `health:SocialHistoryRecordShape` declares only `sh:Info` constraints, so the `health:` spelling of social history cannot have a negative fixture; `social-003` covers the `clinical:` spelling
- (Resolved 2026-06-22) `proc-001/002/003` previously used `dataType: "ProcedureRecord"` (not in the fixture-schema enum) and failed `schema/fixture-schema.json` validation; corrected to `dataType: "Procedure"` (input `type` stays `ProcedureRecord`, matching the cond/lab convention). All fixtures now validate against the schema.

## Fixture Format

Each fixture is a JSON object with the structure defined in `schema/fixture-schema.json`.
`dataType` must match a class name defined in the relevant vocabulary TTL.

## Commit Conventions

```
feat(fixtures): add {ClassName} fixtures (clinical v1.7)
fix(fixtures): {description}
```
