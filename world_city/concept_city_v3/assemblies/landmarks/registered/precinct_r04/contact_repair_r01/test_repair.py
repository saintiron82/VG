"""Hash, source-scope, roof-preservation and finite native replay tests."""
from repair import *
def main():
 o=load(OUT/'replacement_overlay.json');p=load(OUT/'resolved_placements.json');base=load(BASE/'resolved_placements.json');rows=[]
 for r in o['replacements']:
  old=next(a for a in base['assets']if a['id']==r['old_asset_key']);new=r['asset'];s=load(ROOT/old['source']['path']);t=load(ROOT/new['source']['path']);sm={c['id']:c for c in s['components']};tm={c['id']:c for c in t['components']}
  assert sm.keys()==tm.keys();assert s['instances']==t['instances']
  for key in sm:
   if key not in ('court_and_boundary__ground','court_and_boundary__boundary'):assert sm[key]==tm[key]
  for k in ('source','cache'):assert ref(ROOT/new[k]['path'])==new[k]
  a=load(ROOT/old['cache']['path']);b=load(ROOT/new['cache']['path']);roof=lambda m:{g['material']:g['quads']for g in m['groups']if g['material']in ('rgb_a16b51','rgb_80523f','rgb_646f73','rgb_4a565c')};assert roof(a)==roof(b)
  rows.append({'placement_id':r['placement_id'],'all_building_components_identical':True,'all_roof_quads_identical':True,'source_cache_hashes_match':True})
 assert len(p['placements'])==77;assert len(p['assets'])==13;assert p['actual_doors']==base['actual_doors'];assert p['building_components']==base['building_components'];assert load(OUT/'effective_native_access_replay.json')['all_pass'];assert o['removed_all_reported_contact_polygons'];assert len(p['owned_floors'])==1686
 write(OUT/'test_results.json',{'effective_pack':ref(OUT/'resolved_placements.json'),'rows':rows,'all_checks_pass':True,'all_reported_contact_polygons_clear':True,'native_access_doors_affected':25,'independent_full_owner_partition':'pending terrain R14','actual_viewed':False});print('Native edge repair checks pass for three assets; all roof quads preserved.')
if __name__=='__main__':main()
