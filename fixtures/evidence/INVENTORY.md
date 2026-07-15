# Evidence Conformance Fixtures (Inventory)

**Task:** Batched draft sync (spec `PENDING_DOWNSTREAM_SYNC.md` row 2).
**Source:** `cascade-workbench/fixtures/grounding/` (the grounding-gate set proven against the real validator during authoring).
**Vocabulary covered:** `evidence/v1-draft.0.2` (verdict-taxonomy-v2 facet model).
**Purpose:** SHACL-validation fixtures for the facet model and the generalized SHACL-Core grounding invariant on `evidence:Assertion`. The grounding outcome is expressed as orthogonal facets (`evidence:direction`, `evidence:basis`, `evidence:strength`, `evidence:settled`, `evidence:reason`, plus `evidence:confidence`); a grounded result of EITHER basis requires at least one `evidence:hasEvidenceLink`, and the facets must be mutually consistent.

## Fixture kind (read this; it differs from advisory/ and genomics/)

Unlike the `advisory/` and `genomics/` dirs (conversion oracles: `input` plus `expected.ttl` plus `gaps.json`), these are standalone SHACL-validation fixtures. Each file is validated directly and there is no conversion step:

- `<slug>.VALID.ttl` MUST pass `cascade validate`.
- `<slug>.INVALID.ttl` MUST fail `cascade validate` (it violates `evidence:AssertionShape`).

Expected pass/fail is encoded in the filename suffix (`.VALID.ttl` / `.INVALID.ttl`).

## Verification

Validated against the embedded `evidence.shapes.ttl` synced from `spec/` in `cascade-cli` (PR the-cascade-protocol/cascade-cli#16):

```sh
# from a built cascade-cli checkout:
node dist/index.js validate <path/to/fixture>.ttl
```

All VALID fixtures PASS and all INVALID fixtures FAIL against those embedded shapes (demonstrated, not assumed).

## Fixtures

| Fixture id | Expect | Scenario |
|------------|--------|----------|
| `assertion-facet-record-grounded` | PASS | Canonical record-grounded assertion: settled Settled, direction Supports, basis Record, one record-citing evidence link. |
| `assertion-facet-literature-grounded` | PASS | Literature-grounded: settled Settled, direction Contradicts, basis Literature, one Citation link (title plus pmid). Proves the invariant covers EITHER basis. |
| `assertion-facet-needs-evidence` | PASS | Honest unresolved form: settled NeedsEvidence, direction None, basis None, a reason (NoRecord). No evidence links required. |
| `assertion-facet-grounded-no-evidence` | FAIL | Grounded result (Settled / Supports / Record) with ZERO evidence links. Violates the grounding invariant (the facet-model teeth). |
| `assertion-facet-mixed-no-evidence` | FAIL | Direction Mixed IS a grounded direction: conflicting evidence must be shown, so Mixed with zero links violates the invariant. |
| `assertion-facet-direction-without-basis` | FAIL | Facet inconsistency: a grounded direction (Supports) with basis None. A non-None direction requires a real basis. |
| `assertion-facet-needsevidence-grounded-direction` | FAIL | Facet inconsistency: settled NeedsEvidence carrying a grounded direction (Supports). Carries a link so the ONLY violation is the consistency constraint. |

The deprecated flat `evidence:verdict` branch (kept one release for draft-period data) is still accepted by `evidence:AssertionShape`; legacy-verdict fixtures are not carried here because the canonical serialized form is the facet model. Removal of the legacy branch is scheduled for v1.0 graduation (see `spec/PENDING_DOWNSTREAM_SYNC.md`).
