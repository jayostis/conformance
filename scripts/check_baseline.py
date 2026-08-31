#!/usr/bin/env python3
"""Ratchet the conformance suite against an enumerated baseline of known failures.

This is a GATE, not a filter. `run_conformance.py` still executes every fixture
and still prints every failure; nothing is skipped, suppressed, or summarised
away. This script only decides whether CI should be red, by asking a narrower
question than "did anything fail":

    did anything get WORSE, or did anything get BETTER without the record
    being updated?

Both directions fail. The second one is the whole point. A baseline that only
catches new failures is a list that grows and never shrinks, and a permanently
red job and a suppressed failure end the same way: nobody reads either. Failing
when a baselined fixture starts passing is what forces the list down.

Rules, in the order they are checked. Both documents are loaded first, and a
file that does not parse into a JSON object is exit 2 there — the rules below
all read fields off them, so a non-object would crash rather than be judged.

0.  Fixture keys are spelled POSIX on every platform, on both sides. A key
    carrying the OS-native separator matches nothing elsewhere, so it is exit 2
    naming the key rather than a verdict nobody can trust. Walking those keys is
    also where each document's key list is checked one level below rule 1's
    document shape: `fixtures`/`entries` must be a list of objects, each
    carrying a string `path`/`fixture` and -- wherever the entry is one rule 5
    actually keys -- a string `reason`. Both halves are checked because both are
    read by bare subscript downstream, so validating only the first leaves the
    identical failure one field over. A malformed entry is refused there, never
    skipped -- skipping drops it from the comparison and lets the gate draw a
    verdict from evidence it could not read.
1.  The baseline file must exist, parse into an object, and declare `entries`.
    A missing or unreadable baseline is exit 2, never a pass.
2.  The results file must describe a real run: at least one fixture executed and
    at least one constraint evaluated. A degenerate report cannot be ratcheted.
3.  The baseline records the `spec` revision it was measured against. Applying a
    baseline measured at one vocabulary to a run at another is exactly the
    "passed for a different reason" defect this repository keeps finding, so a
    mismatch is exit 2 with the one-line fix named.
4.  Every entry must name the repo that owns the fix. `UNASSIGNED` is exit 2, so
    a regenerated entry cannot slip in unexamined.
5.  Entries are keyed on (fixture, reason), not fixture alone. If a fixture goes
    UNSHAPED -> VIOLATIONS it is a new fact about the world and must fail, even
    though the fixture was already failing.

Exit codes: 0 nothing got worse and nothing silently got better,
            1 the ratchet was violated (either direction),
            2 the gate could not run, or the baseline is unusable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO / "KNOWN_FAILURES.json"

UNASSIGNED = "UNASSIGNED"


def abort(message: str) -> "int":
    sys.stderr.write(f"baseline gate: SELF-CHECK FAILED: {message}\n")
    raise SystemExit(2)


def load_json(path: Path, what: str) -> dict:
    if not path.is_file():
        abort(f"{what} not found at {path}. A gate with no {what} cannot decide anything.")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        abort(f"{what} at {path} could not be read: {exc}")
    else:
        # Parsing is not enough. A top-level array or scalar parses cleanly and
        # then has no `.get`, so every rule below would raise AttributeError and
        # exit 1 — the code CI reads as a real ratchet violation. Unusable input
        # is exit 2, here, before anything tries to read a verdict out of it.
        if not isinstance(loaded, dict):
            abort(f"{what} at {path} is not a JSON object but "
                  f"{type(loaded).__name__}. A gate cannot read anything out of it.")
        return loaded
    return {}  # unreachable, keeps type checkers quiet


def key(fixture: str, reason: str) -> tuple[str, str]:
    return (fixture, reason)


def render(k: tuple[str, str]) -> str:
    return f"{k[0]}  [{k[1]}]"


def fixture_keys(results: dict, baseline: dict,
                 baseline_name: str) -> list[tuple[str, str, str | None]]:
    """Every (fixture, reason) key in both documents, or exit 2 naming the one that is unusable.

    `load_json` refuses a document that is not an object; this refuses the same
    way one level down, where the keys actually live. Tolerating a malformed
    entry here would be worse than crashing on it: the entry is dropped, the gate
    carries on, and it draws a verdict from evidence it could not read. A results
    entry whose `path` is not a string vanishes, so the baselined fixture looks
    like it started passing while the unreadable one looks new -- one fixture
    counted in both directions at once, reported as exit 1, which CI reads as a
    genuine ratchet violation. A `fixtures` mapping iterates to bare strings and
    raises AttributeError further down, exit 1 again. Both are unusable input,
    and unusable input is exit 2 here, before anything reads a verdict out of it.

    BOTH halves of the key are validated, because rule 5 and `regenerate()` both
    read both by bare subscript. Checking only the first half leaves precisely
    the same defect one field over: an entry carrying a perfectly good `fixture`
    and no `reason` raises KeyError and exits 1, the code CI reads as a real
    ratchet violation. The baseline half is the one a human reaches --
    KNOWN_FAILURES.json is hand-edited by whoever owns a failure, so a dropped
    `reason` is an ordinary authoring slip, needing no Windows, no stale runner
    and no --regenerate to produce.

    A results fixture that PASSED is keyed by nothing: rule 5 and `regenerate()`
    both skip it, so its `reason` is never read and is not required here.
    Refusing input that is in fact usable is the mirror of the defect this
    function exists to prevent. `keyed` is spelled as the same predicate both
    consumers use, so the check and the use cannot drift apart.
    """
    triples: list[tuple[str, str, str | None]] = []
    for where, document, list_field, key_field, keyed in (
        ("results file", results, "fixtures", "path",
         lambda item: item.get("outcome") != "pass"),
        (baseline_name, baseline, "entries", "fixture",
         lambda item: True),
    ):
        items = document.get(list_field, [])
        if not isinstance(items, list):
            abort(f"{where}: `{list_field}` is not a list but {type(items).__name__}. "
                  f"A gate cannot read fixture keys out of it.")
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                abort(f"{where}: `{list_field}[{i}]` is not a JSON object but "
                      f"{type(item).__name__}. Every entry must carry a `{key_field}`.")
            k = item.get(key_field)
            if not isinstance(k, str):
                abort(f"{where}: `{list_field}[{i}].{key_field}` is not a string but "
                      f"{type(k).__name__} ({k!r}). A key that is not a string matches "
                      f"nothing, so any verdict drawn from it would be a guess.")
            reason = item.get("reason")
            if keyed(item) and not isinstance(reason, str):
                abort(f"{where}: `{list_field}[{i}].reason` is not a string but "
                      f"{type(reason).__name__} ({reason!r}), on {key_field} {k!r}. "
                      f"Entries are keyed on (fixture, reason); half a key matches "
                      f"nothing, so any verdict drawn from it would be a guess.")
            triples.append((f"{where}, {list_field}[].{key_field}", k, reason))
    return triples


def refuse_native_separator_keys(results: dict, baseline: dict, baseline_name: str) -> None:
    """A fixture key is spelled with `/` on every platform, or it is not usable.

    KNOWN_FAILURES.json is keyed on these strings and is shared across Linux,
    macOS and Windows, so a key carrying the OS-native separator matches nothing
    and turns one fixture into both a new failure and a baselined one that
    started passing. Normalising it here would make malformed input work
    silently; every other check in this file refuses instead, and so does this.

    Both sides are checked -- `fixture_keys` walks them and refuses anything it
    cannot key at all. The results half catches a stale or old-runner report
    locally; the baseline half catches keys a pre-fix `--regenerate` on Windows
    committed into the shared file, which is the half that protects everyone
    downstream.
    """
    offenders = [(where, k)
                 for where, k, _reason in fixture_keys(results, baseline, baseline_name)
                 if "\\" in k]
    if offenders:
        abort(
            f"{len(offenders)} fixture key(s) are spelled with the OS-native separator "
            "rather than POSIX `/`:\n" +
            "\n".join(f"    {where}: {k}" for where, k in offenders) +
            "\n  These keys match nothing on another platform, so any verdict drawn from "
            "them would be a guess.\n"
            "  Fix: re-run scripts/run_conformance.py to regenerate the results, and "
            "respell any committed\n"
            "  baseline entry with `/`."
        )


# --------------------------------------------------------------------------
# Regeneration
# --------------------------------------------------------------------------

def regenerate(baseline_path: Path, results: dict, existing: dict) -> int:
    """Rewrite the baseline from a results file. Deliberate, never automatic.

    Ownership and detail are carried over for entries that survive; anything new
    is written with ownedBy=UNASSIGNED, which the gate refuses to accept. So a
    regeneration cannot quietly absorb a failure nobody looked at.
    """
    previous = {key(e["fixture"], e["reason"]): e for e in existing.get("entries", [])}
    entries = []
    for f in results.get("fixtures", []):
        if f.get("outcome") == "pass":
            continue
        k = key(f["path"], f["reason"])
        prior = previous.get(k)
        entries.append({
            "fixture": f["path"],
            "reason": f["reason"],
            "ownedBy": prior["ownedBy"] if prior else UNASSIGNED,
            "detail": prior["detail"] if prior else (f.get("detail") or "").strip(),
        })
    entries.sort(key=lambda e: (e["fixture"], e["reason"]))
    payload = {
        "$comment": existing.get("$comment", ""),
        "specPin": results.get("specPin", ""),
        "entries": entries,
    }
    baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    fresh = [e for e in entries if e["ownedBy"] == UNASSIGNED]
    print("=" * 72)
    print("REGENERATED the baseline. This is a deliberate act and needs saying so")
    print("in the pull request: it rewrites the record of what is known to fail.")
    print(f"  entries written : {len(entries)}")
    print(f"  carried over    : {len(entries) - len(fresh)}")
    print(f"  NEW, unassigned : {len(fresh)}")
    for e in fresh:
        print(f"      {e['fixture']}  [{e['reason']}]")
    print("=" * 72)
    if fresh:
        print("Each new entry needs an ownedBy and a detail before the gate will pass.")
        return 1
    return 0


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", required=True, metavar="PATH",
                        help="JSON written by run_conformance.py --json")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE), metavar="PATH")
    parser.add_argument(
        "--regenerate", action="store_true",
        help="Rewrite the baseline from --results. Deliberate only; new entries land "
             "as ownedBy=UNASSIGNED and the gate refuses them until a human assigns one.",
    )
    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline)
    results_path = Path(args.results)

    results = load_json(results_path, "results file")
    baseline = load_json(baseline_path, "baseline")

    # Rule 0: keys must be spelled the one way. Checked before anything reads
    # them, --regenerate included, so a native-separator key can neither produce
    # a verdict nor be written into the shared baseline.
    refuse_native_separator_keys(results, baseline, baseline_path.name)

    if args.regenerate:
        return regenerate(baseline_path, results, baseline)

    # Rule 1: the baseline must be structurally usable.
    if "entries" not in baseline or not isinstance(baseline["entries"], list):
        abort(f"{baseline_path.name} declares no `entries` list. "
              "An unreadable baseline must never read as success.")

    # Rule 2: the run must be real. Mirrors the runner's own self-checks so a
    # degenerate report cannot be ratcheted into a green.
    counts = results.get("counts") or {}
    if counts.get("total", 0) <= 0:
        abort("results describe zero executed fixtures. Nothing to ratchet.")
    if results.get("constraintChecks", 0) <= 0:
        abort("results evaluated zero constraint checks across the whole suite. "
              "Every PASS in that report is vacuous, so no verdict from it means anything.")

    # Rule 3: baseline and run must describe the same vocabulary.
    #
    # First half: the run must not have been produced with --allow-spec-drift.
    # That flag validates against whatever shapes are on disk while the report
    # still records the pinned SHA, so a drifted run is not evidence about the
    # pinned vocabulary and must never be ratcheted against a baseline measured
    # for it.
    if results.get("specDrifted"):
        abort(
            f"this run used --allow-spec-drift: shapes came from "
            f"{results.get('specHead', '(unknown)')}, not the pinned "
            f"{results.get('specPin', '(unset)')}.\n"
            "  A drifted run says nothing about the pinned vocabulary, so it cannot be "
            "ratcheted. Re-run against the pinned checkout, or advance the pin deliberately."
        )
    pinned = baseline.get("specPin", "")
    actual = results.get("specPin", "")
    if pinned != actual:
        abort(
            f"baseline was measured against spec {pinned or '(unset)'} but this run used "
            f"{actual or '(unset)'}.\n"
            f"  Advancing scripts/SPEC_PIN changes which shapes run, so the known-failure set "
            f"must be re-measured.\n"
            f"  Fix: set \"specPin\": \"{actual}\" in {baseline_path.name} and reconcile the "
            f"entries in the same commit."
        )

    # Rule 4: no entry may be unowned.
    unassigned = [e for e in baseline["entries"] if e.get("ownedBy", UNASSIGNED) == UNASSIGNED]
    if unassigned:
        abort(
            f"{len(unassigned)} baseline entr{'y' if len(unassigned) == 1 else 'ies'} "
            f"still carry ownedBy={UNASSIGNED}:\n" +
            "\n".join(f"    {e.get('fixture')}  [{e.get('reason')}]" for e in unassigned) +
            "\n  A known failure with no named owner is a graveyard entry. Assign the repo "
            "that owns the fix."
        )

    # Rule 5: key on (fixture, reason).
    baselined = {key(e["fixture"], e["reason"]): e for e in baseline["entries"]}
    if len(baselined) != len(baseline["entries"]):
        abort(f"{baseline_path.name} contains duplicate (fixture, reason) entries.")

    observed = {
        key(f["path"], f["reason"]): f
        for f in results.get("fixtures", [])
        if f.get("outcome") != "pass"
    }

    new = sorted(observed.keys() - baselined.keys())
    gone = sorted(baselined.keys() - observed.keys())
    matched = sorted(baselined.keys() & observed.keys())

    # A fixture that changed which way it fails shows up in BOTH lists. Name it
    # as such, because "still failing" would be the wrong summary of it.
    changed = sorted(
        {n[0] for n in new} & {g[0] for g in gone}
    )

    # Internal consistency: every baseline entry was looked for exactly once.
    if len(matched) + len(gone) != len(baselined):
        abort("internal error: baseline entries were not all accounted for.")

    # --- report -----------------------------------------------------------
    print("Conformance ratchet")
    print("=" * 72)
    print(f"  spec pin              : {actual}")
    print(f"  fixtures executed     : {counts.get('total')}"
          f"  ({counts.get('passed')} passed / {counts.get('failed')} failed"
          f" / {counts.get('skipped')} skipped)")
    print(f"  constraint checks     : {results.get('constraintChecks')}")
    print(f"  baseline entries      : {len(baselined)}")
    print(f"  still failing as known: {len(matched)}")
    print(f"  NEW failures          : {len(new)}")
    print(f"  now passing           : {len(gone)}")
    print()

    if baselined:
        owners = Counter(e["ownedBy"] for e in baseline["entries"])
        print("Known failures by the repo that owns the fix")
        print("-" * 72)
        for owner, n in sorted(owners.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {n:3d}  {owner}")
        print()

    ok = True

    if new:
        ok = False
        print(f"REGRESSION: {len(new)} failure(s) are not in {baseline_path.name}")
        print("-" * 72)
        for k in new:
            entry = observed[k]
            print(f"  {render(k)}")
            if entry.get("detail"):
                print(f"      {entry['detail'][:160]}")
            for v in entry.get("violations", [])[:3]:
                print(f"      violated: {v[:150]}")
        print()
        print("  Fix the fixture or the vocabulary. Adding it to the baseline is only")
        print("  correct if the fix genuinely belongs to another repo, and then it needs")
        print("  an ownedBy and a detail saying so.")
        print()

    if gone:
        ok = False
        print(f"IMPROVEMENT NOT RECORDED: {len(gone)} baselined failure(s) now pass")
        print("-" * 72)
        for k in gone:
            entry = baselined[k]
            print(f"  {render(k)}   (owned by {entry['ownedBy']})")
            if entry.get("detail"):
                print(f"      was: {entry['detail'][:160]}")
        print()
        print(f"  Remove these entries from {baseline_path.name}. This is the ratchet")
        print("  working: the list is meant to shrink, and it only shrinks if letting it")
        print("  go stale is an error.")
        print()

    if changed:
        print(f"Note: {len(changed)} fixture(s) appear in both lists because they still")
        print("fail but for a DIFFERENT reason than recorded, which is a new fact:")
        for path in changed:
            was = next(k[1] for k in gone if k[0] == path)
            now = next(k[1] for k in new if k[0] == path)
            print(f"  {path}: {was} -> {now}")
        print()

    verdict = "RATCHET HELD" if ok else "RATCHET VIOLATED"
    print(f"Verdict: {verdict}  ({len(matched)} known / {len(new)} new / {len(gone)} now passing)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
