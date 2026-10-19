"""Bounded direct entry to the actual north water-junction public field."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex,ActualNative
from .refit_held_private_entries import PublicField,route_intervals,rows
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
import math,copy
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/riverstone-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
OUT=g.HERE/'b05_native_junction_entry_r01'
FIELDS=g.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json'
LAYOUT=a.HERE/'contour_bulk_r01/effective_source_layout_r03.json'

def run():
 OUT.mkdir(exist_ok=True);layout=g.load(LAYOUT);h=next(h for h in layout['holdings']if h['id']=='BLOCK_005:R8_C006');gate=h['gate_position_xz_m'];floor=h['floor_y_m'];f=next(f for f in g.load(FIELDS)['profiles']if f['id']=='NORTH_SHARED_JUNCTION');print('tri',str(f['triangles'][0])[:400],flush=True)
 publicrows=public_domain.records()+rows([g.geo.road_ribbon(x,y,r['width_m']) for r in g.load(g.CITY/'registered_source/plan.json')['roads'] for x,y in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])],'CANONICAL_TRAFFIC')+rows(f['polygons_xz_m'],'NORTH_SHARED_JUNCTION');pub=MaskIndex(publicrows);junction=MaskIndex(rows(f['polygons_xz_m'],'NORTH_SHARED_JUNCTION'));court=MaskIndex([dict(id=h['id'],polygon_xz_m=h['holding_polygon_xz_m'])]);selected=[]
 for w in [3.5,2.]:
  for xx in g.np.arange(66,84.1,.5):
   for zz in g.np.arange(-308,-295.9,.5):
    end=[float(xx),float(zz)]
    if not any(g.geo.point_in_convex_polygon(end,p,1e-8) for p in f['polygons_xz_m']):continue
    line=[gate,end];length=math.dist(*line)
    if length>15 or length<2:continue
    ps=g.ribbons(line,w);pi=route_intervals(line,w,pub);ci=route_intervals(line,w,court);first=min((r['station_range_m'][0]for r in pi),default=length);last=max((r['station_range_m'][1]for r in ci),default=0.);run=first-last;rise=15.6-floor
    if run<.001:continue
    screen=rise/run
    if screen<=5:selected.append(dict(width_m=w,polyline_xz_m=line,polygons_xz_m=ps,first_public_station_m=first,last_flat_station_m=last,private_rise_length_m=run,source_average_rise_screen=screen,length_m=length,public_contacts=pi))
 fig,ax=plt.subplots(figsize=(10,10));ax.add_collection(PolyCollection([r['polygon_xz_m']for r in publicrows],facecolors='#ddd',edgecolors='none'));ax.add_collection(PolyCollection(f['polygons_xz_m'],facecolors='#aaf',edgecolors='none'));ax.add_collection(PolyCollection([h['holding_polygon_xz_m']],facecolors='#ffe4b5',alpha=.5));ax.add_collection(PolyCollection(h['core_court_polygons_xz_m'],facecolors='#afa',alpha=.5));mf=g.load(g.HERE/'effective_city_manifest_r01.json');ax.add_collection(PolyCollection([q for p in mf['placements']if p.get('holding_id')==h['id']for q in p['native_walking_obstacles_xz_m']],facecolors='#654',edgecolors='none'));ax.plot(*gate,'ro');ax.set_xlim(55,100);ax.set_ylim(-285,-340);ax.grid();ax.set_aspect('equal');fig.savefig(OUT/'local_plan.png');plt.close(fig)
 selected.sort(key=lambda r:(r['width_m']<3.5,r['source_average_rise_screen'],r['length_m']));g.write(OUT/'search_diagnostic.json',dict(holding_id=h['id'],gate=gate,floor_y_m=floor,public_field=g.ref(FIELDS),candidates=selected));print('selected',len(selected),[{k:v for k,v in s.items()if k not in ['polygons_xz_m','public_contacts']}for s in selected[:12]],flush=True)
if __name__=='__main__':run()
