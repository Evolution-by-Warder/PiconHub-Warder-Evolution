"""Source selection rules. No guessed provider endpoints or implicit priority."""
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class PiconSource:
    key: str
    role: str = 'peer'
    enabled: bool = True
    endpoint: str | None = None

SOURCES = (
    PiconSource('vhannibal'),
    PiconSource('openatv8'),
    PiconSource('chocholousek'),
)

class SourcePolicyError(ValueError):
    pass

def validate_sources(sources: Iterable[PiconSource]):
    sources = tuple(sources)
    keys = [s.key for s in sources]
    if len(keys) != len(set(keys)):
        raise SourcePolicyError('Duplicate source')
    if not {'vhannibal', 'openatv8'}.issubset(keys):
        raise SourcePolicyError('Missing primary peer source')
    for s in sources:
        if s.role != 'peer':
            raise SourcePolicyError('Input sources must not have priority')
        if s.endpoint is not None and not s.endpoint.startswith('https://'):
            raise SourcePolicyError('Only verified HTTPS endpoints are allowed')
    return sources

def plan_updates(sources, current_fingerprints, previous_fingerprints):
    """A stale source remains enabled; unchanged content needs no processing."""
    sources = validate_sources(sources)
    results = {}
    for source in sources:
        if not source.enabled:
            results[source.key] = 'disabled'
        elif source.key not in current_fingerprints:
            results[source.key] = 'unavailable'
        elif current_fingerprints[source.key] == previous_fingerprints.get(source.key):
            results[source.key] = 'unchanged'
        else:
            results[source.key] = 'process'
    return results

def choose_identity_candidates(candidates):
    """Never choose one peer source over another for conflicting art."""
    by_identity = {}
    for candidate in candidates:
        by_identity.setdefault(candidate['identity'], []).append(candidate)
    accepted, review = {}, {}
    for identity, entries in by_identity.items():
        hashes = {entry['sha256'] for entry in entries}
        if len(hashes) == 1:
            accepted[identity] = entries[0]
        else:
            review[identity] = entries
    return accepted, review
