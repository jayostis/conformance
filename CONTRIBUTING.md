# Contributing to conformance

This repository is the gate between the Cascade Protocol specification and everything that implements it. It holds the conformance fixtures every SDK and tool must pass, and the canonical reference Patient Pod. Contributions are typically a new fixture for a class the vocabulary gained, a negative fixture for a constraint nothing currently exercises, or a fix to the runner or the ratchet.

## Before you start

- All open issues: <https://github.com/search?q=org%3Athe-cascade-protocol+is%3Aissue+is%3Aopen>
- Good first issues: <https://github.com/search?q=org%3Athe-cascade-protocol+is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22>

`VOCAB_VERSIONS` and the "Known gaps" section of `CLAUDE.md` name, class by class, what has no fixture and what has no shape. Those are the openings.

## Development setup

**`spec` must be cloned as a sibling directory**, and it must be at the revision `scripts/SPEC_PIN` names. The runner refuses to run against a different one, because a suite without a pin silently tracks whatever is on `spec` `main`, and a run that passed yesterday can pass today for a different reason.

```
<parent>/
  conformance/
  spec/
```

```bash
git clone https://github.com/the-cascade-protocol/conformance.git
git clone https://github.com/the-cascade-protocol/spec.git
cd conformance

# Use a virtual environment and ACTIVATE it. A current macOS or Debian-family
# Python refuses a bare `pip install` outright (PEP 668).
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt

# check spec out at the pinned commit.
# Read BOTH lines: `repo=` names which remote the commit is on, and it is not
# always the org. Reading only `commit=` fails with "reference is not a tree"
# whenever the pin is ahead of the-cascade-protocol/spec.
SPEC_REPO="$(grep '^repo=' scripts/SPEC_PIN | cut -d= -f2-)"
SPEC_COMMIT="$(grep '^commit=' scripts/SPEC_PIN | cut -d= -f2)"
git -C ../spec fetch "${SPEC_REPO}.git" "$SPEC_COMMIT"
git -C ../spec checkout "$SPEC_COMMIT"
```

CI runs Python 3.13.

## What must be green before review

```bash
source .venv/bin/activate

# 1. the truth: executes and reports every fixture. Exits 1 while any fails.
python3 scripts/run_conformance.py --spec-dir ../spec --json results.json

# 2. the gate: did anything get worse, or better without the record being updated?
python3 scripts/check_baseline.py --results results.json

# 3. the runner's own mutation tests: proof the runner and the ratchet can fail
python3 scripts/selftest_runner.py --spec-dir ../spec
```

The suite is red on its own terms and the report names every failure. **The job is green only when nothing got worse and nothing got better without the record being updated.** Every current failure is enumerated in `KNOWN_FAILURES.json`.

Reading the numbers correctly matters more here than anywhere else in the protocol:

- **The result depends on which `spec` revision you point at, so always say which.** The same fixtures score very differently against older vocabulary, because a fixture that no shape targets evaluates zero constraints and the runner counts a vacuous pass as a failure.
- **Never quote a number obtained with `--allow-spec-drift` as the suite's result.** The gate refuses to run at all when the baseline's `specPin` and the run's disagree.
- The counts measured at the current pin are recorded in the `scripts/SPEC_PIN` comment. Re-measure rather than repeating a number you read somewhere else.

## Commit messages

```
feat(fixtures): add {ClassName} fixtures (clinical v1.7)
fix(fixtures): {description}
```

## Opening a pull request

1. Branch from `main`.
2. Add the fixtures, run all three commands above, and confirm the gate passes.
3. Update `VOCAB_VERSIONS` to the vocabulary versions now covered.
4. Push and open a PR. `.github/PULL_REQUEST_TEMPLATE.md` fills in with the checklist; keep the items and tick them.
5. Record the fixture counts **and the `spec` revision you measured against** in the PR body. If you re-pinned, record both the old and new counts, in the same commit that moves the pin.
6. This repository gates SDK releases. Tag `conformance-v{YYYY-MM-DD}` promptly after merging so the SDKs have something to reference.

### Adding fixtures for a new class

- [ ] At least one **valid** fixture: `fixtures/{type}-{id}-valid.json`
- [ ] At least one **invalid** fixture (a missing required field, or a wrong datatype): `fixtures/{type}-{id}-invalid.json`
- [ ] `schema/fixture-schema.json` -- add the new `dataType` enum value
- [ ] Fixtures for new properties on existing classes, not only for new classes
- [ ] `VOCAB_VERSIONS` updated

**A fixture the runner reports `UNSHAPED` is not testing anything.** No shape targets it, so zero constraints ran and its PASS is vacuous. If the class has no shape yet, the shape belongs in `spec` first; a negative fixture is impossible until then, because there is no constraint to violate.

## The rules that are not negotiable

**Never resolve a failure by weakening the runner.** Do not skip a fixture, do not relax an assertion, do not delete or soften a shape to make a fixture pass.

**`KNOWN_FAILURES.json` is a ratchet, not a suppression list**, and what makes that true is worth preserving if you touch it:

- It hides nothing. `run_conformance.py` still executes every fixture and still prints every failure. Only the gate distinguishes known from new.
- **It fails in both directions.** An unlisted failure fails CI, and a listed failure that starts passing also fails CI, telling you to remove the entry. Without the second half the list only ever grows.
- Entries are keyed on **(fixture, reason)**. A fixture that moves from `UNSHAPED` to `VIOLATIONS` is a new fact and must fail even though it was already failing.
- It never grows on its own. Adding an entry is an explicit committed edit naming the repository that owns the fix. `--regenerate` marks anything new `UNASSIGNED`, and the gate refuses to pass while any entry is `UNASSIGNED`. Using it means saying so in the PR.

Both directions and every refusal are mutation-tested in `scripts/selftest_runner.py`. If you change the gate, change those tests to match, and show them failing first.

## The reference Patient Pod

`reference-patient-pod/` is the **canonical** home of the reference pod. `cascade-cli` reads it from here, and the documentation site publishes a generated copy held byte-identical to this directory. Edit the pod here and nowhere else.

## Vocabulary changes

Fixtures follow vocabulary; they do not lead it. A class with no shape in [`spec`](https://github.com/the-cascade-protocol/spec) cannot be meaningfully fixtured here. If your change needs new vocabulary, it starts there: read [`spec/CONTRIBUTING.md`](https://github.com/the-cascade-protocol/spec/blob/main/CONTRIBUTING.md) for the full seven-step propagation sequence. This repository is step 3, and it gates steps 5 and 6.

## Protocol context

<https://cascadeprotocol.org/llms.txt> is the protocol index: install, quick start, data types, MCP server, security model, vocabulary versions, deployment sequence. About 95 lines, meant to be read in full.

Do not load `llms-full.txt` from that site. It is roughly 1.3 MB, larger than most working contexts, and as of 2026-08-20 its ontology section is known to be incomplete. Read the TTL files in `spec` instead.

## Questions?

Open an issue on this repository, or a [discussion on `spec`](https://github.com/the-cascade-protocol/spec/discussions) for questions about the vocabulary itself rather than the fixtures.
