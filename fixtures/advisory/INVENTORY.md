# Advisory Conformance Fixtures — Inventory

**Task:** TASK-0.7 (structure-only — `expected.ttl` files are placeholders)
**Source:** `cascadeprotocol.org/drafts/advisory-v1/`
**Vocabulary covered:** `advisory/v1-draft.0.1`
**Purpose:** Validate `cascade-cli` advisory-patch application against the Cascade Advisory Protocol (CAP). Each fixture pairs an LD-Patch input with a future `expected.ttl` (the post-application Cascade Turtle state) and a `gaps.json` capturing vocabulary gaps.

## Naming convention

Per fixture triple:

- `<id>.input.ldpatch` — verbatim copy from `cascadeprotocol.org/drafts/advisory-v1/`.
- `<id>.expected.ttl` — placeholder stub at TASK-0.7. Replaced by the canonical post-patch state once the **Phase 4.5** advisory-application pipeline lands.
- `<id>.gaps.json` — placeholder empty array `[]` at TASK-0.7. Populated with `VocabularyGap` entries when application surfaces unmapped concepts.

## Fixtures

| Fixture id | Scenario | Patch class | Why included |
|------------|----------|-------------|--------------|
| `BRCA2-reclassification` | Variant reclassification (LP → P) | `genomics:VariantReclassification` | Canonical example of a `prov:wasRevisionOf` chain on a `genomics:VariantInterpretation` driven by a CAP patch. Exercises auto-apply policy + advisory-class taxonomy. |
| `CPIC-cyp2c19-warfarin` | Drug–gene interaction guideline update | `genomics:DrugInteraction` | CPIC-style PGx advisory affecting a `genomics:Diplotype`/star-allele record. Exercises trusted-issuer scoping + auto-apply policy at scale. |

Both fixtures reference only terms defined in `advisory/v0.1` and whitelisted external prefixes (per `advisory-v1/PROFILE.md`).
