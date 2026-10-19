"""Read-only source inspection; writes only its own audit report, never compiles or edits assets."""
import json,mmap,hashlib,collections,math
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[4];C=R/'world_city/concept_city_v3';BASE=C/'evidence/r8_final110_runtime_r01/scene.json'
def load(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 with BASE.open('rb')as f:
  mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);decoder=json.JSONDecoder()
  def read(key,bracket):
   t=('"'+key+'":'+bracket).encode();i=mm.find(t)+len(t)-1;return decoder.raw_decode(mm[i:].decode())[0]
  assets=read('common_assets','{');placements={p['id']:p for p in read('common_instances','[')};base_hash=hashlib.sha256(mm).hexdigest();mm.close()
 index=C/'registered_integration/r9/integration_r02_camera/index.json';d=load(index);assert d['base_scene_sha256']==base_hash;refs=[ref(index)]
 for row in d['packs']:
  p=R/row['path'];assert ref(p)['sha256']==row['sha256'];q=load(p);refs.append(ref(p));assets.update(q.get('common_assets',{}))
  for i in q.get('remove_instance_ids',[]):placements.pop(i,None)
  for v in q.get('replace_instances',[]):placements[v['id']]=dict(placements[v['id']],**v)
  for v in q.get('add_instances',[]):placements[v['id']]=v
 chosen=['B_REG_0038','cathedral_registered:nave_aisles_transept','BRIDGE_MAIN_RIVER:NORTH_VISIBLE_ROAD'];rows=[]
 for id in chosen:
  p=placements[id];a=assets[p['asset_key']];mp=R/a['master_path'];rp=R/a['render_path'];m=load(mp);render=load(rp);assert ref(mp)['sha256']==a['master_sha256'];assert ref(rp)['sha256']==a['render_sha256'];refs.extend([ref(mp),ref(rp)]);ops=[o for c in m['components']for o in c['operations']]
  rows.append(dict(instance=p,asset_key=p['asset_key'],master=ref(mp),render=ref(rp),pitch_m=render['pitch'],cell_count=render['cell_count'],quad_count=render['quad_count'],component_count=len(m['components']),operation_count=len(ops),component_operations=[dict(id=c['id'],count=len(c['operations']),selected_operations=c['operations'][:3]if c['id']in ['roof','masonry','body']else[])for c in m['components']],materials=m['materials'],material_operation_counts=dict(collections.Counter(o.get('material','CUT')for o in ops)),detail_named_operations=[o for o in ops if any(s in o['id'].lower()for s in ['mortar','brick','tile','joint','ridge','roof_plane'])]))
 hp=R/'voxel_character/common/assets/house/master.json';house=load(hp);cs={c['id']:c for c in house['components']};roof=cs['roof_section']['operations'];foundation=cs['foundation_1.6']['operations'];refs.append(ref(hp))
 original=dict(source=ref(hp),source_status='Canonical detailed common original; not an active whole-house asset in this resolved city index.',components=len(house['components']),instances=len(house['instances']),operations=sum(len(c['operations'])for c in house['components']),roof_section_operation_count=len(roof),roof_section_individual_tile_count=len(roof)-1,tile_vertical_thickness_m=.12,tile_normal_thickness_m=.12/math.sqrt(1+(2.8/3.8)**2),tile_course_advance_m=.28,tile_course_overlap_m=.035,tile_side_gap_m=.018,foundation_stone_width_m=.375,foundation_stone_height_m=.175,foundation_mortar_joint_m=.025,foundation_stone_relief_m=.025,foundation_examples=foundation[:8],roof_examples=roof[:8],not_claimed='Clay brick topology is not inferred from stone names. Geometry dimensions are continuous authoring dimensions; a cache may not retain details smaller than its pitch.')
 paths=['voxel_character/common/core.py','voxel_character/common/coordinate_planes.py','voxel_character/common/render_data.py','voxel_character/tools/mesh.py','voxel_character/common/preview/RenderData.gd','world_city/concept_city_v3/preview_r9/City.gd','world_city/runtime_city/archetypes/ordinary_r2.py','world_city/runtime_city/parts/author.py','voxel_character/common/assets/house/README_KO.md']
 refs.extend(ref(R/p)for p in paths)
 out=dict(schema='riverstone.r10.material_detail_source_audit.v1',status='READ_ONLY_SOURCE_AUDIT_NO_IMPLEMENTATION',base_scene=dict(path=str(BASE.relative_to(R)),sha256=base_hash),resolved_index=ref(index),resolved_native_instance_count=len(placements),canonical_original_house=original,current_representatives=rows,architecture=dict(master='Continuous geometry operations plus material roles; no asset-name dispatch in common compiler.',compiler='Uniform pitch per compile with optional minimum_cells constraints; finite candidate/output budgets.',mesher='Greedy exterior occupancy faces grouped by axis/sign/plane/material. Same-color coplanar faces merge; author feature ID is not a seam boundary.',renderer='Current preview_r9 City common meshes flatten material colors to vertex colors, roughness1, metallic_specular0. No UV, normal-map or per-material roughness binding in inspected paths.',runtime_lod='Current asset record supplies one render_path;64m spatial MultiMesh batching is not distance-switching LOD. No visibility_range/distance LOD selection in City.load_common.',roads='Current data.surfaces.road renders finite triangles with position/normal and one material color; grade/topology is real, per-paver seams/thickness are not implied. Native north approach module is separately included as current representative.'),source_refs=list({v['path']:v for v in refs}.values()))
 (H/'source_evidence.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 print([(r['instance']['id'],r['asset_key'],r['pitch_m'],r['quad_count'],r['operation_count'])for r in rows]);print('original roof tiles',len(roof)-1)
if __name__=='__main__':main()
