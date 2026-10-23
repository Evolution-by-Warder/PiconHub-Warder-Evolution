# PiconHub Warder Evolution 0.1.0

First numbered trial release distributed through the plugin's existing startup
updater. Keep the original feed URL on plugin/futuristic-rebuild so installed
dev2–dev8 builds can discover it without another manual IPK bootstrap.

CI tests and builds the IPK, uploads an immutable GitHub Release with its checksum,
verifies the public package bytes and only then advances plugin/update/stable.json.
The publishing commit is fast-forward only. Existing versions cannot be replaced
with different bytes or advertised as a downgrade. Development versions do not
publish. Future numbered version bumps follow the same automatic workflow.

The release is marked as a GitHub prerelease, and does not become the repository's
global latest release used by the separate Factory application. The compatible
manifest uses the numbered stable-format channel required by installed updaters;
this is not a claim that physical receiver validation is finished.

At every new opening, the existing background check offers a newer plugin version.
After the user accepts, the updater verifies size, SHA256 and IPK identity before
opkg installation. A failed installation never triggers a GUI restart.

After a successful update, show an informational window for three seconds, then
restart the GUI automatically (TryQuitMainloop mode 3). No second confirmation is
required. While that notice is visible, remote input cannot dismiss it early.
Closed-screen callbacks do not restart the GUI.

Bootstrap limitation: the update from dev8 into 0.1.0 still finishes in dev8's
already-loaded installer and asks its original restart question once. Updates
started by 0.1.0 and newer use the automatic three-second notice and restart.

76 local tests pass, including publication order, immutable bytes, public-download
failure, old-dev8 manifest compatibility, idempotent publishing, strict ref updates,
three-second success notice, restart mode and no restart on failure. On-device
installation and subsequent GUI restart still require receiver confirmation.
