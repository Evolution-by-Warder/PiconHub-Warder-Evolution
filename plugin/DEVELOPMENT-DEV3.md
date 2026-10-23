# PiconHub Warder Evolution 0.1.0-dev3

Packaging correction after the first OpenATV 8.0.1 receiver installation attempt.
The dev2 dependency solver rejected `python3-gettext`, which is not a separate
package in the receiver feed. OpenEmbedded provides gettext.py in python3-core.
Remove that invalid dependency and retain python3-core and the other dependencies.

The runtime and interface are unchanged from dev2. Both runtime version.txt and
project metadata now identify dev3. Package tests inspect the generated control
metadata to prevent reintroducing python3-gettext. All 54 local tests pass.

The dev2 install was blocked before installation. Successful installation and
GUI operation on the physical receiver remain to be verified with this build.
The stable update feed is unchanged.

Copy the dev3 IPK to /tmp and install its exact filename, so older IPKs in /tmp
are not selected again:

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev3_all.ipk
```

After a successful installation, restart the GUI using the receiver menu.
