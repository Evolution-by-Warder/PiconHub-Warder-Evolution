# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import ssl
import tempfile
import time

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError

from ..constants import DEFAULT_RETRIES, DEFAULT_TIMEOUT, USER_AGENT
from .errors import IntegrityError, NetworkError


def _request(url, headers=None):
    all_headers = {'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'}
    if headers:
        all_headers.update(headers)
    return Request(url, headers=all_headers)


def open_url(url, timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES, headers=None):
    last = None
    context = ssl.create_default_context()
    for attempt in range(max(0, retries) + 1):
        try:
            req = _request(url, headers=headers)
            try:
                return urlopen(req, timeout=timeout, context=context)
            except TypeError:
                return urlopen(req, timeout=timeout)
        except (HTTPError, URLError, OSError, IOError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(min(2.0, 0.35 * (2 ** attempt)))
    raise NetworkError('Unable to fetch %s: %s' % (url, last))


def fetch_json(url, timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES):
    handle = open_url(url, timeout=timeout, retries=retries)
    try:
        raw = handle.read()
    finally:
        try:
            handle.close()
        except Exception:
            pass
    if not isinstance(raw, str):
        raw = raw.decode('utf-8')
    try:
        return json.loads(raw)
    except Exception as exc:
        raise NetworkError('Invalid JSON from %s: %s' % (url, exc))


def _fsync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass


def download_atomic(url, target, expected_size=None, expected_git_sha=None,
                    timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES,
                    chunk_size=256 * 1024):
    directory = os.path.dirname(target) or '.'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    fd, temp_path = tempfile.mkstemp(prefix='.piconhub-', suffix='.part', dir=directory)
    os.close(fd)
    size = 0
    try:
        handle = open_url(url, timeout=timeout, retries=retries,
                          headers={'Accept': 'application/octet-stream'})
        try:
            with open(temp_path, 'wb') as out:
                while True:
                    chunk = handle.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    size += len(chunk)
                out.flush()
                try:
                    os.fsync(out.fileno())
                except Exception:
                    pass
        finally:
            try:
                handle.close()
            except Exception:
                pass

        if expected_size is not None and int(expected_size) != size:
            raise IntegrityError('Size mismatch for %s: expected %s, got %s' % (
                target, expected_size, size))

        if expected_git_sha:
            from .scanner import git_blob_sha1
            actual = git_blob_sha1(temp_path)
            if actual.lower() != str(expected_git_sha).lower():
                raise IntegrityError('SHA mismatch for %s' % target)

        try:
            os.replace(temp_path, target)
        except AttributeError:
            if os.path.exists(target):
                os.remove(target)
            os.rename(temp_path, target)
        _fsync_dir(directory)
        return size
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise
