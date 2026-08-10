# Core Conformance Fixtures (Inventory)

**Vocabulary covered:** `core` v3.3 (`cascade:AIExtractionActivity` provenance) and
`core` v3.5 (the ORIGIN axis, `cascade:sourceIdentity`).

## Fixture kind

Standalone SHACL-validation fixtures, not conversion oracles. Each file is
validated directly and carries its polarity in its name:

- `<slug>.VALID.ttl` (and the unsuffixed legacy `ai-extracted-medication.ttl`)
  MUST pass validation.
- `<slug>.INVALID.ttl` MUST fail validation.

Every byte is synthetic: invented organizations, endpoints, identifiers, people
and values. The OIDs are under the HL7 example arc.

## The three source axes (core v3.5)

A record carries three different answers to three different questions, and the
fixtures below exist because collapsing any two of them is a defect that has been
measured on real pods:

| Axis | Property | Question |
|---|---|---|
| ORIGIN | `cascade:sourceIdentity` | Which ORGANIZATION the record came from, canonically, whatever transport carried it. The only one usable as a reconciliation key. |
| LABEL | `clinical:sourceEHR` | What to CALL that organization on screen. Source-worded, so two spellings of one organization are two labels. |
| INGESTION | `cascade:sourceSystem` | How and when the data entered the Pod. Never an origin. |

## Fixtures

| Fixture | Expect | Scenario |
|---|---|---|
| `ai-extracted-medication.ttl` | PASS | An `AIExtracted` medication linked to its `cascade:AIExtractionActivity` (core v3.0/v3.3). |
| `source-identity-org.VALID.ttl` | PASS | `org:` tier. An organization was derivable, so the identity carries a normalized slug. All three axes present and all three saying different things. |
| `source-identity-namespace.VALID.ttl` | PASS | `ns:` tier. No organization was derivable, but the record's identifiers have an assigning authority (a C-CDA `<id>` root OID). |
| `source-identity-transport.VALID.ttl` | PASS | `transport:` tier, the honest last resort. Nothing named or located an organization, so the value restates the ingestion label under a prefix that tells a consumer the origin is UNKNOWN. |
| `source-identity-two-transports-one-system.VALID.ttl` | PASS | **The invariant.** One synthetic health system exporting twice. The LABEL differs (endpoint domain vs custodian organization name) and the INGESTION batch differs, and the ORIGIN is identical. A consumer grouping by ORIGIN sees one system; a consumer grouping by either other axis sees two. |
| `source-identity-unprefixed.INVALID.ttl` | FAIL | The display label written straight into the origin axis, with no scheme, so a consumer cannot tell what was actually derived. Rejected on `sh:pattern`. |
| `source-identity-repeated.INVALID.ttl` | FAIL | Two origins on one record. Both values are individually well formed, so only the cardinality constraint catches it. Rejected on `sh:maxCount`. |

## Verification

Measured in both directions, which is the only thing that makes the two negatives
mean anything:

```sh
# RED first: against the previous pin (spec 9461fa9, core 3.4), where
# cascade:SourceIdentityShape does not exist.
python3 scripts/run_conformance.py --spec-dir <spec@9461fa9> --allow-spec-drift \
  --select 'core/source-identity*'
#   4 passed / 2 failed — both negatives report NO_VIOLATION: nothing rejects them.

# GREEN: against the pin now named in scripts/SPEC_PIN (core 3.5).
python3 scripts/run_conformance.py --spec-dir <spec@pin> --select 'core/*'
#   7 passed / 0 failed, 319 constraint checks.
```

Absence of `cascade:sourceIdentity` is deliberately NOT a finding in core v3.5, so
there is no negative fixture for a record that omits it. Every other fixture in
this repository omits it and continues to pass, which is that compatibility claim
being exercised 122 times rather than asserted once.
