"""Bind the one small court-datum supersession into the prepared bulk source."""
import json,copy,math
from .screen import HERE,write
from .. import author as a,native_clearance
ADD=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/contour_revision_r01/b02_shared_datum_addendum_r01.json'
SHA='7c87f2c04e91a17e8d137b940212f534eccdc615bdb8a7d8bdd507c82409f193'

def run():
 assert a.sha(ADD)==SHA
 add=json.loads(ADD.read_bytes());layout=json.loads((HERE/'effective_source_layout.json').read_bytes());prep=json.loads((HERE/'effective_prepared_parcels.json').read_bytes());hid=add['holding_id'];poses={r['id']:r for r in add['replacement_native_placements']};doors={r['id']:r for r in add['replacement_actual_doors']}
 layout['placements']=[poses.get(r['id'],r)for r in layout['placements']];layout['actual_doors']=[doors.get(r['id'],r)for r in layout['actual_doors']];layout['holdings']=[add['replacement_holding']if r['id']==hid else r for r in layout['holdings']];layout['source_references'].append(dict(path=str(ADD.relative_to(a.ROOT)),sha256=SHA));prep['parcels']=[add['replacement_terrain_parcel']if r['id']==hid else r for r in prep['parcels']]
 for r in prep['native_earth_bearings']:
  if r['holding_id']==hid:r['floor_y_m']+=add['rigid_y_delta_m'];r['native_bottom_y_m']+=add['rigid_y_delta_m']
 prep['source_references']=layout['source_references'];write('effective_source_layout_r03.json',layout);write('effective_prepared_parcels_r03.json',prep)
 manifest_path=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/effective_city_manifest_r01.json';manifest=json.loads(manifest_path.read_bytes());assets={};placements=[];actual=[];refs=[]
 for d in manifest['districts']:
  if d['block_id']=='BLOCK_015':continue
  pack=native_clearance.require_ref(d['pack']);refs.append(d['pack'])
  for k,v in pack['assets'].items():
   if k in assets and a.canonical_sha(v)!=a.canonical_sha(assets[k]):raise ValueError('Conflicting shared asset '+k)
   assets[k]=v
  placements.extend(poses.get(r['id'],r)for r in pack['placements']);actual.extend(doors.get(r['id'],r)for r in pack['actual_doors'])
 assert len({r['id']for r in placements})==len(placements)
 assert set(poses)<={r['id']for r in placements}
 pack=dict(schema='riverstone.r17.prepared_multi_district_native_pack.v1',status='SOURCE_PREPARED_PENDING_MATCHING_TERRAIN_PROFILE_AND_SIDE_ACCEPTANCE',base_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)),sha256=a.SCENE_SHA256),assets=assets,placements=placements,actual_doors=actual,replaced_placement_ids=layout['retired_source_ids'],retired_foundation_proxy_ids=[sid+':owned_foundation'for sid in layout['retired_source_ids']],source_references=refs+[dict(path=str(ADD.relative_to(a.ROOT)),sha256=SHA)],summary=dict(holdings=len(layout['holdings']),native_ranges=len(layout['placements']),native_instances=len(placements),actual_doors=len(actual),retired_ids=len(layout['retired_source_ids'])),integration_policy='Apply only with the final accepted holding subset and its complete matching terrain/retirement/access ledger. Never activate all source poses while applying a smaller ground subset.',activation=False)
 write('prepared_native_pack_r03.json',pack);proof=native_clearance.check(layout);write('native_source_preflight_r03.json',proof);print(pack['summary']);print(proof['summary'])
if __name__=='__main__':run()
