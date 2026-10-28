"""Recover visible station labels by PDF columns, preserving uncertain rows."""
from pathlib import Path
import subprocess,json,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;NS={'h':'http://www.w3.org/1999/xhtml'}
records=[];counts={}
for prefix,limit,country in [('',4,'SK'),('c',12,'CZ')]:
 for n in range(1,limit+1):
  name=f'{prefix}{n}';pdf=R.parent/'upload'/(name+'.pdf');xml=R/'research/pdf'/(name+'.xml')
  if not xml.exists():subprocess.run(['pdftotext','-bbox-layout',str(pdf),str(xml)],check=True)
  count=0
  for page_index,page in enumerate(ET.parse(xml).findall('.//h:page',NS),1):
   words=[dict(text=w.text or '',**{k:float(v) for k,v in w.attrib.items()}) for w in page.findall('.//h:word',NS)]
   stars=[w for w in words if w['text'].startswith('☆')]
   columns=[]
   for w in sorted(stars,key=lambda w:w['xMin']):
    if not columns or w['xMin']-columns[-1]>12:columns.append(w['xMin'])
   for star in sorted(stars,key=lambda w:(round(w['yMin']/10),w['xMin'])):
    c=min(range(len(columns)),key=lambda i:abs(columns[i]-star['xMin']));left=columns[c]-2;right=columns[c+1]-3 if c+1<len(columns) else float(page.get('width'))
    same=[w for w in stars if abs(w['xMin']-star['xMin'])<12 and w['yMin']>star['yMin']+6]
    bottom=min(star['yMin']+46,min((w['yMin']-10 for w in same),default=10000))
    first=[w for w in words if star['xMax']-1<=w['xMin']<right and abs(w['yMin']-star['yMin'])<13 and not w['text'].startswith('☆')]
    first.sort(key=lambda w:w['xMin'])
    if first:
     size=first[0]['yMax']-first[0]['yMin']
     selected=[w for w in words if left<=w['xMin']<right and star['yMin']-13<=w['yMin']<bottom and abs((w['yMax']-w['yMin'])-size)<1.8 and not w['text'].startswith('☆')]
     selected.sort(key=lambda w:(round(w['yMin']/5),w['xMin']));label=' '.join(w['text'] for w in selected)
    else:label=star['text'][1:].strip()
    records.append({'country':country,'source_pdf':pdf.name,'page':page_index,'name':label,'status':'extracted-visible-label-not-station-validation'});count+=1
  counts[pdf.name]=count
(R/'catalog/fmstream-pdf-labels.json').write_text(json.dumps({'schema':1,'counts':counts,'records':records,'note':'Printed labels can be clipped or covered by the website player. Duplicates/encodings are not separate validated stations.'},ensure_ascii=False,indent=2)+'\n')
print(counts);print('Labels',len(records),'blank',sum(not r['name'] for r in records));print(records[:5])
