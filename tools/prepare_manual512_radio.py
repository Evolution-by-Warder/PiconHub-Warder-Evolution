"""Build exact review inputs from a frozen producer state and explicit SHA/reference selection."""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True);p.add_argument('--templates',type=Path,required=True);p.add_argument('--renderer',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
state=json.load(open(a.root/'discovery-state.json'))['stations'];selection=json.load(open(a.selection));review=json.load(open(a.decisions));assert review['reviewed_through']+1==len(selection['sources']);rows=[];decisions=[];sources=[]
for i,chosen in enumerate(selection['sources']):
 reason=review['exceptions'].get(str(i));decision='needs_replacement' if reason else 'approve';reason=reason or 'Whole broadcaster logo visually reviewed against exact station identity and current saved page; original colors and proportions retained.'
 sources.append(dict(sha256=chosen['sha256'],decision=decision,reason=reason,review='next_radio_visual_20261105',source_index=i,references=chosen['references']))
 for ref in chosen['references']:
  row=dict(state[ref]);assert row['source']['sha256']==chosen['sha256'];assert row.get('page')
  row.pop('renders',None);row.pop('verification',None);rows.append(row);decisions.append(dict(reference=ref,sha256=chosen['sha256'],decision=decision,reason=reason,review='next_radio_visual_20261105',source_index=i))
for name,value in [('assistant-review-input.json',rows),('assistant-review-decisions.json',decisions),('assistant-source-decisions.json',sources)]:
 (a.root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
if not a.prepare_only:subprocess.run([sys.executable,str(a.renderer),'--root',str(a.root),'--templates',str(a.templates)],check=True)
