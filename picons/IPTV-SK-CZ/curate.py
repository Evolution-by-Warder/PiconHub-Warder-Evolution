from pathlib import Path
from urllib.parse import urljoin
import json,re,unicodedata
R=Path(__file__).resolve().parent
rows=json.loads((R/'catalog/stations.json').read_text())['stations'];pages=json.loads((R/'research/pages.json').read_text());radia=json.loads((R/'research/radia-stations.json').read_text());byname={}
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.casefold()).encode('ascii','ignore').decode())
for r in radia:byname[norm(r['name'])]=r
explicit={
 'Cesky rozhlas 1 - Radiozurnal':'cesky-rozhlas-radiozurnal','Cesky rozhlas 2 - Praha':'cesky-rozhlas-dvojka','Cesky rozhlas 3 - Vltava':'cesky-rozhlas-vltava','Cesky rozhlas 7 - Radio Prague International':'radio-prague-international','CRo Wave':'cesky-rozhlas-radio-wave','CRo Plus':'cesky-rozhlas-plus','CRo Region':'cesky-rozhlas-region','CRo Vltava (FLAC)':'cesky-rozhlas-vltava','CRo D-dur (FLAC)':'cesky-rozhlas-d-dur','CRo Jazz (FLAC)':'cesky-rozhlas-jazz','CRo Radio Wave (FLAC)':'cesky-rozhlas-radio-wave','CRo Dvojka (Vorbis)':'cesky-rozhlas-dvojka','CRo Rádio Junior (Vorbis)':'cesky-rozhlas-radio-junior','CRo Radiožurnál Sport':'radiozurnal-sport','Hitradio City Osmdesatka':'hitradio-80tka','Hitradio City Devadesatka':'hitradio-90tka','Hitradio City milenium':'hitradio-milenium','Hitradio City Zona lasky':'hitradio-zona-lasky','Fajn Radio Fresh':'fajn-radio-fresh','Radio Country':'country-radio','Radio Epigon':'webradio-epigon','Spin Radio':'radio-spin-962-fm','Radio Roma':'roma-radio'}
source={};slugs={x['slug']:x for x in radia}
for st in rows:
 record=slugs.get(explicit.get(st['name'])) or (byname.get(norm(st['name'])) if st['country']=='CZ' else None)
 if record:source[st['name']]={'source_page':'https://radia.cz/radia/'+record['slug'],'url':record['logo'],'identity':record['name'],'evidence':'Station-specific named logo from the publisher catalogue; explicit aliases retained.'}
# Explicitly selected station logos observed on their own homepages.
choices={
 'Radio Aetter':('http://www.aetter.sk/','logo_magenta.svg'), 'BB FM radio':('https://www.bbfm.sk/','logo_bbfm_white_BBBR.svg'),
 'Radio Beta':('https://beta.sk/','beta-radio-logo.png'),'Europa 2':('https://www.europa2.sk/','/assets/logo.svg'),'Radio Expres':('https://www.expres.sk/','logo_re.svg'),
 'Fun Radio':('http://www.funradio.sk/','funradio-logo.svg'),'Fun Radio 80 - 90 roky':('http://www.funradio.sk/','/stanice/8090.svg'),'Fun Radio CZ-SK':('http://www.funradio.sk/','/stanice/cs.svg'),'Fun Radio - Dance':('http://www.funradio.sk/','/stanice/dance.svg'),
 'G-Radio':('http://gradio.sk/','images/logo.gif'),'Radio Frontinus':('http://frontinus.sk/','frontinus_logo_transparent_1.png'),'Radio Logos':('http://www.radiologos.sk/','/images/logo-sm.png'),
 'Radio Parada - Vyšny Hrusov':('https://www.radioparada.sk/','radio_parada_logo_2022-01-e1656439980629.png'),'Radio Melody':('https://www.radiomelody.sk/','/assets/logo.svg'),'Radio Lumen':('http://www.lumen.sk/','/logo/lumen.png'),
 'Rusyn FM':('https://www.rusyn.fm/play/','rusynFM_logo-02.png'),'Radio Si Ty':('https://radiosity.sk/','2021/11/Logo-horne-menu.svg'),'SKY Radio':('http://skyradio.sk/','/img/logo.png'),'Slobodny vysielac':('https://slobodnyvysielac.sk/zive-vysielanie/','sv-logo.png'),'Zahoracke Radio':('http://www.zahorackeradio.sk/','zahoracke_radio_logo.png'),
 'Impuls Radio':('https://www.impuls.cz/','impuls-logo.webp'),'HEY Radio':('http://heyradio.cz/','HEY_logo_head2022.png'),'Color Music Radio':('http://www.radiocolor.cz/','color_logo_head_2022.png'),
 'Radio Dechovka':('http://www.radiodechovka.cz/','cropped-logo_dechovka_samotne_do_3_cm_rgb.-3.jpg'),'Rock Zone':('http://www.rockzone.cz/','rz_logo_bezFM.svg'),'Radio Relax CZ':('https://radio-relax.cz/new/','LOGO-RELAX-192x80-1.png'),
 'Radio Nostalgie CZ':('https://www.radionostalgie.cz/','Radio_Nostalgie_LOGO_2024.svg'),'Radio Orlicko':('https://www.radioorlicko.cz/','./logo.webp'),'Radio Hana':('https://www.radiohana.cz/','/radio_hana/images/logo.png'),'Netro Life Radio':('https://www.netroliferadio.cz/','netroliferadio-logo-white.svg'),'See Jay Radio':('https://www.play.cz/radio/seejay-radio/','seejay-radio.png'),'Radio Ostravan':('http://www.radioostravan.cz/','radioostravanlogo.png'),'Svobodny vysilac CS':('https://www.svobodny-vysilac.cz/','themes/alpha-forte/img/logo.jpg')}
for st,(page,needle) in choices.items():
 p=next(p for p in pages if p['url']==page);hits=[]
 for img in p['images']:
  for field in ('src','data-pagespeed-lazy-src','content'):
   if needle in img.get(field,''):hits.append(urljoin(p['final_url'],img[field]).split('#')[0])
 if not hits:raise ValueError((st,needle))
 source[st]={'source_page':page,'url':hits[0],'identity':st,'evidence':'Explicit station logo selection from the station homepage.'}
# The broadcaster exposes current station-specific wordmarks directly.
for st,page in {'SRo 1 - Radio Slovensko':'https://slovensko.rtvs.sk/','Radio Slovensko':'https://slovensko.rtvs.sk/','SRo 2 - Radio Regina':'https://reginazapad.rtvs.sk/','SRo 3 - Rádio Devín':'https://devin.rtvs.sk/','SRo 4 - Radio FM':'https://fm.rtvs.sk/','Radio FM':'https://fm.rtvs.sk/','SRo 5 - Radio Patria':'https://patria.rtvs.sk/','SRo 6 - Radio Slovakia International':'https://rsi.rtvs.sk/','SRo 9 - Radio Junior':'https://junior.rtvs.sk/','Radio Litera':'https://litera.rtvs.sk/'}.items():
 p=next(p for p in pages if p['url']==page);img=next(i for i in p['images'] if '/radiostations/' in i.get('src',''))
 source[st]={'source_page':p['final_url'],'url':img['src'],'identity':img.get('alt','').strip(),'evidence':'Station-specific logo on the official broadcaster page.'}
matched=[dict(r,logo=source.get(r['name'])) for r in rows]
(R/'catalog/artwork-sources.json').write_text(json.dumps({'schema':1,'status':'source-verification-and-visual-review','rows':matched},ensure_ascii=False,indent=2)+'\n')
print('Selected station-specific sources',sum(bool(r['logo']) for r in matched),'of',len(rows))
for r in matched:
 if not r['logo']:print(r['country'],r['name'])
