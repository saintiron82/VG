"""One-time observed-image design transcription; generation reads these JSON files."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
rules={
 'schema':'riverstone.reference_character.rules.v1','version':1,
 'source_modules':'../../lily_city/revisions/original_lily_r01/data/modules',
 'source_rig':'../../lily_city/data/rig.json',
 'sampling':{'bulk_m':.025,'detail_m':.0125,'detail_categories':['face','bang','flowers','halo','ornament','ribbon'],'maximum_candidate_cells_per_layer':800000,'maximum_cells_per_layer':90000,'maximum_total_cells':100000,'maximum_quads':25000},
 'body':{'height_m':1.775,'adult_proportions':'reuse original_lily adult_base and soft_taper modules; no enlargement of bust, hips, or anatomy','shoulder':[.195,1.32,.015],'elbow':[.213,1.115,.105],'wrist':[.065,1.025,.25],'arm_radius':.045,'forearm_radius':.036},
 'skirt':{'gore_count':20,'band_height_m':.05,'shell_thickness_m':.0375,'lining_thickness_m':.025,'profile_y_radius':[[.08,.81],[.20,.87],[.35,.81],[.50,.72],[.65,.59],[.80,.43],[.95,.25],[1.055,.145]],'front_open_half_angle_deg':24,'front_drape_min_y':.89,'depth_scale':.83,'fold_amplitude_m':.045,'scallop_m':.085},
 'hair':{'strand_count':11,'width_m':.065,'tip_width_m':.018,'head_y':1.78,'rear_depth_m':-.18,'strand_depth_spacing_m':.016,'fan_reach_m':.78,'fan_drop_m':.74},
 'halo':{'center_m':[0,1.83,-.14],'outer_radius_m':.215,'inner_radius_m':.153,'line_radius_m':.010,'arc_step_deg':9,'outer_arc_degrees':[[0,78],[93,173],[190,263],[279,350]],'inner_arc_degrees':[[0,360]],'rays_degrees':[30,145,270]},
 'bouquet':{'center_m':[0,1.035,.335],'flower_count':15,'flower_radius_m':.038,'petal_radius_m':.023,'petal_count':5,'leaf_count':9},
 'rig_contract':{'reuse':'common character semantic part names, hierarchy, coordinate axes and hand/head sockets','rest_pose':'hands together holding bouquet; bespoke shoulder/elbow/wrist pivots','new_parts':['hair_tail_back','hair_tail_left','hair_tail_right','halo','ornament','bouquet','ribbon','dress_bodice'],'runtime':'rest-pose review only; no claim that locomotion was retargeted or verified'},
 'limits':{'initial_disk_budget_bytes':26214400,'no_whole_character_high_resolution':True,'backs_and_hidden_surfaces':'new authored 3D interpretation, not observed in single image','reference_images_used_for':'observation and side-by-side comparison only; never projected as model geometry'}
}
write(ROOT/'data/rules.json',rules)
base={'skin':'efd0c5','skin_light':'f9e2d7','skin_shadow':'cfaaa5','dress':'f6f5fc','dress_light':'ffffff','dress_shadow':'dcddeb','lining':'b2cbe6','lining_shadow':'8faecf','eye_white':'fff5ee','iris':'31b6c5','iris_light':'8be1dd','pupil':'24424e','lash':'4c3d4e','lip':'b77988','leaf':'7f9b58','leaf_light':'b0bd6c','stem':'7d9659','flower':'fbfbff','flower_shadow':'d4dce9','flower_center':'e5dca1','silver':'cbc6c5','silver_light':'e9e3dc','silver_shadow':'9c99ab','hair':'cbc6c5','hair_light':'e9e3dc','hair_shadow':'9c99ab','halo':'2bcad9','ribbon':'56bfd5','jewel':'b3e5ed','shoe':'e8eaf4'}
presets=[{
 'id':'violet_bride','label':'Violet halo · gold eyes','reference_file':'reference/1000041593.webp','hair_flow_sign':1,'hair_style':'center_part_long','front_bang_points':[[[-.15,1.685],[-.11,1.755],[-.025,1.778],[-.016,1.692],[-.09,1.635],[-.135,1.62]],[[.005,1.775],[.07,1.755],[.14,1.706],[.153,1.648],[.112,1.626],[.060,1.676],[.013,1.695]]],
 'palette':dict(base,skin='b98583',skin_light='d4a4a1',skin_shadow='916c78',hair='3c3445',hair_light='665374',hair_shadow='292631',silver='3c3445',silver_light='665374',silver_shadow='292631',iris='dfb64b',iris_light='fff1a0',lining='c7c4e2',lining_shadow='a3a0c2',halo='72527e',ribbon='b568bc',jewel='f4eef6',shoe='e8dce9'),
 'gloves':True,'crown':False,'neck_flower':False,'hairpin':True,'ribbon_turns':1.55,'ribbon_slope':.58,
 'observations':['Long dark purple hair fans to image-right','Both gold eyes visible below parted bangs','Circular segmented purple halo behind head','White dress with wide lavender-lined billowing skirt and high front opening','Long white gloves and pale floral bouquet','Fine hairpin at image-right temple','Purple ribbon sweeps around dress'],
 'new_interpretations':['Rear hair volume and separated locks','Rear bodice fastening and skirt radial construction','Bouquet back and handle','Neutral centered rest posture adapted for semantic rig','All side/back silhouettes']
 },{
 'id':'cyan_bride','label':'Cyan halo · side-swept fringe','reference_file':'reference/1000041592.webp','hair_flow_sign':-1,'hair_style':'one_eye_swept','front_bang_points':[[[-.145,1.69],[-.105,1.75],[-.025,1.78],[.05,1.75],[.068,1.66],[.028,1.575],[-.06,1.515],[-.125,1.56],[-.155,1.625]],[[.058,1.756],[.11,1.72],[.155,1.66],[.158,1.57],[.132,1.52],[.113,1.56],[.118,1.65]]],
 'palette':base,'gloves':False,'crown':True,'neck_flower':True,'hairpin':False,'ribbon_turns':1.45,'ribbon_slope':.60,
 'observations':['Very long light pearl/ash-blonde hair fans to image-left','Heavy sweeping fringe covers image-left eye; other eye cyan','Small white/silver pointed crown above image-right temple','Segmented cyan halo behind head','White dress with blue-lined wide billowing skirt and high front opening','Bare arms, white neck flower and pale floral bouquet','Cyan ribbon sweeps around skirt'],
 'new_interpretations':['Rear hair volume and separated locks','Crown back and interior','Rear bodice fastening and skirt radial construction','Bouquet back and handle','Neutral centered rest posture adapted for semantic rig','All side/back silhouettes']
 }]
for p in presets:
 p['schema']='riverstone.reference_character.preset.v1';p['reference_sha256']=hashlib.sha256((ROOT/p['reference_file']).read_bytes()).hexdigest();p['source_view']='single stylized full-body front illustration';p['art_acceptance']='pending user visual review';write(ROOT/'data/presets'/(p['id']+'.json'),p)
write(ROOT/'data/design.json',{'schema':'riverstone.reference_character.observation.v1','source_viewed':True,'coordinate_mapping':'The comparison camera is on +Z; image-right maps to +X in this fixed front review. Anatomical semantic part names retain the existing common rig convention. Images remain unmodified.','rules_file':'data/rules.json','presets':[{'id':p['id'],'image':p['reference_file'],'sha256':p['reference_sha256'],'observations':p['observations'],'new_interpretations':p['new_interpretations']} for p in presets],'intent':'Two distinct adult fantasy ceremonial-dress 3D voxel interpretations; no exaggerated anatomy; source images are not model billboards.'})
