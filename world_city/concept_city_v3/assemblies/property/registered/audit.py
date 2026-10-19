"""Read-only source audit and labelled 2D proxy drawings. Never a 3D approval."""
import itertools,json,math
from pathlib import Path
from . import author as a
from voxel_character.common import core,coordinate_planes
from world_city.concept_city_v3.registered_topography.author import project
HERE=a.HERE;OUT=HERE/'generated'

def candidate_budget(master,pitch=.5):
 numeric,_=coordinate_planes.resolve_master(master,{'pitch':pitch});components,instances=core.validate_master(numeric,pitch);transforms={}
 def transform_for(key):
  if key in transforms:return transforms[key]
  v=instances[key];t=core.transform(v.get('transform'))
  if v.get('parent'):t=core.compose(transform_for(v['parent']),t)
  transforms[key]=t;return t
 candidates=0;lo=[math.inf]*3;hi=[-math.inf]*3
 for key,v in instances.items():
  for op in components[v['component']]['operations']:
   shape=core.prepare_shape(op['shape'],pitch);bounds=core.shape_bounds(shape);t=core.compose(transform_for(key),core.transform(op.get('transform')));corners=[core.apply(t,p) for p in itertools.product(*zip(*bounds))];low=[min(p[i] for p in corners) for i in range(3)];high=[max(p[i] for p in corners) for i in range(3)]
   candidates+=math.prod(max(0,math.ceil((high[i]-numeric.get('grid_origin',[0,0,0])[i])/pitch-core.EPS)-math.floor((low[i]-numeric.get('grid_origin',[0,0,0])[i])/pitch+core.EPS)) for i in range(3))
   if op['action']=='paint':
    lo=[min(lo[i],low[i]) for i in range(3)];hi=[max(hi[i],high[i]) for i in range(3)]
 return dict(pitch_m=pitch,exact_candidate_visits_without_cell_sampling=candidates,operation_bounds=dict(min=lo,max=hi),candidate_cap=300000,output_cap=100000,within_candidate_cap=candidates<=300000,occupied_cells=None,sampled=False)

OBSERVATIONS={
 'E1':'Small visible slate-roof residence beside the castle; its west property edge is partly occluded. Rear service and garden division are design inference.',
 'E2':'Prominent slate-roof residence with subsidiary volumes and enclosed green area. The image supports a court ensemble; exact wing count and property division are inferred.',
 'E3':'Northern roof/garden grouping is tree-occluded and visually ambiguous with E6. An independently measured E3 house footprint cannot be recovered from this single view.',
 'E4':'Broad, prominent mineral/plaster residence above the west lane, with garden to its rear and a large walled terrace. The 26m main module alone under-expresses the apparent frontage.',
 'E5':'Visible red-roof small residence near the east edge of a broad green enclosure. The side-palace and rear-wing arrangement is an authored interpretation, not a traced plan.',
 'E6':'Formal garden and stone wall are clear; the associated roof overlaps the northern E3 grouping. An east-facing hall keeps the central garden open without claiming an observed exact floor plan.',
 'E7':'Lower wedge-shaped enclosure with a small roof grouping, green court and gateway toward the contour lane. Timber construction and exact service positions are authored social-character choices.'}

def run():
 pack=json.loads((OUT/'pack.json').read_text());recipes=[json.loads((OUT/(pid+'.recipe.json')).read_text()) for pid in a.IDS];old=json.loads((a.CITY/'source/plan.json').read_text());oldn=[p for p in old['plots'] if p['id'] in ['P_NOBLE_01','P_NOBLE_02','P_NOBLE_03','P_NOBLE_04','P_NOBLE_06','P_NOBLE_07','P_NOBLE_08']]
 oldc=a.centre([p['origin_xz_m'] for p in oldn]);newc=a.centre([a.centre(r['plot']['polygon_xz_m']) for r in recipes]);entries=[]
 for r in recipes:
  houses=[p for p in r['placements'] if p['source_provider']=='ordinary_r2'];main=next(p for p in houses if p['role']=='main');vs=[q for p in houses for q in p['footprint_xz_m']];m=main['local_bounds'];main_width=m['max'][0]-m['min'][0];main_depth=m['max'][2]-m['min'][2]
  entries.append(dict(id=r['id'],visible_image_observation=OBSERVATIONS[r['id']],directly_observed=['relative district location','visible roof and enclosure silhouette','garden/service-court relationship where unoccluded'],inferred_not_measured=['absolute metre dimensions','bench and storey heights','main-house assignment at occluded parcel seams','building material/type assignment','door locations and wing counts'],refined_trace_area_m2=r['metrics']['plot_area_m2'],old_rectangular_parcel_area_m2=4340,area_ratio_to_old=r['metrics']['plot_area_m2']/4340,native_main_module_dimensions_m=[main_width,main_depth,m['max'][1]],actual_peak_above_finished_floor_m=m['max'][1]-main['door_local_y_m'],main_module_footprint_fraction=main_width*main_depth/r['metrics']['plot_area_m2'],ensemble_bounds_xz_m=[min(p[0] for p in vs),min(p[1] for p in vs),max(p[0] for p in vs),max(p[1] for p in vs)],metrics=r['metrics'],composition=r['composition_intent'],maximum_bounded_fit_adjustment_m=max(p['fit_adjustment_m'] for p in r['placements']),reference_uncertainty='No calibrated metric height/footprint recovery is claimed from the oblique generated painting.'))
 budget=[]
 for asset,record in pack['asset_manifest'].items():
  if record['status']=='persisted_compiled_reuse':continue
  b=candidate_budget(a.frozen.make_asset_master(record['cache_spec']),record['resource']['pitch']);budget.append(dict(asset_key=asset,source_status=record['status'],**b))
 for r in recipes:
  master=json.loads((OUT/(r['id']+'.infrastructure.master.json')).read_text());budget.append(dict(asset_key=master['id'],source_status='new_property_wrapper',**candidate_budget(master)))
 report=dict(schema='riverstone.registered_property.image_audit.v1',source_sha256=pack['registered_source_sha256'],images_actually_inspected=['world_city/reference/revision_03/city_social_water_concept.png','world_city/concept_city_v3/image_registration/current_vs_target_controls.png'],observed_result='The original noble recipes are shifted south-west and repeated too mechanically; traced estates are irregular, deeper/narrower, and only some are larger.',old_estate_centroid_xz_m=oldc,registered_estate_centroid_xz_m=newc,centroid_change_xz_m=[newc[i]-oldc[i] for i in (0,1)],camera_registration_limit='58.6px anchor RMS, single-view painting; metric sizes are design hypotheses.',estates=entries,budget=pack['budget'],source_only_candidate_budget=budget,maximum_proposed_candidate_visits=max(b['exact_candidate_visits_without_cell_sampling'] for b in budget),compile_performed=False,actual_registered_scene_viewed=False)
 (OUT/'image_audit.json').write_text(json.dumps(report,indent=2)+'\n')
 # Labelled world plan: this is a new vector source diagram, not an edited image.
 colors={'main':'#cbb996','stable':'#8d6e46','servants':'#bba986'};svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1040" viewBox="-255 -355 285 305">','<rect x="-255" y="-355" width="285" height="305" fill="#f2efe3"/>']
 def polygon(p,fill,stroke='#333',sw=.25):return '<polygon points="'+' '.join(f'{x:.4f},{z:.4f}' for x,z in p)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
 for r in recipes:
  svg.append(polygon(r['plot']['polygon_xz_m'],'#d7dfbf','#514a3d',.7))
  for reg in r['ground_regions']:svg.append(polygon(reg['polygon_xz_m'],'#9fb96e' if 'garden' in reg['land_use'] else '#bbb1a0','none'))
  for p in r['placements']:svg.append(polygon(p['footprint_xz_m'], '#466841' if p['role'].startswith('orchard') else '#707f44' if p['role'].startswith('garden') else colors.get(p['role'],'#a6a4ad')))
  for path in r['entrance_routes']:
   svg.append('<polyline points="'+' '.join(f'{x:.4f},{z:.4f}' for x,z in path['polyline_xz_m'])+'" stroke="#e6d8aa" stroke-width="1.1" fill="none"/>')
  g=r['gates'][0];x,z=g['center_xz_m'];svg.append(f'<circle cx="{x}" cy="{z}" r="1.6" fill="#bb543f"/>')
  x,z=r['origin_xz_m'];svg.append(f'<text x="{x}" y="{z-2}" font-size="4.2" text-anchor="middle" font-family="sans-serif" fill="#172020">{r["id"]}</text>')
 svg.append('<text x="-250" y="-60" font-size="4" font-family="sans-serif">SOURCE PLAN ONLY | native modules | gates await grade audit</text></svg>');(OUT/'estate_source_plan.svg').write_text('\n'.join(svg))
 return report
if __name__=='__main__':print(json.dumps({'max_candidates':run()['maximum_proposed_candidate_visits']},indent=2))
