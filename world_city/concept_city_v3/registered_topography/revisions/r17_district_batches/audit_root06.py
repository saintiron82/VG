import json
from . import author as a,preflight_layout,regeneration_interfaces,side_clearance

def run():
 folder=a.HERE/'root06_regrade_r04';out=folder/'interfaces.json'
 if out.exists():raise SystemExit('Preserve prior interface proof')
 profile=json.loads((folder/'profile.json').read_bytes());scene=a.load_scene();layout=json.loads((a.HERE/'layout_draft_r02/selected_layout.json').read_bytes());p=profile['polygon_xz_m'];b=a.bounds(p);window=[[b[0]-1,b[1]-1],[b[2]+1,b[1]-1],[b[2]+1,b[3]+1],[b[0]-1,b[3]+1]];index=a.TriangleIndex(scene,[window]);preflight_layout.virtual_restorations(index,layout);d=regeneration_interfaces.build(scene,index,profile)
 # All retained side fragments and new closures must leave the route interior clear.
 side_scene=dict(surfaces={});bykey={(r['material'],r['triangle_index']):r for r in d['side_surface_edits']}
 for r in side_clearance.SideIndex(scene,[p]).rows:
  tris=bykey.get((r['material'],r['triangle_index']),{}).get('replacement_triangles_xyz_m',[r['vertices_xyz_m']]);side_scene['surfaces'].setdefault(r['material'],[]).extend(v for t in tris for v in t)
 side_scene['surfaces'].setdefault('bank',[]).extend(v for t in d['appended_retaining_triangles_xyz_m']for v in t)
 d['after_side_clearance']=side_clearance.SideIndex(side_scene).audit(profile['triangles']);d['profile_sha256']=a.sha(folder/'profile.json');out.write_text(json.dumps(d,separators=(',',':'))+'\n');print({k:d[k]for k in ('status','maximum_fill_m','maximum_cut_m')});print('bank edits',len(d['side_surface_edits']),'new sides',len(d['appended_retaining_triangles_xyz_m']),'gaps',len(d['uncovered_boundary_segments']),'contacts',len(d['after_side_clearance']['contacts']));print(a.sha(out))
if __name__=='__main__':run()
