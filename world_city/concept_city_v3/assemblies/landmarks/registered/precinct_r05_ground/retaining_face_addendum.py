"""Clarify the immutable clergy patch's ten local retaining-face edits."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5]
def load(p):return json.loads(p.read_text())
def ref(p):return{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
p=HERE/'local_frame_r01/corner_repair_r01/terrain_patch/surface_patch.json';patch=load(p);scene=load(ROOT/patch['base_scene']['path']);rows=[]
for r in patch['surface_edits']:
 if r['material']!='bank':continue
 tri=scene['surfaces']['bank'][r['triangle_index']*3:r['triangle_index']*3+3]
 rows.append({'original_triangle_index':r['triangle_index'],'source_triangle_sha256':r['source_triangle_sha256'],'original_vertices_xyz_m':tri,'replacement_triangles_xyz_m':r['replacement_triangles_xyz_m'],'classification':'Local clergy retaining strip beside a superseded native floor; not riverbank or water geometry.','bounds_xyz_m':{'min':[min(p[j]for p in tri)for j in range(3)],'max':[max(p[j]for p in tri)for j in range(3)]}})
assert len(rows)==10
out={'schema':'riverstone.clergy.retaining_face_addendum.v1','immutable_surface_patch':ref(p),'immutable_index_ledger':ref(p.parent/'index_ledger.json'),'base_scene':patch['base_scene'],'edited_local_retaining_faces':rows,'bank_material_is_not_unchanged':True,'water_material_is_unchanged':not any(r['material']=='water'for r in patch['surface_edits'])and not patch['appended_surfaces'].get('water'),'untouched_bank_triangle_policy':'Every unedited original record retains exact values and order. See frozen apply_edits unchanged ranges in the bound index ledger.','geometry_change_from_this_addendum':False}
(HERE/'retaining_face_addendum.json').write_text(json.dumps(out,indent=2)+'\n');print(ref(HERE/'retaining_face_addendum.json'))
