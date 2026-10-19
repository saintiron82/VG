"""Fit fixed native families against shared ground envelopes and real roof/core masks."""
from . import geometry as g
from .design import HERE as SOURCE
import types
src=(SOURCE/'infill_coherent.py').read_text()
src=src.replace('allowed=eligible&~hused&~lanes','roof_used=g.raster([q for p in layout[\'placements\']for q in p[\'native_roof_polygons_xz_m\']],True);court_used=g.raster([q for h in layout[\'holdings\']for q in h[\'core_court_polygons_xz_m\']],True);allowed=eligible')
src=src.replace('if g.np.any(hm&(hused|lanes)):continue','if False:continue')
src=src.replace("n=native[key];gate=", "n=native[key];newroofmask=g.raster(g.transform(n['roof_local_polygons_xz_m'],c,yaw),True);newcourtmask=g.raster(g.transform([n['court_local_polygon_xz_m']or g.rect(-hpoly[2][0]+2,6,hpoly[2][0]-2,max(t[1]for t in hpoly)-1)],c,yaw),True)\n   if g.np.any(newroofmask&(roof_used|court_used|lanes))or g.np.any(newcourtmask&roof_used):continue\n   gate=")
src=src.replace('if not ev:continue',"if not ev:continue\n   if any(abs(oh['floor_y_m']-ev['y_m'])>1e-6 and g.geo.intersection_area(hp,oh['holding_polygon_xz_m'])>1e-6 for oh in layout['holdings']):continue")
src=src.replace('retired|=ids;hused|=hm;lanes|=rm;free&=~hm',"retired|=ids;hused|=hm;lanes|=rm;obstacles|=g.raster(walk,True);roof_used|=newroofmask;court_used|=newcourtmask")
mod=types.ModuleType(__package__+'.shared_infill_engine');mod.__package__=__package__;exec(compile(src,str(SOURCE/'shared_infill.py'),'exec'),mod.__dict__)
if __name__=='__main__':mod.run()
