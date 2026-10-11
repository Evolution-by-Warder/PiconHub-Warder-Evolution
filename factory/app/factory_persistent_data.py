"""Legacy migration entrypoint intentionally disabled.

Factory data are already organized by the 13-category workspace. Copying data
from older layouts is an explicit operator task and is never done by the app.
"""


def migrate(*_args, **_kwargs):
    raise RuntimeError("Automatic Factory data migration is disabled; existing files were left untouched.")
