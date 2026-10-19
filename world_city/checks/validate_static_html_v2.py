#!/usr/bin/env python3
"""HTML/JS static checks only. Does not claim browser layout or click testing."""
from pathlib import Path
from html.parser import HTMLParser
import json,re,subprocess,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[2]
class Scan(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.buildings=[];self.external=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.append(a['id'])
  if 'data-building'in a:self.buildings.append(a['data-building'])
  for k in ('src','href'):
   if a.get(k,'').startswith(('http:','https:','//')):self.external.append(a[k])
page=(R/'world_city/maps/city_layout_v2.html').read_text();scan=Scan();scan.feed(page);code=re.search(r'<script>(.*?)</script>',page,re.S).group(1)
syntax=subprocess.run(['node','--check'],input=code,text=True,capture_output=True)
plan=json.loads((R/'world_city/data/city_brief.v2.json').read_text());expected={b['id']for b in plan['building_plans']};ET.parse(R/'world_city/maps/city_layout_v2.svg')
result={'passed':syntax.returncode==0 and len(scan.ids)==len(set(scan.ids)) and set(scan.buildings)==expected and not scan.external,'js_syntax_passed':syntax.returncode==0,'syntax_error':syntax.stderr,'unique_dom_ids':len(scan.ids)==len(set(scan.ids)),'building_record_dom_match':set(scan.buildings)==expected,'building_elements':len(scan.buildings),'external_dependencies':scan.external,'svg_xml_parsed':True,'scope':'static syntax, ids and embedded records only; browser interaction unverified'}
(R/'world_city/checks/html_static_validation_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed']else 1)
