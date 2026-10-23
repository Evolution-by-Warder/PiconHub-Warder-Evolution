# PiconHub Warder Evolution — current work plan

Updated: 2026-10-23 after the owner's explicit direction to use Chocholousek as the functional base.

1. Completed: primary verified skin and picon backup in private Trezor, backup-20261023-verified. The extra Library copy timed out and remains unconfirmed.
2. Completed: initial Warder catalog and integrity adapter; nine tests and CI passed.
3. Completed: static review of the real upstream Chocholousek 5.0.240904 code. The historical migration workspace contains a skeleton and must not be described as the complete runtime.
4. Current proposal: modern profile/settings panel with preview, satellite picker, directory picker and structured update screen. See ../plugin/design/CHOCHOL-WARDER-INTERFACE.md.
5. Next: import the exact original source with attribution and retained configuration/runtime path; connect the modern interface to its functions.
6. Then: improve error propagation and job events, integrate Warder catalog/ZIP as a separate source adapter and package a test IPK.
7. Verify OpenATV receiver behavior separately from static/code/package checks.

The earlier from-scratch runtime plan is superseded. Preserve genuine recovered headers, old branches, Factory code, production data, MASTERs and existing IPKs. The UI proposal is not implemented or receiver-tested yet.

## Implementation checkpoint — 2026-10-23

- Imported the original upstream runtime and support assets into the new development branch, retaining author and technical path.
- Connected an asynchronous check for newer Warder plugin releases on each main-screen launch. No daily scheduler, standby installer or picon auto-update was added; the owner's clarified requirement is per-launch checking of the plugin itself.
- Added verified IPK staging and a user-confirmed install route. Stable feed currently offers no release.
- Next: implement the agreed modern screen and OK-opened picker dialogs, using the same eligible choices as the skin, then packaging and physical OpenATV checks.

## Development 0.1.0-dev2

Implemented the agreed native interface, OK-opened pickers, same skin choices, live receiver clock/version and Warder ZIP adapter over preserved Chocholousek profiles. Built a development IPK and added package/artifact CI. Next required evidence is a real OpenATV receiver test; stable feed remains empty. Full details are in ../plugin/DEVELOPMENT-DEV2.md.
