"""Reuse existing native poor-row cache modules in bounded shared-court gaps."""
from . import geometry as g
from .design import HERE as SOURCE
import types
out=SOURCE/'coherent_regrade_r01/BLOCK_018';registry=g.load(out/'native_local.json');scene=g.load(g.R7);text=(SOURCE/'native.py').read_text().replace("for mod in m.get('metadata',{}).get('modules',[]):", "for mod in (m.get('metadata',{}).get('modules',[])or[dict(id='native_row',translation_m=[0,0,0],metadata=m['metadata'],params=dict(style=m['metadata']['style']))]):")
nm=types.ModuleType(__package__+'.native_existing_row');nm.__package__=__package__;exec(compile(text,str(SOURCE/'native.py'),'exec'),nm.__dict__)
keys=['ordinary_r2_90e94fbcf2d1b7','ordinary_r2_239aa05a186005']
for key in keys:
 a=g.copy.deepcopy(scene['common_assets'][key]);a['native_metadata']=dict(palette='wood_brown',role='Existing native attached poor-row lodging and household repair return',reused_exact_R7_cache=True);n=nm.local_for(key,a);n['court_local_polygon_xz_m']=g.rect(-4,5.5,4,10);registry['assets'][key]=n;print(key,n['roof_area_m2'],len(n['doors']),flush=True)
g.write(out/'native_local.json',registry)
# Use the same target-driven shared-envelope fitter, now with the two existing
# small attached-row modules. Source/cache bytes and palette semantics stay fixed.
text=(SOURCE/'shared_infill.py').read_text().replace("src=(SOURCE/'infill_coherent.py').read_text()", "src=(SOURCE/'infill_coherent.py').read_text().replace(\"g.load(SOURCE/'native_local.json')['assets']\",\"g.load(SOURCE/'coherent_regrade_r01/BLOCK_018/native_local.json')['assets']\").replace(\"families=[\",\"families=[('ordinary_r2_90e94fbcf2d1b7',g.rect(-5.75,-5.75,5.75,10.75)),('ordinary_r2_239aa05a186005',g.rect(-6.75,-5.75,6.75,10.75)),\")")
text=text.replace("if __name__=='__main__':mod.run()",'')
mod=types.ModuleType(__package__+'.complete_b18_engine');mod.__package__=__package__;exec(compile(text,str(SOURCE/'shared_infill.py'),'exec'),mod.__dict__);mod.mod.run()
l=g.load(out/'selected_layout.json');l['native_local']=g.ref(out/'native_local.json');g.write(out/'selected_layout.json',l)
