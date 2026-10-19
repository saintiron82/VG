"""Bounded inward-face corrections, preserving the first candidate as evidence."""
import copy,json,time,resource
from pathlib import Path
from resolve_pack import ROOT,HERE,OUT,ref,write,pose
from voxel_character.common import core,coordinate_planes,render_data
from build_audit import source_bounds

NEW=HERE/'placement_r02'

def main():
 start=time.monotonic();basepath=OUT/'resolved_placements.json';p=json.loads(basepath.read_text());original=copy.deepcopy(p);rows=[];changes=[]
 # Inward face at the north bend only; continuous outer curtain remains1.5m thick.
 targets={'FORT_CURTAIN_03_0_05':('north_face',0),'FORT_CURTAIN_04_0_00':('north_face',0),'FORT_CURTAIN_04_0_00:FOOTING:0':('north_face',0),'FORT_CURTAIN_04_0_00:FOOTING:1':('north_face',0),'FORT_CURTAIN_04_0_02':('footing_flare',1.5),'FORT_CURTAIN_04_1_00':('footing_flare',1.5)}
 variants={}
 for x in p['placements']:
  if x['id'] not in targets:continue
  mode,edge=targets[x['id']];signature=(x['source_id'],mode)
  if signature not in variants:
   s=json.loads((ROOT/x['source']['path']).read_text());oldref=x['source'];s['id']+='_road_face_r02';s['revision']=2
   if mode=='north_face':
    b=source_bounds(s)
    s.setdefault('assembly_cuts',[]).append({'id':'retain_continuous_outer_curtain_clear_inner_road','selector':{},'shape':{'kind':'box','min':[b['min'][0],b['min'][1],0],'max':[b['max'][0],b['max'][1],b['max'][2]]}})
   else:
    for c in s['components']:
     if c['id']=='bearing':
      for op in c['operations']:
       op['shape']['min'][2]=-1.5;op['shape']['max'][2]=1.5
   s.setdefault('provenance',{}).update(road_face_repair_author=ref(Path(__file__)),road_face_repair_parent=oldref,reason='Clear the existing registered road without moving the street, opening another gate, or changing the outer curtain line.')
   s.setdefault('extensions',{})['road_face_repair']={'mode':mode,'source_boundary_unchanged':True,'new_gate':False,'outer_wall_continuous':True,'minimum_retained_body_thickness_m':1.5 if mode=='north_face' else 3}
   sp=NEW/'masters'/f"{s['id']}.json";write(sp,s);t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000);assert c['valid'];r=render_data.make_render_data(c);cp=NEW/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,r);a={'id':s['id'],'source':ref(sp),'cache':ref(cp),'master_hash':core.digest(s),'valid':True,'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quads':r['quad_count'],'bounds':r['bounds'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};variants[signature]=a;rows.append(a)
  a=variants[signature];before=copy.deepcopy(x);x.update(asset_key=a['id'],source_id=a['id'],source=a['source'],cache=a['cache'],master_hash=a['master_hash'],actual_cached_bounds_local_m=a['bounds']);b=a['bounds'];poly=[]
  for xx,z in ((b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])):
   q=pose([xx,0,z],x['position_m'],x['yaw_degrees']);poly.append([q[0],q[2]])
  x['outer_footprint_xz_m']=poly;x['world_y_range_m']=[x['position_m'][1]+b['min'][1],x['position_m'][1]+b['max'][1]];changes.append({'placement_id':x['id'],'old_source':before['source'],'old_cache':before['cache'],'new_source':x['source'],'new_cache':x['cache'],'old_footprint_xz_m':before['outer_footprint_xz_m'],'new_footprint_xz_m':poly,'transform_unchanged':True,'mode':mode})
 used={x['asset_key'] for x in p['placements']};p['assets']=[a for a in p['assets'] if a['id'] in used]+rows
 p['base_pack']=ref(basepath);p['status']='resolved_fortification_r02_road_face_repair_pending_independent_review'
 for support in p['support_evidence']:
  if support['placement_id'] in targets:
   support['original_conservative_sample_envelope_retained']=True;support['support_shape_change']='Inward-side or flare material removed. Remaining foundation bottom is unchanged, and original conservative support samples still bound retained footprint.'
 report={'schema':'riverstone.city.fortification_road_face_repair.v1','base_pack':ref(basepath),'changes':changes,'new_caches':rows,'total_wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_openings':0,'road_edits':[],'placement_transform_edits':[],'actual_scene_viewed':False};write(NEW/'repair_report.json',report);p['road_face_repair']=ref(NEW/'repair_report.json');write(NEW/'resolved_placements.json',p);print(json.dumps({'new_caches':len(rows),'changed_placements':len(changes),'peak_candidates':max(a['candidate_cells'] for a in rows),'total_seconds':report['total_wall_seconds']},indent=2))
if __name__=='__main__':main()
