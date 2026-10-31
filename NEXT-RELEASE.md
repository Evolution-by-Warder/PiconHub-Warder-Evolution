# Current receiver repair status — 31 October 2026

The recorded functional repairs and four-entry History presentation are included in the verified 0.1.35 repair package. See the receiver-repair documentation and public verification report. Published repair IPKs are immutable; stable update feeds remain unchanged. A final physical receiver retest of this package is pending.

The following entries are preserved as historical investigation and approval records; their earlier IPK holds do not override the owner's later instruction to combine and repair the recorded issues.

---

# Next release — History presentation

Status: required with the next functional fix or enhancement; no standalone IPK for this task.
Requested by the repository owner on 31 October 2026.

- Show only the latest 4 history entries in the plugin UI.
- Give every entry a clear version/date heading and a visible separator.
- Keep each description brief (at most 3 properly wrapped display lines), so the list fits cleanly on screen.
- Follow the active environment language for UI labels.
- Show only general user-facing changes; omit internal filenames, paths, implementation details, diagnostic/testing notes and working conversations.
- Preserve the full historical source and Git history; the limit applies only to the UI view.
- Preserve installer/result output and its existing actions; do not apply the 4-entry history limit to operational results.

Include this work when the plugin next changes. Check the history screen with long descriptions, language variants and the newest four entries before publishing that release.

## Final verification of plugin installation

Prepared source on `fix/install-transition-20261031`: validate critical runtime files and exact installed version during postinst, then require native package identity, version and fully installed status after opkg exits. Keep the normal opkg install command; a missing force flag has not been established as the cause of the user's first-attempt failure. Minimal real-opkg transition from the original 5.0.240904 passed with and without force flags. No physical-receiver first-failure root cause is claimed. See `reports/install-transition-review-20261031.json`.

This source is pending a future authorized functional release. Keep the already recorded four-entry, general-description History requirement for that release. No public IPK, version, feed or picon data was changed by this investigation.

Prepared source commit: `487e46aef74323cb81ce7af554a90dd74cf36468`. Related skin source: `680bab699ff934b92b891a771ed465ce8d71e53c`; related PiconHub source: `487e46aef74323cb81ce7af554a90dd74cf36468`.
