# Genomics Conformance Fixtures — Inventory

**Task:** TASK-0.7 (structure-only — `expected.ttl` files are placeholders)
**Source:** `cascadeprotocol.org/drafts/genomics-v1/reference-corpus/` (see source `INVENTORY.md` there for acquisition provenance, dated 2026-05-04)
**Vocabulary covered:** `genomics/v1-draft.0.1`
**Purpose:** Drive `cascade convert --from <format>` importer development. Each fixture pairs a real-world input with a future `expected.ttl` oracle and a `gaps.json` that captures vocabulary gaps surfaced during conversion.

## Naming convention

Per fixture triple:

- `<id>.input.<ext>` — verbatim copy from the reference corpus (filename minus extension becomes `<id>`).
- `<id>.expected.ttl` — placeholder stub at TASK-0.7. Replaced by canonical Cascade Turtle output when the corresponding importer ships.
- `<id>.gaps.json` — placeholder empty array `[]` at TASK-0.7. Populated with `VocabularyGap` entries during importer development whenever an input concept has no mapping in `genomics/v1`.

## Fixtures

### `fhir-genomics-ig/` — 7 bundles

Public examples from the HL7 FHIR Genomics Reporting IG. Importer ships in **Phase 1** (`fhir-genomics-converter`).

| Fixture id | Scenario | Contents |
|------------|----------|----------|
| `Bundle-bundle-cgexample` | Comprehensive germline report | 17 resources: DiagnosticReport + Patient + Specimen + Lab + ServiceRequest + 11 Observations (discrete variant, complex variant, haplotype, genotype, disease-pathogenicity, metabolism, efficacy, high-risk implication) + Task |
| `Bundle-bundle-pgxexample` | Pharmacogenomics | PGx-focused bundle with star-allele observations and therapeutic implications |
| `Bundle-bundle-oncology-diagnostic` | Somatic oncology | Tumor variant report scenario (not germline workflow) |
| `Bundle-bundle-oncologyexamples-r4` | Oncology comprehensive | Larger somatic example |
| `Bundle-bundle-compound-heterozygote` | Compound heterozygote | Canonical 3-Observation pattern: variant 1 + variant 2 + relationship observation |
| `Bundle-bundle-CG-IG-HLA-FullBundle-01` | HLA typing | Allele-string-format result |
| `Bundle-bundle-complexVariant-nonHGVS` | Non-HGVS complex variant | Variants too complex for HGVS string representation |

### `clinvar/` — 4 VCV records

NCBI ClinVar Variation Archive XML, fetched via E-utilities. Importer ships in **Phase 2A** (`clinvar-converter`).

| Fixture id | Variant | Gene / Condition | Why included |
|------------|---------|------------------|--------------|
| `VCV000017661-BRCA1` | BRCA1 c.181T>G (p.Cys61Gly) | HBOC | 72 submitters, expert panel reviewed — multi-submitter aggregation |
| `VCV000055448-BRCA2-pathogenic` | BRCA2 (pathogenic) | HBOC | Real version of the variant in our example draft |
| `VCV000208804-MLH1-LynchSyndrome` | MLH1 | Lynch syndrome | Mismatch-repair, distinct counseling pathway |
| `VCV000007105-CFTR-deltaF508` | CFTR ΔF508 | Cystic fibrosis | Autosomal recessive — exercises inheritance/zygosity model |

### `phenopackets/` — 9 examples

GA4GH Phenopacket Schema v2 reference cases. Importer ships in **Phase 2B** (`phenopacket-converter`).

| Fixture id | Scenario | Notable content |
|------------|----------|-----------------|
| `retinoblastoma` | Pediatric cancer | Subject + 4 HPO phenotypes + measurements + biosamples + interpretations + diseases + medical actions + metadata. Most complete single-case example. |
| `marfan` | Connective tissue disease | Minimal phenotype-only case |
| `bethlem-myopathy` | Neuromuscular | Adult Mendelian case |
| `tpm3-myopathy` | Myopathy variant interpretation | Schreckenbach 2014 published case — TPM3 II.2 |
| `covid` | Acute illness | Non-genetic example showing schema coverage |
| `v2-phenopacket` | Schema reference | Single-individual canonical |
| `v2-family` | Trio | Pedigree with parents + proband |
| `v2-cohort` | Cohort | Multiple individuals |
| `biosamples-SAMN05324082` | NCBI BioSample reference | Sample/specimen-only example |

### `vcf/` — 1 partial

| Fixture id | Notes |
|------------|-------|
| `sample-clinvar` | First 64 KB of the weekly ClinVar GRCh38 VCF. Header + ~hundred records. Adequate for header-parsing tests; full-record importer needs a larger sample. Importer ships in **Phase 3**. |

### `vrs/` — 1 hand-built example

| Fixture id | Notes |
|------------|-------|
| `example-allele-BRCA2-deletion` | Hand-authored VRS Allele showing computed identifier pattern (`ga4gh:VA.<base64-hash>`), SequenceLocation with interval, LiteralSequenceExpression for state. Drives data-model decisions for the VRS property normalizer. Importer ships in **Phase 3**. |

## Gaps + counselor-letters / lab-reports

`lab-reports/` and `counselor-letters/` (Phases 5 / 6) are intentionally absent — they require user-provided artifacts (per source-corpus HANDBACK).
