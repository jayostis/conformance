# Workbench Conformance Fixtures (Inventory)

**Task:** Batched draft sync (spec `PENDING_DOWNSTREAM_SYNC.md` rows 1 and 3).
**Source:** the shapes-verification set from the workbench v1-draft.0.5 authoring PR (notes) and the v1-draft.0.4 filing-label axis.
**Vocabulary covered:** `workbench/v1-draft.0.5` (notes / research-flags / follow-ups as W3C Web Annotations) and `workbench/v1-draft.0.4` (`workbench:userSourceLabel` filing axis).
**Purpose:** SHACL-validation fixtures for the note substrate shapes (`WebAnnotationShape`, `CommentingBodyShape`, `FollowUpShape`) and for the `userSourceLabel` filing overlay (which reuses the already-shaped `workbench:Annotation` string predicates, so it adds no new shape).

## Fixture kind (read this; it differs from advisory/ and genomics/)

Unlike the `advisory/` and `genomics/` dirs (conversion oracles: `input` plus `expected.ttl` plus `gaps.json`), these are standalone SHACL-validation fixtures. Each file is validated directly:

- `<slug>.VALID.ttl` MUST pass `cascade validate`.
- `<slug>.INVALID.ttl` MUST fail `cascade validate`.

Expected pass/fail is encoded in the filename suffix (`.VALID.ttl` / `.INVALID.ttl`).

## Verification

Validated against the embedded `workbench.shapes.ttl` synced from `spec/` in `cascade-cli` (PR the-cascade-protocol/cascade-cli#16):

```sh
# from a built cascade-cli checkout:
node dist/index.js validate <path/to/fixture>.ttl
```

All VALID fixtures PASS and all INVALID fixtures FAIL against those embedded shapes (demonstrated, not assumed). The three violation classes each fire on their dedicated INVALID fixture.

## Fixtures: notes substrate (v1-draft.0.5)

| Fixture id | Expect | Scenario |
|------------|--------|----------|
| `note-commenting-multitarget` | PASS | Caregiver note (`oa:commenting`) over two targets, with an `oa:TextualBody` and required PROV-O attribution. |
| `note-followup-vtodo` | PASS | Follow-up (`workbench:followUp`), dual-typed `cal:Vtodo`, with required `ical:status` and optional `ical:due`. |
| `note-questioning-selector` | PASS | Research flag (`oa:questioning`) anchored to a passage via `oa:SpecificResource` plus `oa:TextQuoteSelector`. |
| `note-followup-without-status` | FAIL | Follow-up with no `ical:status`. Violates `FollowUpShape`. |
| `note-commenting-without-body` | FAIL | Commenting note with no body. Violates `CommentingBodyShape`. |
| `note-floating-annotation` | FAIL | No `oa:hasTarget` and no `prov:wasAttributedTo`. Violates `WebAnnotationShape`. |

## Fixtures: filing axis (v1-draft.0.4)

| Fixture id | Expect | Scenario |
|------------|--------|----------|
| `filing-label-refile` | PASS | A re-filed record: a `workbench:Annotation` overlay carrying `annotationProperty "workbench:userSourceLabel"` plus `annotationValue`, with `cascade:SelfReported` provenance. Does not overwrite `clinical:sourceEHR`. |
