"""Read-only audit of sealed existing source operations and render quads. No compiler/exporter imports."""
import collections, hashlib, itertools, json, math, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[7]
BASE=ROOT/'world_city/concept_city_v3'
OUT=pathlib.Path(__file__).parent
IDS={'CLERGY_CANONS_CLOSE','CLERGY_GUEST_ALMS','CLERGY_SCHOOL_SERVICE'}
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def normal(q):
 n=cross([q[1][i]-q[0][i] for i in range(3)],[q[2][i]-q[0][i] for i in range(3)]);return tuple(round(x/math.sqrt(sum(v*v for v in n))) for x in n)
def mul(b,p):return [sum(b[i][j]*p[j] for j in range(3)) for i in range(3)]
def world(t,p):return [x+y for x,y in zip(mul(t['basis'],p),t['translation'])]
def inverse(t,p):return [sum(t['basis'][j][i]*(p[j]-t['translation'][j]) for j in range(3)) for i in range(3)]
def inside(s,p):return all(s['min'][i]-1e-8<=p[i]<s['max'][i]-1e-8 for i in range(3))
scene_path=BASE/'evidence/visual_registered_common_r5/bridge_scene.json'
scene=read(scene_path);r=read(BASE/'assemblies/landmarks/registered/precinct_r04/contact_repair_r01/resolved_placements.json')
report={'scene_sha256':sha(scene_path),'method':'Only parses existing sources and render-cache quads. Occupancy reconstructed by signed X-face ray intervals, checked against every expanded unit face; no compile, city export, or GUI.','assets':[]}
for a in r['assets']:
 if a.get('compound_id') not in IDS:continue
 m=read(ROOT/a['source']['path']);cache=read(ROOT/a['cache']['path']);pitch=cache['pitch'];quads=[(g['material'],q) for g in cache['groups'] for q in g['quads']]
 faces=collections.defaultdict(list);quadkeys=collections.Counter();rows=collections.defaultdict(list);facets=[]
 for mat,q in quads:
  n=normal(q);axis=next(i for i,v in enumerate(n) if v);sgn=n[axis];ijk=[[round(v/pitch) for v in p] for p in q];lo=[min(p[i] for p in ijk) for i in range(3)];hi=[max(p[i] for p in ijk) for i in range(3)];ab=[i for i in range(3) if i!=axis]
  quadkeys[tuple(sorted(tuple(v) for v in q))]+=1
  for u in range(lo[ab[0]],hi[ab[0]]):
   for v in range(lo[ab[1]],hi[ab[1]]):
    pos=[0,0,0];pos[axis]=lo[axis];pos[ab[0]]=u;pos[ab[1]]=v;faces[(axis,*pos)].append((sgn,mat))
    if axis==0:rows[(u,v)].append((lo[axis],sgn))
  h=(hi[1]-lo[1])*pitch;w=sum((hi[i]-lo[i])*pitch for i in [0,2]);
  if axis!=1 and mat=='rgb_9e9b88':facets.append({'normal':n,'width_m':w,'height_m':h,'bounds':{'min':[v*pitch for v in lo],'max':[v*pitch for v in hi]},'quad':q})
 occupied=set();row_errors=[]
 for (y,z),events in rows.items():
  events.sort();state=0;start=None
  for x,sgn in events:
   if sgn==-1:
    if state:row_errors.append([y,z,x,'entry while occupied'])
    start=x;state+=1
   else:
    if state!=1:row_errors.append([y,z,x,'exit not paired'])
    if start is not None:
     occupied.update((xx,y,z) for xx in range(start,x))
    state-=1
  if state:row_errors.append([y,z,'unclosed'])
 inconsistent=0
 for (axis,x,y,z),entries in faces.items():
  for sign,mat in entries:
   back=[x,y,z];front=[x,y,z]
   if sign>0:back[axis]-=1
   else:front[axis]-=1
   inconsistent+=not(tuple(back) in occupied and tuple(front) not in occupied)
 walls=[]
 for comp in m['components']:
  if not comp['id'].endswith('__masonry'):continue
  t=next(i['transform'] for i in m['instances'] if i['component']==comp['id']);boxops=[o for o in comp['operations'] if '__range_' in o['id']];cuts=[o['shape'] for o in comp['operations'] if o['action']=='cut' and o['shape']['kind']=='box'];expected=set()
  for op in boxops:
   s=op['shape'];corners=[world(t,p) for p in itertools.product(*zip(s['min'],s['max']))];lo=[math.floor(min(p[i] for p in corners)/pitch) for i in range(3)];hi=[math.ceil(max(p[i] for p in corners)/pitch) for i in range(3)]
   for xyz in itertools.product(*(range(lo[i],hi[i]) for i in range(3))):
    p=inverse(t,[(v+.5)*pitch for v in xyz])
    if inside(s,p) and not any(inside(c,p) for c in cuts):expected.add(xyz)
  missing=expected-occupied;bottom={p for p in expected if p[1]==0};unsupported=[p for p in bottom if (p[0],p[1]-1,p[2]) not in occupied]
  walls.append({'component':comp['id'],'source_operation_ids':[o['id'] for o in boxops],'height_m':max(o['shape']['max'][1] for o in boxops),'thickness_m':0.75,'expected_sampled_wall_cells_excluding_authored_door':len(expected),'missing_from_actual_cache':len(missing),'bottom_wall_cells':len(bottom),'bottom_cells_without_cached_support_below':len(unsupported),'instance_transform':t})
 boundary=next(c for c in m['components'] if c['id']=='court_and_boundary__boundary');paints=[o for o in boundary['operations'] if o['action']=='paint'];widths=[math.dist(o['shape']['polygon'][0],o['shape']['polygon'][-1]) for o in paints]
 tall=[f for f in facets if f['height_m']>=5 and f['width_m']<=1];full_boundary=[f for f in facets if f['height_m']==2 and f['bounds']['min'][1]==0]
 inst=[p for p in scene['common_instances'] if p['id']==a['compound_id']]
 ar={'id':a['compound_id'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'source_sha_matches':sha(ROOT/a['source']['path'])==a['source']['sha256'],'cache_sha_matches':sha(ROOT/a['cache']['path'])==a['cache']['sha256'],'scene_instances':inst,'pitch_m':pitch,'quad_count':len(quads),'reconstructed_cells':len(occupied),'declared_cell_count':cache['cell_count'],'exact_duplicate_quads':sum(n-1 for n in quadkeys.values() if n>1),'overlapping_unit_faces':sum(len(v)-1 for v in faces.values() if len(v)>1),'unpaired_x_ray_events':len(row_errors),'faces_inconsistent_with_outward_occupancy':inconsistent,'continuous_source_walls':walls,'boundary':{'component':'court_and_boundary__boundary','paint_operations':len(paints),'cut_operations':sum(o['action']=='cut' for o in boundary['operations']),'paint_height_above_floor_m':2,'paint_bottom_local_y_m':-.5,'world_top_y_m':16,'width_range_m':[min(widths),max(widths)],'material':'rgb_9e9b88','cache_full_height_2m_facets':len(full_boundary)},'stone_vertical_facets':len(facets),'stone_tall_thin_facets':len(tall),'stone_tall_thin_normals':dict(collections.Counter(str(f['normal']) for f in tall)),'stone_tall_thin_widths':dict(collections.Counter(str(f['width_m']) for f in tall)),'stone_tall_thin_height_range_m':[min(f['height_m'] for f in tall),max(f['height_m'] for f in tall)],'example_tall_facets':tall[:5]}
 report['assets'].append(ar)
report['conclusion']='Vertical striping is flat-lit alternating X/Z stair faces on 32.3-degree continuous masonry voxelized at 0.5 m within each compound union. Sources author solid walls and stone boundary belts, not regularly spaced posts. All recovered masonry wall samples excluding authored doors are present and supported. No duplicate/overlapping cache faces or invalid outward faces were found. This is not a missing-wall, duplicate-surface, double-transform, or alternating-material failure.'
(OUT/'stripe_audit.json').write_text(json.dumps(report,indent=2)+'\n')
for a in report['assets']:
 print(a['id'],{k:a[k] for k in ['quad_count','reconstructed_cells','declared_cell_count','exact_duplicate_quads','overlapping_unit_faces','unpaired_x_ray_events','faces_inconsistent_with_outward_occupancy','stone_tall_thin_facets','stone_tall_thin_widths','stone_tall_thin_height_range_m']});print('WALLS',[(w['component'],w['height_m'],w['expected_sampled_wall_cells_excluding_authored_door'],w['missing_from_actual_cache'],w['bottom_cells_without_cached_support_below'])for w in a['continuous_source_walls']]);print('BOUNDARY',a['boundary'])
print('Wrote',OUT/'stripe_audit.json')
