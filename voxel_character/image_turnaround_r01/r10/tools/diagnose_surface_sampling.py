"""Freeze continuous master and thickness; diagnose cell sampling only."""
from regularized_surface import *

def run():
 m,c=verify_measurement(ROOT/'generated/measured/measurements.json.gz');master=gzread(SURFACE/'generated/master.json.gz');tests=[]
 for name,pitch,origin in [('nominal',.025,[0,0,0]),('same_pitch_half_cell_origin',.025,[.0125,.0125,.0125]),('local_region_half_pitch',.0125,[0,0,0])]:
  dm=copy.deepcopy(master);dm['grid_origin']=origin;t=time.monotonic();cc=compile_master(dm,{'pitch':pitch},max_candidate_cells=350000,max_output_cells=20000);r=make_render_data(cc);metrics,_=projections(r,m,c);tests.append({'name':name,'pitch_m':pitch,'grid_origin':origin,'continuous_operations_sha256':digest(dm['components']),'operations_exactly_unchanged':dm['components']==master['components'],'normal_thickness_m':.025,'cells':len(cc['cells']),'candidates':cc['candidate_cells'],'wall_seconds':time.monotonic()-t,'structure':components(cc['cells']),'projection_metrics':metrics,'note':'diagnostic only; no pass selected by changing pitch or origin, no deletion/fill'})
  if pitch==.0125:gzwrite(SURFACE/'evidence/diagnostic_half_pitch.cells.json.gz',cc)
 # Export the actual pre-voxel primitive exterior quads for direct CPU inspection.
 groups={}
 for op in master['components'][0]['operations']:
  sh=op['shape'];poly=sh['polygon'];t=transform(op['transform']);low=[apply(t,[*p,sh['z_min']]) for p in poly];high=[apply(t,[*p,sh['z_max']]) for p in poly];quads=[list(reversed(low)),high]
  for i in range(len(poly)):j=(i+1)%len(poly);quads.append([low[i],low[j],high[j],high[i]])
  groups.setdefault(op['material'],[]).extend(quads)
 continuous={'materials':master['materials'],'groups':[{'material':k,'quads':v} for k,v in sorted(groups.items())]};gzwrite(SURFACE/'generated/continuous_primitives.render.json.gz',continuous);pts=np.array([p for group in continuous['groups'] for q in group['quads'] for p in q]);center=(pts.min(0)+pts.max(0))/2;span=float(max(pts.max(0)-pts.min(0))*1.4);files=[]
 for name,yaw,pitch in [('front',0,0),('three_quarter',45,15),('side',90,0),('back',180,0)]:
  im=raster(continuous,math.radians(yaw),math.radians(pitch),center,span,size=384);d=ImageDraw.Draw(im);d.rectangle((0,0,384,25),fill='white');d.text((6,8),name+' / continuous 25mm primitive surface',fill='black');im.save(SURFACE/'generated'/f'continuous_{name}.png');files.append({'path':f'generated/continuous_{name}.png','sha256':sha(SURFACE/'generated'/f'continuous_{name}.png')})
 write(SURFACE/'evidence/sampling_diagnosis.json',{'frozen_master_sha256':sha(SURFACE/'generated/master.json.gz'),'tests':tests,'renderer_sha256':sha(CPU_SOURCE),'continuous_exporter_sha256':sha(__file__),'continuous_images':files,'limits':'Primitive outer surfaces include internal overlap faces; no primitive modification or post-voxel repair. This diagnoses voxel sampling, not missing semantic fold depth or view inconsistency.'});print(json.dumps({'tests':[{k:t[k] for k in ['name','cells','structure','wall_seconds']} for t in tests],'disk_bytes':budget()}))
if __name__=='__main__':run()
