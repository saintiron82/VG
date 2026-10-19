#!/usr/bin/env python3
"""Emit finite common master JSON only; never sample/compile or mutate live scene.

The source set is an integration contract, not a ready atomic terrain bundle.
Recess/collar/buffer promotion belongs to the coordinating terrain integrator.
"""
import argparse,json,math
from author import HERE,ROOT,terrain,g,box,rect,area,clean,subtract,FILES,digest

def emit(overlay,out):
 out.mkdir(parents=True,exist_ok=True);field=terrain.default_field();block=overlay['first_infill_block'];manifest=[]
 body=[b['source_footprint_xz_m'] for b in block['building_instances']]
 # Split grouped path/court surfaces to <=8m exact source bounds. Ownership is
 # made disjoint before extrusion; no bbox may silently fill gaps or buildings.
 groups={}
 features=[(p['id'],'earth',p['ribbon_polygons_xz_m']) for p in block['paths']]
 features += [(z['id'],z['material'],[z['polygon_xz_m']]) for z in block['zones']]
 for identity,material,polys in features:
  for poly in polys:
   bb=box(poly)
   for ix in range(math.floor(bb[0]/8),math.ceil(bb[2]/8)):
    for iz in range(math.floor(bb[1]/8),math.ceil(bb[3]/8)):
     tile=rect(ix*8,iz*8,(ix+1)*8,(iz+1)*8);clipped=clean(g.convex_intersection(poly,tile))
     if not clipped:continue
     key=(ix,iz,material);record=groups.setdefault(key,{'polygons':[],'features':[],'material':material})
     # Paths own overlapping garden/court access. Original road surfaces will be
     # excluded by the integrating layer to avoid coincident collision owners.
     owned=[p for (xx,zz,_),r in groups.items() if (xx,zz)==(ix,iz) for p in r['polygons']]
     additions=subtract(clipped,body+owned)
     record['polygons'].extend(additions);record['features'].append(identity)
 for (ix,iz,material),rec in sorted(groups.items()):
  if not rec['polygons']:continue
  master=terrain.make_surface_master([ix*8,iz*8,(ix+1)*8,(iz+1)*8],rec['polygons'],field,material=rec['material'])
  master['metadata']['source_landuse_feature_ids']=sorted(set(rec['features']))
  master['metadata']['atomic_integration_required']=True
  path=out/(master['id']+'.master.json');path.write_text(json.dumps(master,sort_keys=True,indent=2)+'\n')
  manifest.append({'id':master['id'],'path':str(path.relative_to(ROOT)),'sha256':digest(path),'kind':'walk_surface',
    'requested_pitch_m':.1,'finite_polygon_area_m2':sum(area(p) for p in rec['polygons']),
    'layer_replacement_requirement':'exclude current public pavement; replace terrain atomically with buried support, buffer and shoulder where required'})
 for b in block['building_instances']:
  projection={'id':b['id'],'body_footprint_xz_m':b['source_footprint_xz_m'],'foundation':b['foundation_requirement']}
  master=terrain.make_foundation_master(projection);path=out/(master['id']+'.master.json')
  path.write_text(json.dumps(master,sort_keys=True,indent=2)+'\n')
  manifest.append({'id':master['id'],'path':str(path.relative_to(ROOT)),'sha256':digest(path),'kind':'building_foundation',
    'requested_pitch_m':.5,'building_id':b['id'],'required_terrain_cut':master['metadata']['required_terrain_cut']})
 result={'schema':'riverstone.landuse.common_source_manifest.v1','status':'source_only_no_compile_no_runtime_promotion',
   'entries':manifest,'source_count':len(manifest),'source_overlay_sha256':digest(HERE/'candidate_overlay.json'),
   'foundation_count':len(block['building_instances']),'walk_source_count':sum(x['kind']=='walk_surface' for x in manifest),
   'integration_rule':'Source blocks never create floating overlays: consume required terrain cuts and build the terrain replacement bundle before adding buildings or collision surfaces.'}
 (out/'manifest.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(HERE/'common_sources'));args=p.parse_args()
 data=json.loads((HERE/'candidate_overlay.json').read_text());m=emit(data,__import__('pathlib').Path(args.out));print(json.dumps({k:m[k] for k in ('status','source_count','foundation_count','walk_source_count')}))
if __name__=='__main__':main()
