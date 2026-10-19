"""Exact final atomic emission/native verification plus bounded R07 lineage."""
import collections,hashlib,json,pathlib,struct,gc
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def source(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p
 assert sha(p)==r['sha256'],'Changed final activation source '+str(p)
 return p
read=lambda p:json.loads(p.read_bytes())
def canonical(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def key(t):return struct.pack('<9d',*(float(x)for v in t for x in v))
def counts(vs):return collections.Counter(key(vs[i:i+3])for i in range(0,len(vs),3))
def apply_array_edits(vs,rows,index_key):
 selected={}
 for r in rows:
  i=r[index_key];assert i not in selected and 0<=i<len(vs)//3,'Unknown or duplicate producer row';assert vs[3*i:3*i+3]==r['source_triangle_xyz_m'];assert canonical(r['source_triangle_xyz_m'])==r['source_triangle_sha256'];selected[i]=r
 out=[]
 for i in range(len(vs)//3):
  r=selected.get(i)
  if r:out.extend(v for t in r['replacement_triangles_xyz_m']for v in t)
  else:out.extend(vs[3*i:3*i+3])
 return out

def public_lineage(binding,doc):
 h=CITY/'registered_topography/revisions/public_corridors_r18';northp=h/'north_junction_transition_r01/appended_top_retirement_ledger.json';sidep=h/'causeway_side_joins_r01/producer_row_retirement_ledger.json';north=read(northp);side=read(sidep);start=read(source(north['source']));mid=read(source(north['output']));nrows=[r for r in north['rows']if r['material']=='road'];assert len(nrows)==107
 assert apply_array_edits(start['appended_surfaces']['road'],nrows,'source_appended_triangle_index')==mid['appended_surfaces']['road'];sidebinding=read(source(side['source_binding']));sidestart=read(source(sidebinding['patches'][15]));assert mid['appended_surfaces']['road']==sidestart['appended_surfaces']['road'];srows=[r for r in side['rows']if r.get('patch_index')==15 and r['location']=='appended_surfaces'and r['material']=='road'];assert len(srows)==227;end=read(source(binding['patches'][15]));assert apply_array_edits(sidestart['appended_surfaces']['road'],srows,'source_triangle_index')==end['appended_surfaces']['road'];old=read(source(doc['sources']['original_412_catalog']));field=read(source(old['activation_requirements']['finite_public_field']));original=collections.Counter(key(t)for r in field['records']for t in r['triangles_xyz_m']);missing_before=original-counts(start['appended_surfaces']['road']);assert not missing_before,'R07 is not present verbatim before declared bounded updates';allowed=collections.Counter(key(r['source_triangle_xyz_m'])for r in nrows+srows);current=counts(end['appended_surfaces']['road']);missing=original-current;assert not(missing-allowed),'Unexplained original R07 retirement';unaffected=original-allowed;assert not(unaffected-current);assert not((allowed-current)&current),'Internal counter contradiction'
 return dict(north_ledger=ref(northp),side_ledger=ref(sidep),first_source=north['source'],north_output=north['output'],side_source=sidebinding['patches'][15],final_public_producer=binding['patches'][15],north_exact_rows=len(nrows),side_exact_rows=len(srows),original_r07_triangle_instances=sum(original.values()),original_r07_changed_instances=sum(missing.values()),original_r07_unaffected_required=sum(unaffected.values()),ordered_array_reconstruction_exact=True)

def validate(scene,binding_path,doc):
 binding=read(binding_path);assert ref(binding_path)==doc['activation_requirements']['atomic_binding'];assert binding['base_scene']['sha256']=='1429ae51b7c72b12940dcf0dd7e12c2684cab95f81735d228bba64dc819317c1';assert len(binding['patches'])==29 and len(binding['packs'])==20 and len(binding['collision_contracts'])==13
 for r in binding['evidence']:source(r)
 lineage=public_lineage(binding,doc);patch_materials=collections.defaultdict(list);patch_rows=[]
 for rr in binding['patches']:
  path=source(rr);p=read(path);assert p['base_scene_sha256']==binding['base_scene']['sha256'];summary={}
  for mat,vs in p['appended_surfaces'].items():assert mat!='water'and len(vs)%3==0;patch_materials[mat].append(rr);summary[mat]=len(vs)//3
  patch_rows.append(dict(source=rr,id=p['id'],triangle_instances=summary))
 materials={}
 for mat,refs in patch_materials.items():
  required=collections.Counter()
  for rr in refs:required.update(counts(read(source(rr))['appended_surfaces'][mat]))
  actual=counts(scene['surfaces'].get(mat,[]));missing=required-actual;materials[mat]=dict(required_triangle_instances=sum(required.values()),missing_triangle_instances=sum(missing.values()));assert not missing,'Final emitted triangles absent from actual '+mat;del required,actual,missing;gc.collect()
 # Existing private23/18/20 producer tops must still all be present exactly.
 old=read(source(doc['sources']['original_412_catalog']));preserved=[]
 for rr in old['activation_requirements']['appended_surface_patches']:
  p=read(source(rr));s={}
  for mat,vs in p['appended_surfaces'].items():required=counts(vs);actual=counts(scene['surfaces'][mat]);assert not(required-actual),'Unexplained predecessor private emission change';s[mat]=sum(required.values())
  preserved.append(dict(source=rr,retained_triangle_instances=s))
 selected={};retired=set();pack_rows=[]
 for rr in binding['packs']:
  p=read(source(rr));assets=p['assets']if isinstance(p['assets'],dict)else{a['id']:dict(render_path=a['cache']['path'],render_sha256=a['cache']['sha256'])for a in p['assets']};removed=set(p.get('replaced_placement_ids',[]))|set(p.get('replacement_ledger',{}).get('existing_native_placements_removed',[]))
  for pid in removed:selected.pop(pid,None)
  retired.update(removed)
  for po in p['placements']:selected[po['id']]=(po,assets[po['asset_key']],rr);retired.discard(po['id'])
  pack_rows.append(dict(source=rr,placements=len(p['placements']),explicit_retired_ids=sorted(removed)))
 actual={p['id']:p for p in scene['common_instances']};assert not(retired&set(actual)),'Superseded native instances remain active';posekeys=['asset_key','position_m','yaw_rad','scale','transform']
 for pid,(po,asset,rr)in selected.items():
  assert pid in actual,'Missing final native '+pid
  for k in posekeys:
   default=0 if k=='yaw_rad'else[1,1,1]if k=='scale'else None;assert actual[pid].get(k,default)==po.get(k,default),'Changed native pose '+pid+' '+k
  act=scene['common_assets'][po['asset_key']];assert act['render_sha256']==asset['render_sha256'];assert sha(ROOT/act['render_path'])==act['render_sha256']
 train=read(source(doc['sources']['required_training_entry']));tp=actual[train['native_stair_id']];assert tp['asset_key']==train['native_asset_key'];assert all(tp.get(k,[1,1,1]if k=='scale'else 0)==v for k,v in train['native_transform'].items())
 contracts={c['id']:c for c in scene['collision_contracts']};contract_checks=[]
 for rr in binding['collision_contracts']:
  c=read(source(rr));actualc=contracts[c['id']];assert all(c.get(k)==actualc.get(k)for k in['id','disable_native_mesh_collider_ids','add_triangles_world_xyz_m']);contract_checks.append(dict(source=rr,id=c['id'],exact_physical_fields_match=True))
 return dict(binding=ref(binding_path),public_lineage=lineage,pack_checks=pack_rows,selected_native_instances=len(selected),retired_native_ids=sorted(retired),append_checks=dict(patches=patch_rows,materials=materials,preserved_61_private=preserved,method='Exact ordered triangle-value multiset inclusion for all 29 active producers, with unchanged predecessor private tops and explicitly reconstructed north/causeway public successors.'),contract_checks=contract_checks)
