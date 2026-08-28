# Coverage Conformance Fixtures (Inventory)

**Vocabulary covered:** `coverage` v1.5 — `coverage:status`.

These are the Turtle fixtures for the coverage vocabulary. The four older
`coverage-00*.json` fixtures at the root of `fixtures/` cover
`coverage:InsurancePlanShape`'s pre-v1.5 constraints and are unaffected by this
batch; they omit `coverage:status` and continue to pass, which is what exercises
the release's compatibility claim.

## Fixture kind

Standalone SHACL-validation fixtures. `.VALID.ttl` must pass; `.INVALID.ttl`
must be rejected with at least one `sh:Violation`.

Note that there is **no `.WARN.ttl` here**, and that is the interesting part; see
below.

Every byte is synthetic: invented payer, plan, member and group numbers.

## Fixtures

| Fixture | Expect | Scenario |
|---|---|---|
| `coverage-status-active.VALID.ttl` | PASS | `Coverage.status`, required binding to `fm-status`: active \| cancelled \| draft \| entered-in-error. |
| `coverage-status-terminated.INVALID.ttl` | FAIL | "terminated" — the word payer systems and member portals use for a plan that has ended, which a converter passing the payer's own vocabulary through will write. The `fm-status` spelling is "cancelled". Rejected by `coverage:InsurancePlanShape` / `coverage:status` / `sh:in`. |

## Why this one is a Violation when the five `clinical:status` fixtures are Warnings

This is the same question in two directions, and the release answers it with one
rule: **the severity follows the binding strength of the element the data is
converted from.** That rule was established in this same shape by coverage v1.4.

- FHIR binds `Coverage.status` with **required** strength, so a value from
  outside the value set is not conformant at source and there is no conformant
  producer to protect. Violation.
- FHIR binds `Coverage.type` **extensibly**, where a payer may conformantly send
  an alternate code, which is why `coverage:coverageType`'s value is checked only
  at `sh:Warning` two constraints above in the very same shape. The two
  severities in one shape are not an inconsistency; they are the rule being
  applied.

The other half of the argument is that nothing is lost by rejecting it. The core
v3.5 ratchet exists to avoid turning **existing** data red, and no pod has ever
carried `coverage:status`, because it did not exist before v1.5.

FHIR marks `Coverage.status` a modifier element, which is what makes the check
worth having at all: a cancelled plan read as an active one is a *wrong* answer
to "am I covered", not a missing one.

## What is deliberately not tested here

`coverage:status`'s **presence** is not required, although the source element is
1..1, because no producer has yet had the chance to write it. There is therefore
no negative fixture for a plan record that omits the property. The four existing
`coverage-00*.json` fixtures all omit it and all still pass, which exercises that
compatibility claim four times rather than asserting it once.

The shape's own note names the ratchet steps: add `sh:minCount 1` at `sh:Warning`
once producers emit it, and raise to `sh:Violation` only after a release in which
that warning is observably absent from conforming output.

## Verification

```sh
# RED first: against the previous pin (spec d37901e, coverage v1.4), where
# coverage:status is not declared on any shape.
python3 scripts/run_conformance.py --spec-dir <spec@d37901e> --allow-spec-drift \
  --select 'coverage/*'
#   coverage-status-terminated.INVALID.ttl reports NO_VIOLATION: nothing rejects it,
#   because the property is unconstrained there. 44 constraint checks ran, all on
#   the plan's other properties, which is exactly the silent-acceptance the
#   release closes.

# GREEN: against the pin now named in scripts/SPEC_PIN (coverage v1.5).
python3 scripts/run_conformance.py --spec-dir <spec@pin> --select 'coverage/*'
#   2 passed / 0 failed, 47 constraint checks each.
```

The check count rising 44 → 47 on the same two records is the binding itself
becoming reachable.

Cross-checked with `cascade validate --shapes <spec shapes>` (cascade-cli 0.17.0,
a different SHACL engine): both verdicts agree with this runner's.
