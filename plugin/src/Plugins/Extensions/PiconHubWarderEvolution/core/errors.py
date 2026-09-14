# -*- coding: utf-8 -*-

class PiconHubError(Exception):
    pass


class NetworkError(PiconHubError):
    pass


class CatalogError(PiconHubError):
    pass


class IntegrityError(PiconHubError):
    pass


class UnsafePathError(PiconHubError):
    pass
