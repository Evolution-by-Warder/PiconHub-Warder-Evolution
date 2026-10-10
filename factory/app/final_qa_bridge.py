"""Fail-closed bridge from review evidence to local finalization.

Only engine-issued, pinned and verified evidence may enable final QA. Never infer
approval from an OK / Beriem review click or a filename alone.
"""
from pathlib import Path
import re
import hashlib

class FinalizationNotReady(ValueError):
    pass


def prepare_finalization(output_dir, item):
    evidence = item.get('final_qa_evidence')
    if not isinstance(evidence, dict):
        raise FinalizationNotReady('Chýba finálne QA potvrdenie z motora')
    if evidence.get('status') != 'FINAL_QA_APPROVED':
        raise FinalizationNotReady('Finálna QA nie je schválená')
    if evidence.get('identity_verified') is not True or evidence.get('plastic_templates_verified') is not True:
        raise FinalizationNotReady('Identita alebo plastické šablóny nie sú overené')
    if evidence.get('review_id') != item.get('review_id'):
        raise FinalizationNotReady('QA dôkaz patrí inej položke')
    root = Path(output_dir).resolve()
    if root.name.upper() != 'PICONS' or root.parent.name != '04-WORK':
        raise FinalizationNotReady('Galéria nie je napojená na kanonické pracovné úložisko')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', str(evidence.get('identity', ''))):
        raise FinalizationNotReady('Neplatná identita')
    hashes = evidence.get('sha256')
    if not isinstance(hashes, dict) or set(hashes) != {'black', 'white'}:
        raise FinalizationNotReady('Chýbajú oba overené SHA-256')
    for v in ('black', 'white'):
        if not isinstance(hashes[v], str) or not re.fullmatch('[0-9a-f]{64}', hashes[v]):
            raise FinalizationNotReady('Neplatný SHA-256')
    source_sha = evidence.get('source_sha256')
    if not isinstance(source_sha, str) or not re.fullmatch('[0-9a-f]{64}', source_sha):
        raise FinalizationNotReady('Chýba overený odtlačok zdrojového PNG')
    variants = {v: root / source_sha[:2] / source_sha / (v + '.png') for v in ('black', 'white')}
    for variant, path in variants.items():
        if not path.is_file():
            raise FinalizationNotReady('Pracovné PNG chýbajú: ' + variant)
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != hashes[variant]:
            raise FinalizationNotReady('Pracovné PNG bolo zmenené po QA: ' + variant)
    return dict(root=root.parent.parent, identity=evidence['identity'], variants=variants,
                approval='FINAL_QA_APPROVED', expected_sha256=hashes)
