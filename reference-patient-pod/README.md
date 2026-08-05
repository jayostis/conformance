# Reference Patient Pod: Alex Rivera

> **Canonical location.** This pod is maintained in the `conformance` repository,
> at `reference-patient-pod/`. That is the only copy anyone should edit.
>
> It is also published at <https://cascadeprotocol.org/reference-patient-pod/>.
> That published copy is **generated**: `cascadeprotocol.org/scripts/sync-reference-pod.sh`
> copies this directory into the website and keeps the two byte-identical, and
> running that same script with `--check` fails if they ever drift apart. Edits
> made to the published copy are not edits to the pod; they are drift, and the
> check exists to find them.

## Patient Narrative

**Alex Rivera** is a 52-year-old male (DOB: August 15, 1973) living in Portland, Oregon. He works a desk job and maintains a moderate exercise routine, visiting the gym approximately three times per week. His emergency contact is his spouse, Maria Rivera.

Alex manages several chronic conditions typical of a middle-aged American male:

- **Essential Hypertension** (diagnosed 2015) -- controlled with lisinopril 20 mg daily, previously augmented with amlodipine 5 mg which was discontinued in June 2024 after blood pressure stabilized.
- **Type 2 Diabetes Mellitus** (diagnosed 2018) -- managed with metformin 1000 mg twice daily. His most recent HbA1c is 7.2%, slightly above the 7.0% target, suggesting room for improved glycemic control.
- **Hyperlipidemia** (diagnosed 2019) -- treated with atorvastatin 40 mg nightly. Lipid panel shows total cholesterol 198 mg/dL and LDL 112 mg/dL (near but not at goal), with triglycerides elevated at 190 mg/dL.
- **Mild Persistent Asthma** (diagnosed 2005) -- well-controlled, uses albuterol inhaler as needed.
- **Seasonal Allergic Rhinitis** (diagnosed 2010) -- managed with over-the-counter cetirizine 10 mg daily during allergy seasons.

Alex has known drug allergies to **penicillin** (moderate: rash and urticaria) and **sulfonamide antibiotics** (mild: rash), as well as a **shellfish** food allergy (severe: anaphylaxis risk, carries EpiPen).

He wears an **Apple Watch Series 9** which tracks daily heart rate, activity (steps, active energy, exercise minutes), and sleep. He also uses an **Omron Evolv** home blood pressure monitor for regular self-monitoring. His wellness data shows a typical pattern: more active on weekdays with gym sessions (8,000-12,000 steps), lower activity on weekends (4,000-5,000 steps), and sleep averaging 7.1 hours per night with occasional poor sleep nights (5.5-5.9 hours).

His immunizations are up to date, including the 2024 COVID-19 booster (Pfizer), annual influenza vaccine, Tdap, and PCV20 pneumococcal vaccine.

Alex carries primary health insurance through **Blue Cross Blue Shield** (PPO plan) since January 2020.

---

## Medication Interaction Scenario

This reference pod contains a deliberately embedded **cross-provenance medication interaction** that an AI agent should be able to detect:

### The Scenario

Alex's physician prescribed **lisinopril** (an ACE inhibitor) for hypertension. ACE inhibitors reduce aldosterone secretion, which decreases renal potassium excretion. Independently, Alex self-initiated a **potassium chloride 20 mEq** daily supplement to address occasional leg cramps -- without informing his physician.

His most recent **serum potassium** lab result is **5.1 mEq/L**, which is above the normal range of 3.5-5.0 mEq/L. This borderline hyperkalemia is clinically significant and likely caused by the combination of the ACE inhibitor's potassium-sparing effect and the supplemental potassium intake.

### Why This Matters for Agent Development

Detecting this interaction requires correlating data across **three different files** with **two different provenance layers**:

| File | Provenance | Key Data |
|------|-----------|----------|
| `clinical/medications.ttl` | `cascade:ClinicalGenerated` | Lisinopril 20 mg (ACE inhibitor) |
| `wellness/supplements.ttl` | `cascade:SelfReported` | Potassium Chloride 20 mEq |
| `clinical/lab-results.ttl` | `cascade:ClinicalGenerated` | Serum K+ 5.1 mEq/L (borderline high) |

An agent that only examines clinical records would miss the self-reported potassium supplement. An agent that only checks for drug-drug interactions would miss this drug-supplement interaction. Only an agent that correlates across provenance boundaries can identify the complete picture.

---

## Data Inventory

| File | Domain | Type | Records | Provenance | Schema |
|------|--------|------|---------|------------|--------|
| `clinical/patient-profile.ttl` | Clinical | PatientProfile | 1 | ClinicalGenerated | 2.0 |
| `clinical/conditions.ttl` | Clinical | ConditionRecord | 5 | ClinicalGenerated | 1.3 |
| `clinical/medications.ttl` | Clinical | Medication | 8 | ClinicalGenerated + SelfReported | 1.3 |
| `clinical/allergies.ttl` | Clinical | AllergyRecord | 3 | ClinicalGenerated + SelfReported | 1.3 |
| `clinical/lab-results.ttl` | Clinical | LabResultRecord | 11 | ClinicalGenerated | 1.3 |
| `clinical/immunizations.ttl` | Clinical | ImmunizationRecord | 4 | ClinicalGenerated | 1.3 |
| `clinical/vital-signs.ttl` | Clinical | VitalSign | 30 days | ClinicalGenerated | 1.3 |
| `clinical/insurance.ttl` | Clinical | CoverageRecord | 1 | ClinicalGenerated | 1.3 |
| `wellness/heart-rate.ttl` | Wellness | DailyVitalReading | 30 days | DeviceGenerated | 1.3 |
| `wellness/blood-pressure.ttl` | Wellness | Observation (FHIR) | 30 days | DeviceGenerated | 1.3 |
| `wellness/activity.ttl` | Wellness | DailyActivitySnapshot | 30 days | DeviceGenerated | 1.3 |
| `wellness/sleep.ttl` | Wellness | DailySleepSnapshot | 30 days | DeviceGenerated | 1.3 |
| `wellness/supplements.ttl` | Wellness | Supplement | 3 | SelfReported | 1.3 |

### Totals

- **Clinical records:** 33 discrete records + 30 days vital signs
- **Wellness records:** 120 daily snapshots (4 types x 30 days) + 3 supplements
- **Provenance layers:** 3 (ClinicalGenerated, DeviceGenerated, SelfReported)
- **Date range:** 2026-01-20 to 2026-02-18 (30 days for time-series data)

---

## Provenance Summary

The Cascade Protocol tracks three layers of data provenance, all represented in this pod:

| Provenance Class | RDF Value | Source | Files |
|-----------------|-----------|--------|-------|
| **ClinicalGenerated** | `cascade:ClinicalGenerated` | Electronic Health Record (EHR) export | All `clinical/` files |
| **DeviceGenerated** | `cascade:DeviceGenerated` | Apple Watch Series 9 (HealthKit), Omron Evolv | `wellness/heart-rate.ttl`, `wellness/blood-pressure.ttl`, `wellness/activity.ttl`, `wellness/sleep.ttl` |
| **SelfReported** | `cascade:SelfReported` | Patient-entered data | `wellness/supplements.ttl`, some records in `clinical/medications.ttl` and `clinical/allergies.ttl` |

Each record includes a `cascade:dataProvenance` triple linking it to its provenance class. Device-generated records also include `prov:wasGeneratedBy` blocks identifying the specific device and data source.

---

## Namespace Prefixes

All TTL files in this pod use the following standard Cascade Protocol prefixes:

| Prefix | Namespace | Usage |
|--------|-----------|-------|
| `cascade:` | `https://ns.cascadeprotocol.org/core/v1#` | Core protocol terms (provenance, schema version) |
| `health:` | `https://ns.cascadeprotocol.org/health/v1#` | Wellness/device data types |
| `clinical:` | `https://ns.cascadeprotocol.org/clinical/v1#` | Clinical record types |
| `fhir:` | `http://hl7.org/fhir/` | FHIR resource types (Observation, MedicationStatement) |
| `sct:` | `http://snomed.info/id/` | SNOMED CT concept codes |
| `loinc:` | `http://loinc.org/rdf#` | LOINC observation codes |
| `rxnorm:` | `http://www.nlm.nih.gov/research/umls/rxnorm/` | RxNorm medication codes |
| `icd10:` | `http://hl7.org/fhir/sid/icd-10-cm/` | ICD-10-CM diagnosis codes |
| `cvx:` | `http://hl7.org/fhir/sid/cvx/` | CVX immunization codes |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` | XML Schema datatypes |
| `prov:` | `http://www.w3.org/ns/prov#` | W3C PROV-O provenance ontology |

---

## Directory Structure

```
reference-patient-pod/
  .well-known/
    solid                          # Solid protocol discovery document
  profile/
    card.ttl                       # WebID profile (foaf:Person)
  settings/
    publicTypeIndex.ttl            # Clinical data type registry
    privateTypeIndex.ttl           # Wellness data type registry
  clinical/
    patient-profile.ttl            # Demographics, emergency contact
    conditions.ttl                 # 5 active conditions
    medications.ttl                # 8 medications (1 discontinued)
    allergies.ttl                  # 3 allergies (drug + food)
    lab-results.ttl                # 11 lab results with LOINC codes
    immunizations.ttl              # 4 immunizations with CVX codes
    vital-signs.ttl                # 30 days clinical vital signs
    insurance.ttl                  # BCBS PPO coverage
  wellness/
    heart-rate.ttl                 # 30 days resting HR (Apple Watch)
    blood-pressure.ttl             # 30 days home BP (Omron Evolv)
    activity.ttl                   # 30 days steps/energy/exercise
    sleep.ttl                      # 30 days sleep duration/quality
    supplements.ttl                # 3 self-reported supplements
  index.ttl                        # Root LDP container listing
  manifest.ttl                     # Export provenance metadata
  README.md                        # This file
```

---

## Disclaimer

**This is entirely synthetic data.** Alex Rivera is a fictional patient created for the purpose of demonstrating the Cascade Protocol data model, testing SDK serialization/deserialization, and developing AI agent capabilities for cross-provenance health data correlation.

No real patient data was used in the creation of this reference pod. Medical details (conditions, medications, lab values, vital signs) are realistic but fabricated. Do not use this data for any clinical decision-making.

This reference pod is maintained as part of the [Cascade Protocol](https://cascadeprotocol.org) open specification.
