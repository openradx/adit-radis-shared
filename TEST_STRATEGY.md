# Testing Plan — ADIT, RADIS & the shared library

What we test, where it's weak, and what to add — with the analysis behind it.

## Where we stand

**ADIT (DICOM transfer).** The core is well tested: the permission model, transfer retry/lifecycle,
and pseudonym generation, plus a large browser-test layer that needs the full Docker/Orthanc stack.
The gaps are in the layers that face the outside world — web views and the DICOMweb API are tested
mostly for "the page loads," nothing checks that the API blocks a user without access, and the code
that strips patient identifiers from each image is never tested directly.

**RADIS (report archive + LLM).** Uneven. The newest piece — report labelling — is well tested. But
the central `reports` app and the `chats` app have essentially no tests, the search engine itself is
untested, and the LLM tests use a fake that returns a fixed answer regardless of input — so they
prove the wiring runs, not that the labels are correct.

**The shared library** both build on has ~8 tests total — including the API token/login code, which
is exercised only through a browser click-through. A bug there breaks both products at once.

Across all three: the build measures coverage but never fails when it drops, and there's no security
or dependency-vulnerability scanning — which matters for software handling patient data.

## Coverage at a glance

| Project | Well covered | Thin or missing | Biggest risk |
|---|---|---|---|
| **ADIT** | core models & permissions, transfer retry/lifecycle, pseudonym generation, Orthanc E2E | view *behaviour* (mostly smoke), DICOMweb API authorization, the per-image de-identification engine | patient identifiers leaking on transfer; API access not enforced |
| **RADIS** | report labelling (newest), search query parser, job/task state machine | `reports` app (none), `chats` (none), the search engine, real LLM behaviour | wrong/lost reports; mislabelled data; broken search going unnoticed |
| **shared** | — (~8 tests total) | token/login auth (browser-only), the base job/task framework | one bug breaks **both** products at once |

## The kinds of tests we need — and where each stands

The foundation behind the priorities below: a good suite spreads across these levels. This is where
the three projects sit today.

| Kind of test | What it catches | ADIT | RADIS | Shared |
|---|---|---|---|---|
| **Unit** | logic errors in one function | strong (core) | patchy | minimal |
| **Integration** (DB/services) | wrong DB behaviour, bad wiring | good | good where present | minimal |
| **Web / view behaviour** | broken pages, wrong data saved, missing access checks | mostly smoke | mixed | n/a |
| **API contract** | API ↔ client drift, bad responses | DICOMweb authz missing | reports API untested | token-auth browser-only |
| **Async / WebSocket** | broken live updates, async bugs | mislabelled / absent | none | fixtures only |
| **Security** (access · input · deps) | data leaks, injection, vulnerable deps | API authz gap | raw-query surface | — |
| **Data integrity** (PHI · DB) | identifier leaks, corruption, lost rows | de-id untested | upsert/dedup untested | — |
| **Acceptance / E2E** | whole user journeys break | heavy (needs Orthanc) | homepage only | login only |
| **Reliability / concurrency** | crashes, double-processing | retry ok; crash & lock not | none | — |
| **Performance guards** | slow queries, N+1 | none | none | — |
| **LLM correctness** | wrong labels/answers | n/a | fake-only → real eval deferred | — |

Two we deliberately skip for now: **load/stress** (until scale is real) and **accessibility**
(internal radiology tool).

## What to add, in order

**1. First — things that can cause real harm**
- ADIT: prove patient identifiers are actually removed on transfer (fill an image with every
  identifying field, run the transfer, check they're gone). Test that the DICOMweb API rejects users
  without access.
- RADIS: test the `reports` save / update / de-duplicate path (the heart of the system) and the
  search engine (insert a report, confirm a search finds it). Test that hostile search input can't
  crash the query or break out of it.
- RADIS: real tests for the LLM wiring — the report text reaches the prompt, answers map to the right
  labels, confidence stays in range — using a fake we actually control.
- Shared: test the token/login code directly, not just through a browser.

**2. Next — fill the everyday gaps**
- Replace "the page loads" tests with ones that check the right thing happened (data saved, wrong
  user blocked).
- ADIT: the live-transfer WebSocket, the file receiver, the Excel-upload parser.
- RADIS: the subscription and extraction background jobs, the chat views, the report export.
- Cover the async code in both projects (none of it is tested directly today).

**3. Then — robustness and tidy-up**
- Throw malformed / oversized input at the parsers and search; confirm they fail gracefully.
- A few real end-to-end journeys for RADIS (search → result, labelling).
- Confirm a worker that crashes mid-job resumes correctly, and that two workers don't double-process.
- Make the suite faster and flake-free, and have the build fail when coverage drops or a known
  vulnerability appears.

**4. Later — needs a decision or data from you**
- **LLM quality check:** a small set of real reports with known-correct labels, run against the
  actual model to catch quality drift over time. Needs that labelled set from your team.
- **Audit trail:** neither app records who accessed or transferred which patient data. If that's a
  compliance requirement, it needs building first, then testing.

## What makes these tests worth having

Three things we hold to, so the suite catches *future* bugs instead of just turning red when someone
edits code:
- **Test what the code does (its result), not how it does it** — so tests survive refactoring.
- **Check real outcomes, not just "no error"** — a test that only checks a page loads won't catch a
  broken feature.
- **Keep tests fast and reliable** — a slow or flaky suite stops getting run.
