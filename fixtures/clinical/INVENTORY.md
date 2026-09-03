# Clinical Conformance Fixtures (Inventory)

**Vocabulary covered:** `clinical` v1.4 (`social-history-smoking.ttl`, the
`clinical:` spelling of social history), `clinical` v1.16 (the encounter,
document and status batch below), `clinical` v1.19 (the coverage-type
vocabulary warning on the deprecated `clinical:CoverageRecord` spelling) and
`core` v3.10/v3.11 (the consent-scope pair —
records typed `clinical:SocialHistoryRecord`, constrained by a `core` shape,
so they live here beside the other social history fixtures rather than in
`../core/`).

## Fixture kind

Standalone SHACL-validation fixtures, not conversion oracles. Each file is
validated directly and carries its polarity in its name:

- `<slug>.VALID.ttl` MUST pass: no `sh:Violation`.
- `<slug>.INVALID.ttl` MUST be rejected: at least one `sh:Violation`.
- `<slug>.WARN.ttl` MUST be **noticed but not rejected**: at least one
  `sh:Warning` AND no `sh:Violation`.

The third polarity is new in this batch and it exists because clinical v1.16
needed it. Five of the release's rulings are `sh:Warning` bindings, per the
ratchet core v3.5 wrote down: a value that existing data already carries is
*reported*, never rejected, and the severity is raised only after a release in
which the warning is observably absent from conforming output. A two-polarity
runner cannot state that claim. `.INVALID.ttl` fails such a fixture with
`NO_VIOLATION`, and `.VALID.ttl` passes it while asserting nothing about the
warning, which is the same silence clinical v1.16 exists to end. See the note at
the top of `scripts/run_conformance.py`.

Every byte is synthetic: invented hospital, clinicians, visit numbers, document
identifiers and dates. The OIDs are under the HL7 example arc.

## Fixtures

### Encounter and participation (clinical v1.16)

| Fixture | Expect | Scenario |
|---|---|---|
| `encounter-inpatient-full.VALID.ttl` | PASS | Every encounter fact the release added, on one inpatient admission: all three `Encounter.class` Coding members, two `encounterReason` values, both `hospitalization` fields, two participations in **different** roles, and two business identifiers in `{system}\|{value}` token form alongside one `sourceRecordId`. Inpatient rather than ambulatory on purpose: `admitSource` and `dischargeDisposition` are the signal that separates an admission from an office visit, and neither is meaningful on a clinic visit. |
| `encounter-participant-standalone.VALID.ttl` | PASS | A `clinical:EncounterParticipant` with nothing pointing at it. Cascade validates a pod **file by file**, so a participation written to a different file from its encounter arrives exactly like this, and `clinical:EncounterParticipantShape` targets the class rather than a path from an encounter. Also carries a second, **local** role code, which an extensibly-bound source may conformantly send. |
| `encounter-participant-two-names.INVALID.ttl` | FAIL | Two individuals on one participation. `Encounter.participant.individual` is 0..1, and this is the corruption the shape's cardinality constraints exist to stop: a reader given two names under one role cannot tell whose the specialty is. Everything else is correct, so only `sh:maxCount` catches it. |
| `encounter-two-admit-sources.INVALID.ttl` | FAIL | Two admission sources on one admission. Violates a cardinality the **release itself chose** on a property that did not exist under v1.15, so the fixture is evidence about this release rather than about older vocabulary. |

### Document status and attribution (clinical v1.16)

| Fixture | Expect | Scenario |
|---|---|---|
| `document-two-statuses-two-authors.VALID.ttl` | PASS | All four axes on one document, each saying something different: `clinical:status` "final" (the content), `clinical:documentReferenceStatus` "current" (the pod's pointer), two `documentAuthorName` values (who wrote it), one `authenticatorName` (who signed it, a third person), and `providerName` at its single permitted value so the repeatable author list is shown coexisting with the `sh:maxCount 1` that was discarding authors. |

### The `clinical:status` bindings (clinical v1.16)

Three of the five binding sets live here; the other two are on `health:` shapes
and are in [`../health/INVENTORY.md`](../health/INVENTORY.md). Each is a PASS
case and a warning case that differ in exactly one respect: membership of the
bound value set.

| Fixture | Expect | Scenario |
|---|---|---|
| `status-vitalsign-final.VALID.ttl` | PASS | `Observation.status`, 8 codes. |
| `status-vitalsign-completed.WARN.ttl` | WARN | "completed" — a real FHIR code on *workflow* resources and in no `Observation.status` value set. What a converter writes when it maps a general "this is done" state onto an observation. |
| `status-clinicaldocument-appended.VALID.ttl` | PASS | **"appended" is the point.** It is one of the six codes in `diagnostic-report-status` and **not** in `composition-status`, so this fixture passes only under the wider set the release deliberately bound to `clinical:ClinicalDocumentShape`. A fixture using "final" would pass under either binding and prove nothing about which was chosen. |
| `status-clinicaldocument-in-progress.WARN.ttl` | WARN | "in-progress" is out of set under the wider binding *and* the narrower one, so this fixture keeps meaning what it means if the ratchet later narrows the DocumentReference-derived subtypes to `composition-status`. |
| `status-laboratoryreport-corrected.VALID.ttl` | PASS | "corrected" is what distinguishes a result that **replaced** an earlier wrong one from the wrong one itself. Also absent from `composition-status`, so it too passes only under the wider set. |
| `status-laboratoryreport-in-progress.WARN.ttl` | WARN **(currently FAILS — see below)** | The same value as the ClinicalDocument twin, on the class that reaches `ClinicalDocumentShape` through `sh:node`. |

### Consent scope (core v3.10)

`cascade:consentScope` is the first constraint in this specification that
mentions consent. Before this pair, `cascade:ConsentScopeShape` shipped with
**zero** constraint executions behind it — a released shape that no fixture
reaches, which is the condition issues #5 (`checkup:`), #10 (`pots:`) and #6
(`clinical:CoverageRecord`) were filed for, and the one this repository exists
to catch. #6 is closed: `coverage-record-legacy-type-vocabulary.WARN.ttl` below
is part of that fix.

| Fixture | Expect | Scenario |
|---|---|---|
| `social-history-consent-scope.VALID.ttl` | PASS | `cascade:consentScope cascade:SocialHistoryConsent` on a social history record — the class `clinical.ttl` says "requires separate consent scope", so the record type a producer will write the property on first. It and its INVALID sibling differ in exactly one respect besides their subject IRIs — the value of `cascade:consentScope` — so `sh:in` is the only thing that can separate their verdicts. (It is *not* byte-identical to `social-history-smoking.ttl`: it carries a different `health:smokingStatus` and no `clinical:packsPerYear`. Neither is constrained on this class, which the counts show — strip the consent scope and it evaluates that fixture's same 12 checks.) |
| `social-history-consent-scope-wrong-value.WARN.ttl` | WARN | `cascade:consentScope cascade:SelfReported`. **The value being a real term is the point.** `cascade:SelfReported` is a `cascade:DataProvenance` subclass declared in `core.ttl` since v1, so an invented IRI would have been caught by any constraint that merely checked the value resolved; an IRI that exists in the same namespace and is simply not in the closed `cascade:ConsentScope` list is caught only by the constraint this release added. It is also the confusion a producer will actually make, provenance being the other `cascade:` code list a record of this shape carries. **This file was `.INVALID.ttl` until core v3.11**, which opened the value set on D-CONSENT-1 — `sh:in` at `sh:Warning`, never `sh:Violation`, because a closed list missing a member rejects conformant data. The data did not change; what the specification does with it did, and the polarity suffix is the only place a fixture can say so. It now fires exactly one warning and no violation: `cascade:ConsentScopeShape / cascade:consentScope / sh:InConstraintComponent`. |

**What is deliberately NOT here, and must not be added.** There is no fixture
asserting that a *missing* consent scope is rejected. core v3.10 requires the
property nowhere, on no record class, at no severity: `cascade:ConsentScopeShape`
is `sh:targetSubjectsOf`, so it constrains the value wherever the predicate
appears and reports nothing on a record that omits it. That is the ratchet
`core` v3.5 wrote down. Requiring presence is step 2 — `sh:minCount 1` at
`sh:Warning` on `clinical:SocialHistoryRecordShape`, once a reference producer
emits a scope — and step 3 raises it to `sh:Violation`; each is its own
vocabulary version and neither is this one.

**`social-history-smoking.ttl` is what asserts that half, and it does so by
being left alone.** It carries no consent scope and still passes, at 12
constraint checks, unchanged across the pin move. Adding a consent scope to it
would destroy the only evidence in this repository that absence is still
unchecked — which is what separates spec#5 as merged from the draft that put
`sh:minCount 1` at `sh:Violation` on `clinical:SocialHistoryRecordShape` and
would have rejected every social history record written before v3.10.

### Coverage type vocabulary, deprecated spelling (clinical v1.19)

`clinical:CoverageRecord` is deprecated since clinical v1.5 and **retained**, not
removed, because real pre-migration Pods still hold coverage in that spelling.
clinical v1.18 shaped the class and v1.19 added the advisory value check below.
No fixture asserted the class at the time, because #1 / PR #4 had just retyped
`coverage-001` onto the current `coverage:InsurancePlan` spelling — correct for
data going forward, and it removed the corpus's last legacy instance at about the
moment `spec` shaped it. The two JSON halves of the fix live at
`../legacycoverage-001.json` (happy path) and `../legacycoverage-002.json`
(negative); the warning half is here, because only a `.WARN.ttl` can state it.

| Fixture | Expect | Scenario |
|---|---|---|
| `coverage-record-legacy-type-vocabulary.WARN.ttl` | WARN | `clinical:coverageType "commercial"` — a payer-local code in neither the retained Cascade values (`primary`, `secondary`, `dental`, `vision`) nor the v3-ActCode list, and the word payer systems, EOBs and member portals actually use for employer-sponsored coverage. **`.WARN.` and not `.INVALID.` is the point:** FHIR binds `Coverage.type` EXTENSIBLY, so an alternate code is conformant at source and the specification deliberately does not reject it — an `.INVALID.` fixture would fail with `NO_VIOLATION`. **And not `.VALID.` either:** that asserts only the absence of a violation, which this record also satisfies, so it would pass whether or not `clinical:CoverageTypeVocabularyShape` existed. Everything else on the record is clean, because a warn fixture that also violates something is rejected outright and is not evidence about the warning. Exactly one warning fires: `clinical:CoverageTypeVocabularyShape / clinical:coverageType / sh:InConstraintComponent`. |

## A defect this batch found, and did not paper over

`status-laboratoryreport-in-progress.WARN.ttl` is listed in
[`KNOWN_FAILURES.json`](../../KNOWN_FAILURES.json), owned by `spec`.

clinical v1.16 states that all five `clinical:status` bindings are `sh:Warning`,
so an out-of-set status is reported and never rejected. That holds on
`clinical:ClinicalDocumentShape` and **fails on every class that reaches it
through `sh:node`**. SHACL defines conformance as an *empty* result set, so a
nested `sh:Warning` makes the value node non-conforming, and the outer `sh:node`
constraint then reports a `sh:Violation` at its own default severity. The lab
report is therefore rejected for a value the release says should only be warned
about.

The blast radius is all six document subtypes — `LaboratoryReport`,
`ProgressNote`, `DischargeSummary`, `ConsultationNote`, `ImagingReport`,
`VisitSummary` — and it applies to `clinical:documentReferenceStatus` as well as
to `clinical:status`. On `ProgressNote` the underlying warning is not even
reported, only an opaque `NodeConstraintComponent`, so a reader cannot tell which
field was wrong.

Measured on two independent engines, which is what rules out an implementation
quirk: pyshacl 0.30.1 (this runner) and cascade-cli 0.17.0 (rdf-validate-shacl)
agree on the verdict, and both agree the `ClinicalDocument` twin is only warned.

The fixture asserts what clinical v1.16 says rather than what the shapes
currently do, and the baseline entry is what keeps that honest: the ratchet fails
in both directions, so when `spec` fixes the severity the entry must be removed
in the same commit.

## Verification

Measured in both directions. Only the RED-first half makes a negative or a
warning fixture mean anything.

```sh
# RED first: against the previous pin (spec d37901e, clinical v1.15), where none
# of these constraints exists.
python3 scripts/run_conformance.py --spec-dir <spec@d37901e> --allow-spec-drift \
  --select 'clinical/encounter*' --select 'clinical/document*' --select 'clinical/status*'
#   Both INVALID fixtures report NO_VIOLATION; all three WARN fixtures report
#   NO_WARNING; both participant fixtures report UNSHAPED with 0 constraint checks,
#   because clinical:EncounterParticipant does not exist there.

# GREEN: against the pin now named in scripts/SPEC_PIN (clinical v1.16).
python3 scripts/run_conformance.py --spec-dir <spec@pin> --select 'clinical/*'
#   11 passed / 1 failed / 12 total (the 12th is the legacy social-history fixture);
#   status-laboratoryreport-in-progress.WARN.ttl is the failure, as recorded above.
```

The positive fixtures are not proven by passing — they pass under both pins,
because the release is strictly widening. What proves them is the **constraint
check count**, which rises at the new pin for every one of them: the encounter
goes 33 → 57, the document 38 → 48, the ClinicalDocument status case 34 → 44 and
the lab report 71 → 94. A positive fixture whose count did not move would be
green without touching the new vocabulary at all.

Cross-checked with the real CLI validator, pointed at shapes taken from the spec
checkout rather than its own embedded copy (which is one release behind until
the step-4 sync lands):

```sh
cascade validate fixtures/clinical/<fixture> --shapes <flat dir of spec *.shapes.ttl>
```

All eleven verdicts agree with this runner's, including the lab report failure.

### The consent-scope pair (core v3.10)

Same discipline, and the RED half is the whole argument for the polarity suffix.

```sh
# RED first: at the PREVIOUS pin (spec 9b13ae4, core v3.8), where no shape
# anywhere mentions consent.
python3 scripts/run_conformance.py --spec-dir <spec@9b13ae4> \
  --select 'clinical/social-history*'
#   2 passed / 1 failed / 3 total.
#   social-history-consent-scope-wrong-value reports a failure: the two files
#   are INDISTINGUISHABLE there, both evaluating the same 12 constraint checks
#   as social-history-smoking.ttl, because the consent scope on each is read by
#   nothing. That is what a polarity suffix turns into a reported failure
#   instead of a silent pass.
#
#   NOTE the file is .WARN.ttl as of core v3.11 and was .INVALID.ttl before it,
#   so the reason differs by pin: NO_VIOLATION for the old name, NO_WARNING for
#   the current one. Either way the point stands -- a .VALID.ttl would have
#   passed at core v3.8 and told nobody anything.

# GREEN: at the pin now named in scripts/SPEC_PIN (spec 40e581f, core v3.10).
python3 scripts/run_conformance.py --spec-dir <spec@40e581f> \
  --select 'clinical/social-history*'
#   3 passed / 0 failed / 3 total.
```

The positive fixture is not proven by passing either — it passes under both
pins. What proves it is the count: **12 → 16** constraint checks, the four being
`cascade:ConsentScopeShape`'s `sh:nodeKind`, `sh:in`, `sh:minCount` and
`sh:maxCount`. `social-history-smoking.ttl` stays at **12 → 12**, and that
non-movement is the open-world assertion: the shape did not reach it, because it
carries no consent scope.

The negative fixture's single violation is
`cascade:ConsentScopeShape / path cascade:consentScope / InConstraintComponent`,
verbatim from `results.json` — one violation, from the constraint under test,
and nothing else fires.

Measured across the **whole** suite at both pins, because two of the five
version steps this pin moves (clinical v1.18, coverage v1.7) are explicitly not
widening: 163 fixtures, exactly one verdict change, and it is
`social-history-consent-scope-wrong-value.INVALID.ttl` going `NO_VIOLATION` →
`pass`. (That file is now `.WARN.ttl`; core v3.11 opened the value set, so the
rejection it asserted became a warning and the polarity had to follow. The
2026-09-02 re-pin to spec 3362861 records that move.) No existing fixture changed verdict, gained a warning or lost one. See
`scripts/SPEC_PIN` for the counts and for where the +20 constraint checks went.
