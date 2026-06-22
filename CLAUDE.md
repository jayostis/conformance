# conformance — Agent Context

## Repository Purpose

Conformance test fixtures and reference Patient Pod for the Cascade Protocol.
Downstream SDKs (sdk-typescript, sdk-python) and tools (cascade-cli) must pass all fixtures here before releasing.

## Key Architecture

- `fixtures/` — JSON fixture files, one per record instance. Named `{type}-{id}.json`.
- `schema/fixture-schema.json` — JSON Schema for the fixture format (includes `dataType` enum).
- `reference-patient-pod/` — Example Turtle files showing real schema usage.

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

### Vocabulary coverage (as of 2026-06-22)

Covered up to core=3.3, health=2.4, clinical=1.9 (matches `spec/VOCAB_VERSIONS`). Recent additions:
- core v3.3: `cascade:AIAsserted` provenance leaf (fixture `social-002`); `cascade:ProxyAgent` caregiver-proxy with ProxyAgentShape required-field coverage (fixtures `proxy-001` valid, `proxy-002` missing `proxyRelationship`).
- health v2.4: `health:SocialHistoryRecord` + `smokingStatus`/`alcoholUse`/`exerciseFrequency`/`occupationalExposure` (fixture `social-001`).
- clinical v1.9: `cascade:AIExtracted` now valid in every clinical record's `dataProvenance` enum (fixture `med-011`, an AIExtracted Medication).

### Known gaps

See `VOCAB_VERSIONS` comments. Missing fixture categories:
- `encounter` (Clinical v1.7)
- `medication-administration` (Clinical v1.7)
- `implanted-device` (Clinical v1.7)
- `imaging-study` (Clinical v1.7)
- `claim-record` (Coverage v1.3)
- `benefit-statement` (Coverage v1.3)
- `denial-notice` (Coverage v1.3)
- FHIR passthrough properties on existing records (Core v2.8)
- Pre-existing: `proc-001/002/003` use `dataType: "ProcedureRecord"` which is not in the fixture-schema enum (`Procedure`); these three fail `schema/fixture-schema.json` validation and predate this change.

## Fixture Format

Each fixture is a JSON object with the structure defined in `schema/fixture-schema.json`.
`dataType` must match a class name defined in the relevant vocabulary TTL.

## Commit Conventions

```
feat(fixtures): add {ClassName} fixtures (clinical v1.7)
fix(fixtures): {description}
```
