# WARDER PICON FACTORY

Unified Windows desktop application for source ingestion, identity matching, PNG processing, QA, manual review, and local finalization.

## Authoritative Windows workspace

The only production data root is `D:\WARDER-PICON-FACTORY`. The application and installer use these exact categories:

| Folder | Purpose |
| --- | --- |
| `00-STATE` | Checkpoints and run history |
| `01-SOURCES` | Source inputs, manifests, downloaded archives, and ingest metadata |
| `02-ORIGINALS` | Immutable original PNG files from local and remote sources |
| `03-REGISTRY` | Warder Master snapshots and mappings |
| `04-WORK` | Rendered working images |
| `05-QA` | QA exceptions and manual decisions |
| `06-OUTPUT` | Locally finalized results |
| `07-PUBLISH-STAGING` | Draft publication preparation only |
| `08-REPORTS` | Reports and statistics |
| `09-LOGS` | Installer, runtime, and diagnostic logs |
| `10-TOOLS` | Service tools |
| `11-APP` | Engine, GUI, dependencies, updater, and app data |
| `12-ARCHIVE` | Historical data |

At startup, a read-only preflight inventories all 13 folders. It enables writes only when all are present and readable. A missing D: drive, missing category, unreadable directory, or unsafe reparse-point stops writes. The application does not create missing top-level folders, migrate data, or use another data root. The preflight does not modify existing files.

The source tree contains a developer launcher. The one-file Windows CMD installs the executable under `11-APP\WARDER-PICON-FACTORY`; diagnostics go to `09-LOGS`. Updates preserve earlier app versions for manual recovery. The CMD is built after Windows tests and a native GUI smoke test and is uploaded as an Actions artifact, not published as a GitHub Release.

## Data flow and safety

- Vhannibal, OpenATV 8, Chocholousek, and local ZIP inputs are archived under `01-SOURCES`; source checkpoints remain in `00-STATE`.
- Original PNG files from local and remote sources are stored additively under `02-ORIGINALS`; the renderer writes 220 × 132 RGBA transparent, black, and white variants under `04-WORK`.
- Read-only Master snapshots are stored additively under `03-REGISTRY\MASTER-SNAPSHOTS`; checkpoints are in `00-STATE`.
- Review queues, conflicts, and manual decisions remain in `05-QA\EXCEPTIONS` and `05-QA\review-decisions.json`. Existing queue files under `08-REPORTS` remain readable as a legacy fallback and are never migrated or deleted. Only eligible NEW candidates pass local QA finalization to `06-OUTPUT`; existing targets are never overwritten.
- Reports are stored under `08-REPORTS`; logs are stored under `09-LOGS`. The ChatGPT export is the separate file `D:\WARDER-PICONS-PENDING.zip` and is not a workspace root.
- No automatic production publication is performed.

## GUI

The GUI provides Dashboard, Sources, Master Registry, Candidates, Graphics Engine, QA, Exceptions, Finalization, Settings, and Diagnostics. Settings displays the live, read-only 13-folder inventory and preflight result. The dashboard shows counts from the selected workspace; source inventory counting runs off the Tk event thread. Exceptions are reviewed in pages of ten with available image previews. The Windows UI uses Segoe UI, DPI-aware scaling, resizable tables, and horizontal/vertical scrolling.

## Verification status

Local and CI tests use synthetic workspaces, never user files. They verify the exact 13-folder mapping, read-only preflight, file hashes before and after inventory, import through render/QA/review/finalization, existing-file protection, and repeat-run behavior. This development environment cannot inspect the user's D: drive; only the app's on-device preflight can inventory it.

## Trvalé Git rozhodnutia a pokračovanie práce

factory/registry/warder-identity-registry.json a
factory/registry/master-approval-ledger.json sú autoritatívne na
factory-warder-development. GUI review už neukladá konečné rozhodnutie iba do
lokálneho review-decisions.json: každé potvrdenie sa pripraví ako PENDING dávka
a uloží do jedného Git commitu po validácii, kontrole aktuálneho HEAD a
read-after-write overení.

APPROVED_FOR_REVIEW je auditný výsledok review, nie automatické schválenie
Master identity ani artworku. Tlačidlo „Potvrdiť identitu + Warder ID“ vytvorí
jedno nové sekvenčné ID iba po potvrdení povinných polí používateľom a v rovnakej
transakcii uloží Registry, approval event aj review event. Tlačidlo pre artwork
vyžaduje existujúce Warder ID, jeden presný review item, všetky tri PNG varianty
a ich validáciu; nahratie artworku do Git je súčasťou toho istého commitu.
Existujúci schválený artwork sa týmto tokom neprepisuje; rebranding zostáva
blokovaný bez osobitného evidenčného toku.

Pri nedostupnom tokene, sieti alebo konfliktnom HEAD dávka ostáva
PENDING/UNSAVED v lokálnom staging súbore pending-master-review-batches.json;
GUI ju nikdy neoznačí ako uloženú. Retry PENDING opakuje iba pripravené
rozhodnutia, bez nového skenovania. Opakovaný submit s rovnakým review ID a
dôkazom je idempotentný.

factory/registry/project-progress.json je odvodený checkpoint ledgeru a
Registry. Počet remaining je zámerne null, kým celý aktívny review queue nie
je trvalo exportovaný do Gitu; používateľské dáta a PNG sa do diagnostiky ani
do tohto súboru nepridávajú. Aktuálny commit obsahujúci checkpoint sa vždy
určí z Git HEAD; last_commit v JSON je overený parent batch transakcie.

Po čistej inštalácii Factory načíta review eventy a Registry z aktuálneho Git
HEAD. Offline režim zobrazí stav ako neoverený; nič lokálne neprezentuje ako
trvalo schválené. Vývojové zápisy vyžadujú samostatný GitHub write token s
oprávnením na tento repozitár. Produkčná vetva sa nikdy nezapisuje.


## Git Master diagnostic and no-render recovery (v0.2.53)

The Git Contents API may return a valid base64 body with line-wrap whitespace.
The reader strips only ASCII whitespace and then performs strict base64 validation;
it never switches to permissive decoding. Network/HTTP/API response errors remain
visible in the review GUI, and an unavailable or invalid snapshot remains
fail-closed.

When a previous run has produced a valid local review queue, **Prepočítať
MASTER-first bez renderu** fetches a commit-pinned Git Master and reclassifies
that saved queue. It does not scan sources, open PNGs, rerender, rewrite QA, or
approve identities. It writes a new queue and coverage report; previous queue
and audit files remain untouched. Only exact Git identity/artwork approvals
whose hashes match the current Master can cover artwork items.

The first PC run on 2026-10-14 was reported as 162,427 PNG / 306.57 seconds,
preflight 13/13, and 9,932 pending decisions (4,054 identity, 5,877 artwork,
one technical QA). The report bytes were not present in the development branch
at recovery time, so those counts are owner-reported and not independently
recomputed here. The reported transparent `ilsole24ore tv` technical QA item
is explicitly preserved for separate investigation; a Master refresh cannot
dismiss it. No registry, ledger, approval, Warder ID, source PNG, or production
branch is altered by this recovery.


## v0.2.54 — snapshot integrity, saved-queue recovery, and workflow states

Git Master reads and cache validation now share the same canonical JSON SHA-256
calculation (snapshot schema 3 invalidates the incompatible v0.2.53 cache). The Git commit pins the exact repository bytes; the snapshot
content digest is computed over parsed canonical JSON so key order and GitHub
Contents API formatting cannot create a false integrity failure. Snapshot
validation reports field-specific digest or Registry/ledger issue codes. The
GUI uses this same validated fetch path as the engine and remains fail-closed.

At successful workspace preflight, a valid saved review queue is restored and
refreshed against one commit-pinned Git snapshot. This avoids rerunning the
full source scan/render when a queue already exists. A first run or an absent
or invalid queue still starts normal processing. A refresh writes a new queue
and coverage report without PNG access; previous reports are preserved. The
GUI keeps the refresh result visible and reports source count → active count,
exactly covered tasks, Git commit, elapsed time, and BEZ RENDERU. An unchanged
queue explains that no exact service-reference plus approved artwork hash
evidence matched.

Each refreshed task receives a separate evidence-bound workflow status map:
AUTO_RESOLVED_VERIFIED, READY_FOR_HUMAN_APPROVAL, AMBIGUOUS, CONFLICT,
TECHNICAL_QA, BLOCKED_MISSING_EVIDENCE, or COMPLETED_GIT_CONFIRMED. This
derived map is separate from evidence-hashed review items. No uncertain identity
is approved automatically. The previously reported ilsole24ore tv transparent
FULLY_TRANSPARENT / OUTPUT_CHANGED_DURING_QA finding remains in Technical QA.

The 2026-10-14 PC task totals remain owner-reported until the PC-generated
review report is available for independent replay. Current committed Git
Registry and approval ledger are still empty, so no prior picon approval can
be inferred from their presence. The new refresh report will measure actual
coverage and decision groups on the user's saved queue.
