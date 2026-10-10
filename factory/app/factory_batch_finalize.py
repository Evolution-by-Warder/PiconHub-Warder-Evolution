"""Local evidence-gated batch publication; never manufactures QA approval."""
import argparse
import json
from pathlib import Path
from final_qa_bridge import prepare_finalization, FinalizationNotReady
from finalize_picons import finalize_triplet


def run_batch(root, evidence_file, *, commit=False):
    root = Path(root).resolve()
    work = root / '04-WORK' / 'PICONS'
    final = root / '06-OUTPUT' / 'PICONS'
    payload = json.loads(Path(evidence_file).read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
        raise ValueError('Invalid QA evidence document')
    report = {'mode': 'publish' if commit else 'dry-run', 'total': len(payload['items']),
              'eligible': 0, 'published': 0, 'blocked': 0, 'items': []}
    seen = set()
    for item in payload['items']:
        ident = item.get('review_id') if isinstance(item, dict) else None
        try:
            if not isinstance(item, dict) or not isinstance(ident, str) or not ident or ident in seen:
                raise FinalizationNotReady('Invalid or duplicate review ID')
            seen.add(ident)
            request = prepare_finalization(work, item)
            report['eligible'] += 1
            if commit:
                result = finalize_triplet(**request)
                report['published'] += 1
                report['items'].append({'review_id': ident, 'status': 'PUBLISHED', 'paths': result})
            else:
                report['items'].append({'review_id': ident, 'status': 'READY'})
        except (FinalizationNotReady, ValueError, PermissionError, FileNotFoundError, FileExistsError, OSError) as exc:
            report['blocked'] += 1
            report['items'].append({'review_id': ident, 'status': 'BLOCKED', 'reason': str(exc)})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--commit', action='store_true', help='Publish only pinned and verified QA-approved assets')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    result = run_batch(args.root, args.evidence, commit=args.commit)
    dest = Path(args.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"QA batch: eligible={result['eligible']} published={result['published']} blocked={result['blocked']}; report={dest}")

if __name__ == '__main__':
    main()
