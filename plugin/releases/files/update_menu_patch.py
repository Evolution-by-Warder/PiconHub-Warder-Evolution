# -*- coding: utf-8 -*-
from __future__ import print_function

from . import plugin as p
from .update_ui import PiconHubUpdateChoice


def _open_update_choice(self):
    self.session.open(PiconHubUpdateChoice)


# Routing only. All updater visuals live in update_ui.py.
p.PiconHubMain.quickUpdate = _open_update_choice
p.PiconHubUpdateMenu = PiconHubUpdateChoice
