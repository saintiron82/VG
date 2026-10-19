"""Reuse unchanged pixel measurements for an explicit display-thickness test.
No boundary, centerline, fitted curve, image mask or source pixel is edited.
"""
import copy,json,numpy as np
from scipy import ndimage as ndi
from measured_cloth import ROOT,COMMON,read,write,sha,gzread,build,compile_master,make_render_data,budget

def topology(c):
 ps=np.array([r[:3] for r in c['cells']]);lo=ps.min(0)-1;grid=np.zeros(tuple(ps.max(0)-lo+2),bool);grid[tuple((ps-lo).T)]=True;l,n=ndi.label(grid);return {'six_connected_components':int(n),'component_sizes_cells':sorted(np.bincount(l.ravel())[1:].tolist(),reverse=True),'enclosed_empty_cells':int((ndi.binary_fill_holes(grid)&~grid).sum())}

def run():
 original=read(ROOT/'data/region_contract.json');c=copy.deepcopy(original);c['region']['thickness_m']=.05;c['region']['thickness_status']='50 mm explicit coarse-grid display thickness test; not measured cloth, no changes to pixel-derived middle surface';cp=ROOT/'data/region_contract_50mm.json';write(cp,c)
 for k in ['views','alignment','mask']:assert c[k]==original[k]
 newpaths=[]
 for suffix,old in [('measured_50mm','measured'),('mutated_measurement_50mm','mutated_measurement')]:
  oldpath=ROOT/'generated'/old/'measurements.json';m=read(oldpath);m['contract_path']=str(cp.resolve());m['contract_sha256']=sha(cp);m['measurement_reuse']={'original_measurement_sha256':sha(oldpath),'reason':'only display-thickness prior changed; view/alignment/mask/section sampling inputs exactly equal; all measured samples reused byte-equivalently'};p=ROOT/'generated'/suffix;p.mkdir(exist_ok=False);write(p/'measurements.json',m);assert m['sections']==read(oldpath)['sections'];newpaths.append(p/'measurements.json')
 build(newpaths[0],ROOT/'generated/region_50mm');build(newpaths[1],ROOT/'generated/mutated_region_50mm');co=gzread(ROOT/'generated/region_50mm/compiled.cells.json.gz');mu=gzread(ROOT/'generated/mutated_region_50mm/compiled.cells.json.gz');master=gzread(ROOT/'generated/region_50mm/master.json.gz');oldmaster=gzread(ROOT/'generated/region/master.json.gz')
 for a,b in zip(master['components'][0]['operations'],oldmaster['components'][0]['operations']):
  aa=copy.deepcopy(a);bb=copy.deepcopy(b)
  for q in [aa,bb]:q['shape'].pop('z_min');q['shape'].pop('z_max')
  assert aa==bb
 re=compile_master(master,{'pitch':.025},max_candidate_cells=600000,max_output_cells=50000);assert re==co
 saved_render=gzread(ROOT/'generated/region_50mm/region.render.json.gz');rr=make_render_data(re);rr['frame']=saved_render['frame'];assert rr==saved_render
 a={tuple(x[:3]) for x in co['cells']};b={tuple(x[:3]) for x in mu['cells']};delta=a^b;ys=[(p[1]+.5)*.025 for p in delta];assert min(ys)>=.35 and max(ys)<=.50
 report={'same_measured_samples':True,'same_middle_surface_and_operations_except_thickness':True,'independent_common_compile_exact':True,'independent_common_mesh_exact':True,'previous_25mm_topology':topology(gzread(ROOT/'generated/region/compiled.cells.json.gz')),'new_50mm_topology':topology(co),'local_pixel_mutation_occupancy_delta_cells':len(delta),'local_pixel_mutation_y_range_m':[min(ys),max(ys)],'locality_pass':True,'prior_status':'Thickness is explicit display assumption, not an image measurement or source-shape fit. All failed 25mm outputs preserved.','new_contract_sha256':sha(cp),'compiler_sha256':sha(COMMON/'core.py'),'test_code_sha256':sha(__file__),'art_approval':False}
 write(ROOT/'evidence/thickness_prior_test.json',report);print(json.dumps(report));budget()
if __name__=='__main__':run()
