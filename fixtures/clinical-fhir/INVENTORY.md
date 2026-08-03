# General clinical FHIR fixtures — inventory

**Purpose:** hold every SDK's FHIR importer to deterministic, non-destructive record
identity on ordinary clinical resources.

**Vocabulary exercised:** `core`, `health`, `clinical` (Patient, Condition,
AllergyIntolerance, Immunization, Observation as vital sign and as laboratory result,
MedicationStatement, Encounter, Procedure).

## Why this directory exists

Before it, the corpus had no general clinical FHIR fixtures at all. Searching the whole
repository for `"resourceType"` returned **7 files, every one of them a FHIR Genomics
bundle**. So the FHIR clinical path — the one every SMART on FHIR pull and every Apple
Health import runs through, and by a wide margin the most reachable importer in the
product — had **zero shared-corpus coverage**. Its only tests lived inside a single SDK's
own test directory, which means the other SDKs were never held to any of it.

And **every fixture that did exist carried an `id`**. That is the more consequential half.
A resource with an id gets its identity handed to it; a resource without one has to derive
identity from its own content, and that derivation is where records get silently merged.
A corpus in which nothing is id-less cannot detect the one defect that only appears when
something is.

Both gaps are closed here: each clinical type appears in an id-bearing form and in an
id-less form, and the id-less pairs are constructed so that a merge would destroy
information a reader can plainly see is different.

## What is asserted, and why it is not a list of IRIs

`identity-expectations.json` states **relations** between fixtures — two must be distinct,
two must be the same — rather than pinning literal IRIs.

A relation is the thing that actually has to hold for the data to survive. It is also the
same claim in every SDK regardless of how each spells its hash, and it does not have to be
regenerated every time an identity key is legitimately widened. A pinned IRI would have to
be, and a regenerated oracle is vacuously green against its own generator.

Literal cross-SDK vectors already exist for the hash function itself, in
`fixtures/deterministic-ids/test-vectors.json`. Those cover the algorithm. These cover the
importer's choice of what to put into it, which is where the failures have actually been.

The two failure directions are not symmetric, and both are covered:

- **A split** (one record minting two identities) is recoverable: all the data is present
  and can be reconciled later, by a tool or a person, because both copies are there to
  compare. Covered by the `same` expectation.
- **A merge** (two records minting one identity) is not: the second record's content is
  simply gone, and nothing downstream can know it existed. Covered by the `distinct`
  expectations, which are the majority for that reason.

## Fixtures

| Group | Fixtures | What it exercises |
|---|---|---|
| Patient | `patient-with-id`, `patient-no-id` | An anonymous identity must never collide with an assigned one |
| Condition (structured) | `condition-with-id`, `condition-no-id-structured-hypertension`, `condition-no-id-structured-diabetes` | The baseline content-hash path |
| Condition (narrative-only) | `condition-no-id-narrative-diabetes`, `condition-no-id-narrative-breast-cancer` | No code, no onset, no subject — only prose. See below |
| Condition (server metadata) | `condition-with-id-meta-fetch-a`, `condition-with-id-meta-fetch-b` | One record, two server reads, differing `meta.versionId` / `lastUpdated` / `source` |
| AllergyIntolerance | `allergy-with-id`, `allergy-no-id-penicillin`, `allergy-no-id-sulfa` | Merging two allergies tells a clinician a patient is safe to receive something they react to |
| Immunization | `immunization-with-id`, `immunization-no-id-2024`, `immunization-no-id-2025` | Same vaccine, two years: merging erases a dose |
| Observation (vital) | `vital-heartrate-with-id`, `vital-heartrate-no-id-morning`, `vital-heartrate-no-id-evening` | Repeat readings inside one day are a clinical series, not duplicates |
| Observation (lab) | `lab-glucose-fasting`, `lab-glucose-postprandial`, and id-less variants of each | Same patient, same LOINC, same day, **different measured value** |
| MedicationStatement | `medication-with-id`, `medication-no-id-bare`, `medication-no-id-note-only` | A record with nothing, versus one whose only content is a note |
| Encounter | `encounter-with-id`, `encounter-no-id-may`, `encounter-no-id-june` | Two visits on different dates |
| Procedure | `procedure-with-id`, `procedure-no-id-colonoscopy`, `procedure-no-id-echocardiogram` | Two different procedures |

### The three fixtures worth reading closely

**The narrative-only Conditions.** Their only content is `text.div`, reading "Type 2
diabetes mellitus" and "Metastatic breast cancer". They are trivially different to any
reader. An importer that excludes narrative from its content hash while leaving the
`resourceType` discriminator IN it makes both look non-empty, hashes both to
`{"resourceType":"Condition"}` — a value identical for every Condition in existence — and
merges two unrelated diagnoses. **No id-bearing fixture can surface that**, which is
precisely why a corpus of only id-bearing fixtures never did.

**The two same-day glucose results.** A fasting 95 mg/dL and a post-prandial 310 mg/dL.
Serial same-day results are ordinary clinical practice: glucose curves, troponin series,
repeat potassium, pre- and post-dialysis. An identity key of `{patient, code, date}`
collapses them, one value is written and the other is destroyed, and a normal result and a
critical one become interchangeable outputs of the same input.

**The bare MedicationStatement versus the note-only one.** An importer that substitutes a
placeholder drug name before minting turns "we do not know" into "these are the same
record". Its content hash then succeeds with a **constant**, which is indistinguishable
from the hash failing except that it merges instead of splitting.

## Measured, twice

Every expectation was evaluated against a real build rather than reasoned about, both
before and after the identity fixes that were in flight when these fixtures were written.

**Against the previously published importer: 9 of 12 held.** The three that did not:

| Expectation | Result |
|---|---|
| `lab-same-day-same-code-different-value` | both glucose results minted one IRI |
| `lab-same-day-same-code-different-value-id-less` | same, id-less |
| `medication-no-id-differs-only-in-narrative` | both minted one IRI |

All three were the same shape: an identity key narrower than the records it was
identifying. These fixtures were written to make exactly those three visible.

**Against a build carrying the lab identity key and the reconciler collision split: 12 of
12 hold**, which is why every entry now reads `status: "satisfied"`.

That is the intended lifecycle of the `status` field, and it is worth stating because it
is the only part of this corpus that can rot. A consumer should assert a
`not-yet-satisfied` entry in its **current** direction, so that an implementation
satisfying it turns the suite red and forces this file to be updated. The field is a
tripwire in both directions, never a reason to skip an assertion.

### A second thing the measurement showed

Four clinical types **discard a resource's own server-assigned `id`** and identify it by a
content hash instead, so an id-bearing resource and an id-less one with the same content
land on one IRI:

```
urn:uuid:13bac2c5-…  condition-with-id, condition-no-id-structured-hypertension,
                     condition-with-id-meta-fetch-a, condition-with-id-meta-fetch-b
urn:uuid:76ac6e1a-…  allergy-with-id, allergy-no-id-penicillin
urn:uuid:bc5a8514-…  immunization-with-id, immunization-no-id-2025
```

Vital signs do the opposite: `vital-heartrate-with-id` and
`vital-heartrate-no-id-morning` carry identical content and mint **different** IRIs,
because that path honours the `id`.

That asymmetry is not asserted either way here, because whether an id should win is a
design question rather than a correctness one — for Condition, Allergy and Immunization
the merged pairs really are the same clinical fact, and no data is lost. It is recorded
because it is the same mechanism that produced the glucose failure above, where the two
records are **not** the same fact, and because a corpus is the right place for it to be
visible rather than rediscovered.

## Status

**This repository has no runner and no CI**: no workflow, no `package.json`, no
`Makefile`. Its fixtures execute only because suites in consuming repositories reach into
a checkout of this repo and assert on them. So a fixture added here with no consuming test
somewhere else is an inert file that will never run anywhere.

A consuming suite exists for `cascade-cli`. `sdk-typescript`, `sdk-python` and the Swift
SDK still need one each, and until they have one they are exactly as unprotected from this
defect class as they were before these fixtures existed — which was the point of adding
them. The expectations are stated as relations rather than as pinned IRIs specifically to
make that port cheap: a consumer asserts "these two must not share an identity" without
reproducing any particular implementation's hash.
