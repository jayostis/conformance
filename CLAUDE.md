# conformance — Agent Context

## Repository Purpose

Conformance test fixtures and reference Patient Pod for the Cascade Protocol.
Downstream SDKs (sdk-typescript, sdk-python) and tools (cascade-cli) must pass all fixtures here before releasing.

## Key Architecture

- `fixtures/` — JSON fixture files, one per record instance. Named `{type}-{id}.json`. Also 71 `.ttl` fixtures in subdirectories, with polarity in the filename. **Three** polarities: `*.VALID.ttl` (or no suffix) must produce no `sh:Violation`; `*.INVALID.ttl` must produce at least one; `*.WARN.ttl` must produce at least one `sh:Warning` **and** no `sh:Violation`. The third exists because Cascade shapes report a value existing data already carries at `sh:Warning` rather than rejecting it (the `core` v3.5 ratchet, applied by `clinical` v1.16 to five `clinical:status` bindings), and neither of the other two polarities can state that claim: `.INVALID.ttl` fails such a fixture with `NO_WARNING`'s sibling `NO_VIOLATION`, and `.VALID.ttl` passes it while asserting nothing about the warning.
- `schema/fixture-schema.json` — JSON Schema for the fixture format (includes `dataType` enum).
- `scripts/run_conformance.py` — executes every fixture against the SHACL shapes from a pinned `spec` checkout. `scripts/SPEC_PIN` names the commit.
- `scripts/selftest_runner.py` — mutation tests proving the runner can fail.
- `reference-patient-pod/` — **Canonical** home of the reference pod: 22 files of synthetic Turtle showing real schema usage. `cascade-cli` reads it from here, and `cascadeprotocol.org` publishes a generated copy of it at `/reference-patient-pod/` that its `scripts/sync-reference-pod.sh --check` holds byte-identical to this directory. Edit the pod here and nowhere else.

## MANDATORY: run the suite before claiming a fixture works

```bash
python3 -m pip install -r scripts/requirements.txt

# 1. the truth: executes and reports every fixture. Exits 1 while any fails.
python3 scripts/run_conformance.py --spec-dir ../spec --json results.json

# 2. the gate: did anything get worse, or better without the record being updated?
python3 scripts/check_baseline.py --results results.json
```

Against the revision in `scripts/SPEC_PIN` (`spec` at core 3.10 / health 2.8 /
clinical 1.19 / coverage 1.7), which is what CI executes: **140 passed / 26
failed / 0 skipped / 166 total**, 63,468 constraint checks, and all 26 are
enumerated in `KNOWN_FAILURES.json`, so the ratchet holds and the job is green.

These counts move with the pin, so re-measure them in the same commit that
re-pins. They had gone two pins stale before 2026-09-01, which is the failure
mode to avoid: a mandatory-verification section quoting numbers no run can
reproduce teaches the reader to disbelieve the section.

The result depends on which `spec` revision you point it at, so **always say which**,
and never quote a number obtained with `--allow-spec-drift` as the suite's result.
The same 118 fixtures score 52/66 against the pre-2026-08-03 vocabulary, because 14
of them evaluate zero constraints where the shapes that target them do not exist and
the runner counts a zero-constraint pass as a failure. Moving the pin is what moves
that number, so re-pin deliberately, re-measure `KNOWN_FAILURES.json` in the same
commit, and record both counts in the PR. The gate refuses to run at all if the
baseline's `specPin` and the run's disagree.

**Never resolve a failure by weakening the runner.** Do not skip a fixture, do not
relax an assertion, do not delete or soften a shape to make a fixture pass. A new
fixture that the runner reports as `UNSHAPED` is not testing anything: no shape
targets it, so zero constraints ran and its PASS would be vacuous.

**The ratcheting baseline is permitted, and is the mechanism of record.** This
supersedes an earlier blanket ban on "a baseline of known failures" in this file,
which was written before the composition of the failures was known. Most of them
are not fixable here at any effort: they need shapes authored in `spec`. "Red
until fixed" therefore meant red on every pull request for an unbounded period,
and a permanently red job and a suppressed failure end in the same place, with
nobody reading either.

What makes `KNOWN_FAILURES.json` legitimate rather than a suppression list, and
what you must preserve if you touch it:

- **It hides nothing.** `run_conformance.py` still executes every fixture and
  still prints every failure. Only the *gate* — `scripts/check_baseline.py` —
  distinguishes known from new.
- **It fails in BOTH directions.** A failure that is not listed fails CI. **A
  listed failure that starts passing also fails CI**, telling the author to
  remove the entry. The second half is the entire justification: without it the
  list grows and never shrinks. Do not remove it.
- **Entries are keyed on (fixture, reason).** A fixture that goes `UNSHAPED` →
  `VIOLATIONS` is a new fact about the world and must fail even though it was
  already failing. Keying on the fixture alone is how a ratchet starts lying.
- **It never grows on its own.** Adding an entry is an explicit committed edit
  carrying the repo that owns the fix. `--regenerate` exists, marks anything new
  `UNASSIGNED`, and the gate refuses to pass while any entry is `UNASSIGNED`.
  Using it needs saying so in the pull request.
- **A degenerate, drifted or pin-mismatched run cannot be ratcheted.** The gate
  exits 2 rather than green if the baseline is missing or unparseable, if the run
  evaluated zero constraints, if it was produced with `--allow-spec-drift`, or if
  the baseline was measured against a different `spec` revision than the run used.

Both directions and all of those refusals are mutation-tested in
`scripts/selftest_runner.py` and run in CI. If you change the gate, change those
tests to match and show them failing first.

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

### Vocabulary coverage (as of 2026-09-01)

Covered up to core=3.10, health=2.8, clinical=1.19, coverage=1.7. Read the comments in
`VOCAB_VERSIONS`: each row now names what a fixture actually exercises and what it does
not, measured by recording which node shapes matched a focus node across the whole suite.
- core v3.10: `cascade:consentScope` and `cascade:ConsentScopeShape`, the first
  constraint here that mentions consent. `clinical/social-history-consent-scope.VALID.ttl`
  and `-wrong-value.INVALID.ttl`. Absence of the property is NOT constrained by
  v3.10 and must not be given a fixture; `clinical/social-history-smoking.ttl`
  carries no scope, is deliberately unedited, and its continued pass is what
  asserts that. See the core=3.10 row in `VOCAB_VERSIONS`.
- clinical v1.18/v1.19: **reached as of 2026-09-01** (#6, PR #11). Three fixtures
  restore the deprecated-and-retained `clinical:CoverageRecord` spelling, which no
  fixture had asserted since `coverage-001` was retyped by PR #4:
  `legacycoverage-001` (happy path, recovered from the pre-migration form at
  `0a7d5dc^`), `legacycoverage-002` (negative, `clinical:providerName` absent) and
  `clinical/coverage-record-legacy-type-vocabulary.WARN.ttl` (v1.19's
  `clinical:CoverageTypeVocabularyShape` firing at `sh:Warning` on an
  out-of-vocabulary value). 38 constraint checks each, +114 total. This is the
  obligation `spec`'s `CONTRIBUTING.md` "Deprecating a spelling" imposes: a
  retained spelling keeps a fixture demonstrating it still reads.
- coverage v1.6: **still no fixture.** `cascade:AIExtracted` on
  `InsurancePlanShape` is unexercised. coverage v1.7 IS exercised: six coverage
  fixtures go 47 → 49 constraint checks.
- The historical entries below describe earlier batches and their pins.
- core v3.7 / health v2.8 / clinical v1.16 / coverage v1.5: 25 fixtures across
  `fixtures/clinical/`, `fixtures/health/`, `fixtures/coverage/` and `fixtures/core/`.
  The pre-existing 136 score identically at the old and new pins, which measures the
  release's "additive and strictly widening" claim rather than quoting it. One of the
  25 is baselined: it found a real defect in the release, where `sh:node` inheritance
  escalates a nested `sh:Warning` into an outer `sh:Violation` on all six document
  subtypes. See `README.md`, "A defect the v1.16 batch found".
- core v3.4: `cascade:ExportManifest` and `cascade:RecordSummary` shaped (`pod-002` valid, `pod-004` negative).
- health v2.5: five record classes and three daily-snapshot classes shaped. 26 existing fixtures that had evaluated zero constraints became live; `dailyvital-*`, `dailyactivity-*`, `dailysleep-*` added.
- clinical v1.13: four duplicated record classes deprecated. Deprecation is not a SHACL constraint, so no fixture asserts it; the clinical fixtures are executed against the v1.13 shapes.

### Known gaps

Each of these is a class that fixtures assert and no shape targets, so the fixture
evaluates zero constraints and the runner reports it `UNSHAPED`. A **negative** fixture
for any of them is impossible until a shape exists: there is no constraint to violate.

- `health:ProcedureRecord` — asserted by `proc-001/002/003`, not defined in `health.ttl`
- `clinical:MedicationAdministration`, `clinical:ImplantedDevice`, `clinical:ImagingStudy` — defined in `clinical.ttl`, no shape. (`clinical:Encounter` left this list at clinical v1.14, and `clinical:EncounterParticipant` was shaped from birth in v1.16.)
- `coverage:ClaimRecord`, `coverage:BenefitStatement`, `coverage:DenialNotice`, `coverage:AppealRecord` — defined in `coverage.ttl`, no shape
- (Resolved 2026-09-01, both directions) `clinical:CoverageRecord` was listed here as "asserted by `coverage-001`, no shape". PR #4 retyped `coverage-001` to `coverage:InsurancePlan` and clinical v1.18 added `clinical:CoverageRecordShape`, which inverted the gap rather than closing it — a **shape with no fixture behind it**. #6 / PR #11 closed that half too: three fixtures now assert the class, so the shape is executed rather than merely present. Note the pairing is deliberate and must survive: `coverage-001` demonstrates the spelling new data uses, `legacycoverage-001` demonstrates the retained spelling still reads. Retiring the legacy fixture is how the deprecation becomes an accident rather than a decision.
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
