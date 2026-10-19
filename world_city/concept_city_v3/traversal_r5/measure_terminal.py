"""Measure retained initial failure against native quads and continuous source."""
import pathlib,json,math,hashlib,bisect
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[2];B=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
pack=read(B/'drawbridge_candidate/resolved_placements.json');asset=pack['assets']['stone_approaches'];render_path=ROOT/asset['render_path'];assert sha(render_path)==asset['render_sha256'];render=read(render_path);frame=pack['bridge_to_world'];basis=frame['basis'];origin=frame['translation']
def world(v):return [origin[i]+sum(basis[i][j]*v[j] for j in range(3)) for i in range(3)]
def local(v):return [sum(basis[j][i]*(v[j]-origin[j]) for j in range(3)) for i in range(3)]
faces=[];tops=[]
for group in render['groups']:
 for index,q in enumerate(group['quads']):
  lo=[min(p[k] for p in q) for k in range(3)];hi=[max(p[k] for p in q) for k in range(3)]
  if not (lo[2]<=0<=hi[2] and hi[0]>=60 and lo[0]<=72 and lo[1]>=1.2 and hi[1]<=2.1):continue
  record={'material':group['material'],'quad_index':index,'local_min':lo,'local_max':hi,'actual_quad_local_xyz_m':q,'actual_quad_world_xyz_m':[world(v) for v in q]}
  if hi[0]==lo[0] and hi[1]>lo[1]:record.update(kind='vertical_riser',rise_m=hi[1]-lo[1],full_face_width_m=hi[2]-lo[2],center_world_xyz_m=world([lo[0],(lo[1]+hi[1])/2,0]));faces.append(record)
  elif hi[1]==lo[1] and hi[0]>lo[0]:record.update(kind='native_deck_tread',run_m=hi[0]-lo[0],width_m=hi[2]-lo[2]);tops.append(record)
raw=read(H/'evidence/capsule_actual_r5_initial.json');back=next(r for r in raw['routes'] if r['id'].endswith('COUNTRY_REVERSE'));contact=back['obstacle_contact_samples'][0];lp=local(contact['position']);hit=[r for r in faces if abs(r['local_min'][0]-lp[0])<.002];assert len(hit)==1 and hit[0]['rise_m']==.25
profile_path=B/'continuous_deck_overlay.json';overlay=read(profile_path);profile=overlay['profile_x_y_m'];xx=[p[0] for p in profile]
def original(x):
 i=max(0,min(len(profile)-2,bisect.bisect_right(xx,x)-1));a,b=profile[i:i+2];return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
# The studied terminal span is before the separate outer transition regions.
for x in [62,72]:
 p=world([x,0,0])
 for t in overlay['terminal_transitions']:
  d=sum((p[k]-t['outer_center_xz_m'][j])*t['inward_unit_xz'][j] for j,k in enumerate([0,2]));assert d>t['length_m']
# Native lane tops span the complete seven-metre public corridor.
for t in tops:assert t['local_min'][2]<=-3.5 and t['local_max'][2]>=3.5
breaks=sorted(set([62,72]+[x for x in xx if 62<x<72]+[t['local_min'][0] for t in tops if 62<t['local_min'][0]<72]));samples=[]
for x in breaks:
 for offset in [-1e-8,0,1e-8]:
  u=x+offset
  if not 62<=u<=72:continue
  native=max(t['local_min'][1] for t in tops if t['local_min'][0]-1e-12<=u<=t['local_max'][0]+1e-12);samples.append({'bridge_x_m':u,'native_y_m':native,'continuous_source_y_m':original(u),'source_minus_native_m':original(u)-native})
result={'schema':'riverstone.r5.native_southern_terminal_diagnosis.v1','failure_seal':ref(H/'freeze_initial.json'),'inputs':{'native_pack':ref(B/'drawbridge_candidate/resolved_placements.json'),'native_render':ref(render_path),'continuous_source':ref(profile_path),'continuous_author':ref(B/'compile_bridge.py'),'drawbridge_author':ref(B/'drawbridge_candidate/author.py')},'actual_pitch_m':asset['pitch_m'],'classification':'Coarse 0.25 m common sampling of the continuous shared bridge deck profile. This is the natural road deck cap, not an authored pedestrian stair flight.','classification_source':'compile_bridge.py shared_deck continuous_cap_* extrusions use profile_x_y_m; drawbridge author make_fixed copies assembly_source and only changes the central opening/hinge area.','blocking_contact':{'world_xyz_m':contact['position'],'bridge_local_xyz_m':lp,'capsule_center_world':contact['capsule_center'],'lower_feet_floor_y_m':1.25,'upper_tread_y_m':1.5,'contact_count':back['obstacle_contact_ids']['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'],'native_face':hit[0]},'native_risers':faces,'native_treads':tops,'source_alignment':{'sample_count':len(samples),'maximum_measured_absolute_source_native_difference_m':max(abs(s['source_minus_native_m']) for s in samples),'native_terminal_y_m':1.25,'continuous_source_terminal_y_m':original(72),'terminal_source_minus_country_road_m':original(72)-1.25,'source_y_at_x62_m':original(62),'source_y_at_x64_m':original(64),'samples':samples},'proposal_only':{'scope':'Finite 7 m public corridor over the terminal source deck, with exact endpoint seams to existing native landing and SOUTH_COUNTRY_ROAD. Source/profile correction must be an explicit new collision adapter; no existing geometry or controller changed.','preferred_basis':'Existing continuous shared deck source, with an explicitly measured finite end blend to the quantized Y1.25 country-road anchor. Do not install the unmodified analytical profile: it misses that seam by 57.904 mm.','candidate_extent_local_xz_m':[62,-3.5,72,3.5],'area_m2':70,'limits':['Extent is a proposal, not a validated replacement. The exact starting seam, end blend, maximum gradient and source-versus-native displacement require proof before activation.','Replace only road-cap top/riser collision within the declared corridor; preserve native parapets, structural bodies, openings and actual authored stairs. Avoid duplicate blocking native risers under a new proxy.','Keep the existing visuals and failure baseline separately bound; explain any finite visual/physical discrepancy. Never span an unsupported void or place a free floating ramp.','Outbound source-hint spawn issue also needs a separate fixture revision bound to the actual initial deck level.']}}
out=H/'evidence/native_terminal_measurement.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'blocking_local':lp,'face_rise':hit[0]['rise_m'],'face_width':hit[0]['full_face_width_m'],'source_native_delta_max':result['source_alignment']['maximum_measured_absolute_source_native_difference_m'],'terminal_alignment_delta':original(72)-1.25,'report_sha256':sha(out)},indent=2))
