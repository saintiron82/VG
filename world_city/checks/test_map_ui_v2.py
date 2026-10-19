#!/usr/bin/env python3
"""Use the cloud workspace's Chromium to inspect the local standalone planning map."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[2]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-gpu'])
 page=browser.new_page(viewport={'width':1500,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((R/'world_city/maps/city_layout_v2.html').as_uri());n=page.locator('.building').count()
 page.locator('#find').click();empty='입력하세요' in page.locator('#result').inner_text()
 page.locator('#search').fill('대성당');page.locator('#find').click();search=page.locator('#name').inner_text()=='대성당' and 'new_assembly_required' in page.locator('#detail').inner_text()
 page.locator('#D01-B001').click(force=True);clicked=page.locator('#name').inner_text()=='큰 성 주성'
 result={'passed':n==1308 and empty and search and clicked and not errors,'browser':'cloud workspace Chromium, local file, no external dependencies','building_elements':n,'empty_search_guard':empty,'name_search_and_unbuilt_detail':search,'svg_building_click':clicked,'page_errors':errors}
 browser.close()
(R/'world_city/checks/ui_validation_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['passed']else 1)
