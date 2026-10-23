# PiconHub Warder Evolution

Development version: **0.1.0-dev2**. Native modern interface and Warder picon adapter are implemented; physical receiver validation is pending. See [DEVELOPMENT-DEV2.md](DEVELOPMENT-DEV2.md) for behavior, provenance and test limits.

The functional base is Chocholousek Picons 5.0.240904 by s3n0. Original configuration keys and runtime directory are retained. Main opens WarderMainScreen; each row opens a picker with OK. The menu follows the skin, with three backgrounds and three resolutions. Profiles remain distinct. Date, clock and installed version are live widgets.

The per-launch updater checks Warder plugin releases in the background and offers installation only when a newer published package exists. The development feed still offers no stable release. Picons are updated only when explicitly started by the user.

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build
```

The package is a development artifact for testing, not a receiver-verified stable release. The original recovery headers, historical branches, production picons, skin sources and protected MASTER data are unchanged.
