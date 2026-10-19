"""Approval-gated, source-only property instancing. Frozen recipes stay unchanged."""
from __future__ import annotations
import copy, hashlib, json, math
from collections import Counter
from pathlib import Path
from . import recipes
HERE=Path(__file__).parent
TOKEN='PROPERTY_TEMPLATE'
EXTERNAL_PATH_KINDS={'property_gate_link','recipe_external_frontage_link'}
INTERNAL_PATH_KINDS={'recipe_actual_door_link','recipe_garden_path','cross_courtyard','door_link','property_internal_access'}


def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
class SourcePlanSnapshot(dict):
    """Parsed mapping bound to its exact file bytes and original content digest."""
    def __init__(self,data,file_sha256):
        super().__init__(data);self.file_sha256=file_sha256;self.parsed_sha256=sha(data)

def read_source_plan(path):
    data=Path(path).read_bytes();h=hashlib.sha256(data).hexdigest();return SourcePlanSnapshot(json.loads(data),h),h
def geometry_hash(plot):
    fields=('property_type','width_m','depth_m','origin_xz_m','yaw_rad','polygon_xz_m','gate_front','gate_position_xz_m','gate_connection_xz_m','road_id','variant')
    return sha({k:plot[k] for k in fields if k in plot})
def same_polygon(a,b,tolerance=.01):
    return len(a)==len(b) and any(all(math.dist(a[i],c[(i+offset)%len(c)])<=tolerance for i in range(len(a))) for c in (b,list(reversed(b))) for offset in range(len(b)))
def _variant(plot):
    tail=plot['id'].rsplit('_',1)[-1];return int(plot.get('variant',int(tail)-1 if tail.isdigit() else 0))
def _ids(value,pid):
    if isinstance(value,str):return pid+value[len(TOKEN):] if value==TOKEN or value.startswith(TOKEN+':') else value
    if isinstance(value,list):return [_ids(x,pid) for x in value]
    if isinstance(value,dict):return {k:_ids(v,pid) for k,v in value.items()}
    return value


class PropertyResolver:
    """Caches local source templates and common-master sources, never compiles them."""
    def __init__(self):
        freeze=json.loads((HERE/'freeze_manifest.json').read_text())
        actual=hashlib.sha256((HERE/'recipes.py').read_bytes()).hexdigest()
        if actual!=freeze['source_sha256']:raise ValueError('Frozen recipe source changed')
        for path,expected in freeze['external_dependencies_sha256'].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen master dependency changed: '+path)
        self.recipe_source_sha256=actual
        catalog=HERE/'generated/cache_catalog.json'
        if hashlib.sha256(catalog.read_bytes()).hexdigest()!=freeze['all_files_sha256']['generated/cache_catalog.json']:raise ValueError('Frozen asset catalog changed')
        self.allowed_assets=json.loads(catalog.read_text())['assets']
        self.templates={};self.sources={};self.template_build_count=0;self.source_build_count=0

    def _template(self,plot):
        kind=plot['property_type'];v=_variant(plot);shape_variant=v%3 if kind=='noble_estate' else v%2 if kind=='poor_block' else 0
        key=(kind,float(plot['width_m']),float(plot['depth_m']),shape_variant)
        if key not in self.templates:
            local=recipes.example_plot(kind,shape_variant);local.update(id=TOKEN,width_m=key[1],depth_m=key[2]);local['gate_position_xz_m']=[0,key[2]/2]
            r=recipes.build_property_recipe(local)
            if not r['checks']['valid']:raise ValueError('Invalid frozen template: '+str(r['checks']['errors']))
            if set(r['cache_specs'])-set(self.allowed_assets):raise ValueError('Template is outside the frozen 25-asset catalog')
            self.templates[key]=r;self.template_build_count+=1
        return self.templates[key]

    def _instantiate(self,plot,pad):
        r=_ids(copy.deepcopy(self._template(plot)),plot['id']);o=plot['origin_xz_m'];yaw=plot.get('yaw_rad',0);floor=pad['floor_y_m'];d=plot['depth_m']
        r['plot']=copy.deepcopy(plot);r['plot']['pad_y_m']=floor;r['resolved_variant']=_variant(plot)
        for p in r['placements']:
            local=p['local_position_m'];xz=recipes.world_point([local[0],local[2]],o,yaw);p['position_m']=[xz[0],floor,xz[1]];p['yaw_rad']=yaw+p['local_yaw_rad'];p['footprint_xz_m']=recipes.world_polygon(p['footprint_local_xz_m'],o,yaw)
            p['ground_anchor']['support_points_xz_m']=recipes.world_polygon(p['ground_anchor']['support_points_xz_m'],o,yaw);p['ground_anchor']['datum_y_m']=floor
            p['source_plot_id']=plot['id'];p['source_plot_geometry_sha256']=geometry_hash(plot);p['compound_pad_id']=pad['id']
            for e in p.get('entrances',[]):e['door_world_xz_m']=recipes.world_point(e['door_local_xz_m'],o,yaw);e['door_world_position_m']=[e['door_world_xz_m'][0],floor,e['door_world_xz_m'][1]]
        for a in r['entrance_routes']:
            a['polyline_xz_m']=recipes.world_polygon(a['polyline_local_xz_m'],o,yaw);a['ribbon_polygons_xz_m']=[recipes.world_polygon(q,o,yaw) for q in a['ribbon_polygons_local_xz_m']];a['road_id']=plot.get('road_id');a['source_plot_id']=plot['id'];a['floor_y_m']=floor
            full=a['polyline_xz_m']
            if a.get('threshold_bridge_to_actual_door_local_xz_m'):
                bridge=recipes.world_polygon(a['threshold_bridge_to_actual_door_local_xz_m'],o,yaw);a['threshold_bridge_to_actual_door_xz_m']=bridge;full=bridge[:1]+full
            a['full_polyline_xz_m']=full;a['full_polyline_position_m']=[[x,floor,z] for x,z in full]
        for g in r['gates']:
            g['position_xz_m']=recipes.world_point(g['center_local_xz_m'],o,yaw);g['public_frontage_point_xz_m']=recipes.world_point([g['center_local_xz_m'][0],d/2],o,yaw);g['floor_y_m']=floor
        for region in r['ground_regions']:region['polygon_xz_m']=recipes.world_polygon(region['polygon_local_xz_m'],o,yaw)
        r['surface_ownership']['polygon_xz_m']=recipes.world_polygon(recipes.rect([0,0],plot['width_m'],d),o,yaw);r['surface_ownership']['pad_y_m']=floor
        r['external_frontage_requirements']=[{'gate_id':g['id'],'frontage_point_xz_m':g['public_frontage_point_xz_m'],'minimum_link_width_m':3 if g['role']=='main' and plot['property_type']=='noble_estate' else 2.5 if g['role']=='service' else 1.8,'existing_main_gate_connection_xz_m':plot.get('gate_connection_xz_m') if g['role']=='main' else None,'external_connection_owner':'concept_city_v3 land-use street/path plan'} for g in r['gates']]
        r['checks']=recipes.validate_recipe(r)
        return r

    def _asset(self,key,spec,compiled):
        if key not in self.sources:
            source=recipes.make_asset_master(spec);self.sources[key]={'source':source,'sha256':sha(source)};self.source_build_count+=1
        resource=recipes.resource_for(spec);source_sha=self.sources[key]['sha256'];identity=sha({'master_source_sha256':source_sha,'sampling_resource':resource});hit=compiled.get(key)
        if hit and (not hit.get('compiled_asset_ref') or hit.get('master_source_sha256')!=source_sha or hit.get('sampling_resource')!=resource):hit=None
        return {'asset_key':key,'cache_spec':copy.deepcopy(spec),'common_schema':'riverstone.voxel.master.v1','master_source_sha256':source_sha,'sampling_resource':resource,'compile_identity':identity,'cache_status':'reuse_verified_compiled_asset' if hit else 'compile_once_required','compiled_asset_ref':hit.get('compiled_asset_ref') if hit else None}

    def source_for(self,asset_key):
        """Return one cached common-source master; caller compiles once per identity."""
        return copy.deepcopy(self.sources[asset_key]['source'])

    def resolve(self,plan,terrain_contract,approved_plot_ids,source_plan_sha256,compiled_assets=None):
        """Never infer approval, a whole-plot floor, or an irregular-plot recipe.

        Use read_source_plan() to pair parsed data with the actual JSON-file hash.
        approved_plot_ids is a review scope, not an automatic source-plan default.
        """
        if approved_plot_ids is None:raise ValueError('Explicit approved_plot_ids is required')
        approved=set(approved_plot_ids);compiled=compiled_assets or {};plots={p['id']:p for p in plan.get('plots',[])}
        if len(plots)!=len(plan.get('plots',[])):raise ValueError('Duplicate source plot IDs')
        if len(source_plan_sha256)!=64:raise ValueError('Actual source JSON SHA256 is required')
        pads={p['plot_id']:p for p in terrain_contract.get('compound_pads',[])}
        if len(pads)!=len(terrain_contract.get('compound_pads',[])):raise ValueError('Duplicate compound pad ownership')
        out={'schema':'riverstone.concept_city.property_resolution.v1','status':'source_only_not_a_full_scene','source_plan_sha256':source_plan_sha256,'source_plan_content_sha256':sha(plan),'terrain_contract_sha256':sha(terrain_contract),'recipe_source_sha256':self.recipe_source_sha256,'approved_plot_ids':sorted(approved),'resolved_properties':[],'unresolved':[],'asset_manifest':{},'unresolved_policy':'Keep original source IDs and geometry; no replacement or deletion until an explicit compatible recipe and whole-compound pad exist.','no_compilation':True,'no_scene_emission':True}
        def unresolved(pid,reason,detail=None):out['unresolved'].append({'source_plot_id':pid,'source_plot_geometry_sha256':geometry_hash(plots[pid]) if pid in plots else None,'reason':reason,'detail':detail,'replacement_ids':[],'source_preserved':True})
        mismatch=terrain_contract.get('source_plan_sha256')!=source_plan_sha256
        source_unbound=(plan.file_sha256!=source_plan_sha256 or plan.parsed_sha256!=sha(plan)) if isinstance(plan,SourcePlanSnapshot) else sha(plan)!=source_plan_sha256
        for pid in sorted(set(plots)|approved):
            if pid not in plots:unresolved(pid,'approved_plot_id_missing_from_source');continue
            plot=plots[pid]
            if pid not in approved:unresolved(pid,'not_in_explicit_approved_scope');continue
            if source_unbound:unresolved(pid,'source_mapping_not_bound_to_supplied_snapshot_hash');continue
            if mismatch:unresolved(pid,'terrain_source_snapshot_mismatch');continue
            family=plot.get('property_type')
            if family not in recipes.FAMILIES:unresolved(pid,'no_complete_recipe_for_property_type',family);continue
            try:
                w,d=float(plot['width_m']),float(plot['depth_m']);o=plot['origin_xz_m'];yaw=plot.get('yaw_rad',0);frame=recipes.world_polygon(recipes.rect([0,0],w,d),o,yaw)
                if (w,d)!=recipes.DEFAULT_SIZES[family]:unresolved(pid,'dimensions_outside_frozen_cache_catalog',[w,d]);continue
                if not same_polygon(frame,plot.get('polygon_xz_m',[])):unresolved(pid,'irregular_or_incomplete_buildable_frame');continue
                if plot.get('gate_front','+Z')!='+Z' or math.dist(plot.get('gate_position_xz_m',[]),recipes.world_point([0,d/2],o,yaw))>.05:unresolved(pid,'incompatible_gate_frame');continue
                pad=pads.get(pid)
                if not pad:unresolved(pid,'missing_whole_compound_pad');continue
                if not math.isfinite(pad['floor_y_m']):unresolved(pid,'nonfinite_pad_floor');continue
                if not same_polygon(frame,pad.get('source_plot_polygon_xz_m',[])) or not any(same_polygon(frame,q) for q in pad.get('owned_polygons_xz_m',[])):unresolved(pid,'pad_does_not_own_exact_source_plot');continue
                if math.dist(pad.get('gate_xz_m',[]),plot['gate_position_xz_m'])>.05:unresolved(pid,'pad_gate_position_mismatch');continue
                r=self._instantiate(plot,pad)
                gate_errors=[]
                for g in r['gates']:
                    ledger=[x for x in pad.get('gate_ledger',[]) if math.dist(x['xz_m'],g['public_frontage_point_xz_m'])<=.05]
                    if not ledger or any(abs(x[k]-pad['floor_y_m'])>.001 for x in ledger for k in ('threshold_y_m','landing_y_m')):gate_errors.append(g['id'])
                if gate_errors:unresolved(pid,'missing_or_nonlevel_gate_landing',gate_errors);continue
                if not r['checks']['valid']:unresolved(pid,'recipe_validation_failed',r['checks']['errors']);continue
                buildings=[b for b in plan.get('buildings',[]) if b.get('source_plot_id',b.get('plot_id'))==pid]
                paths=[p for p in plan.get('paths',[]) if p.get('owner_plot_id')==pid]
                unknown=[p['id'] for p in paths if p.get('kind') not in EXTERNAL_PATH_KINDS|INTERNAL_PATH_KINDS]
                if unknown:unresolved(pid,'unclassified_path_ownership',unknown);continue
                escaping=[p['id'] for p in paths if p.get('kind') in INTERNAL_PATH_KINDS and not recipes.convex_polygon_contains(frame,p.get('polyline_xz_m',[]),.01)]
                if escaping:unresolved(pid,'internal_path_leaves_replacement_plot',escaping);continue
                missing_links=[]
                for req in r['external_frontage_requirements']:
                    links=[p for p in paths if p.get('kind') in EXTERNAL_PATH_KINDS and p.get('road_id')==plot.get('road_id') and p.get('width_m',0)>=req['minimum_link_width_m']-.001 and len(p.get('polyline_xz_m',[]))>=2 and min(math.dist(p['polyline_xz_m'][0],req['frontage_point_xz_m']),math.dist(p['polyline_xz_m'][-1],req['frontage_point_xz_m']))<=.05]
                    if not links:missing_links.append(req['gate_id'])
                if missing_links:unresolved(pid,'missing_external_frontage_source_link',missing_links);continue
                byid={p['id']:p for p in r['placements']};proxy_mismatches=[]
                for b in buildings:
                    rid=b.get('source_recipe_placement_id')
                    if rid and (rid not in byid or b.get('asset_key')!=byid[rid]['asset_key'] or not same_polygon(b.get('footprint_xz_m',[]),byid[rid]['footprint_xz_m'])):proxy_mismatches.append(b['id'])
                if proxy_mismatches:unresolved(pid,'reviewed_recipe_proxy_geometry_mismatch',proxy_mismatches);continue
                props=[p for p in plan.get('property_placements',[]) if p.get('source_plot_id',p.get('plot_id'))==pid]
                ledger={'replace_building_ids':[p['id'] for p in buildings],'replace_internal_path_ids':[p['id'] for p in paths if p.get('kind') in INTERNAL_PATH_KINDS],'replace_property_placement_ids':[p['id'] for p in props],'preserve_external_path_ids':[p['id'] for p in paths if p.get('kind') in EXTERNAL_PATH_KINDS],'superseded_per_building_pad_ids':[p['id'] for p in terrain_contract.get('building_pads',[]) if p.get('plot_id')==pid],'add_placement_ids':[p['id'] for p in r['placements']],'add_internal_path_ids':[p['id'] for p in r['entrance_routes']],'atomic_replacement_required':True,'ownership_match':'explicit source_plot_id/plot_id; never bounding-box or prefix deletion'}
                for key,spec in r['cache_specs'].items():out['asset_manifest'].setdefault(key,self._asset(key,spec,compiled))
                record={'source_plot_id':pid,'source_plot_record_sha256':sha(plot),'source_plot_geometry_sha256':geometry_hash(plot),'source_building_geometry_sha256':sha(buildings),'recipe_template_identity':sha([family,w,d,r['resolved_variant']%(3 if family=='noble_estate' else 2 if family=='poor_block' else 1)]),'compound_pad_id':pad['id'],'compound_pad_sha256':sha(pad),'resolved_placement_geometry_sha256':sha([{k:p[k] for k in ('id','asset_key','position_m','yaw_rad','footprint_xz_m')} for p in r['placements']]),'floor_y_m':pad['floor_y_m'],'placements':r['placements'],'entrance_routes':r['entrance_routes'],'gates':r['gates'],'external_frontage_requirements':r['external_frontage_requirements'],'ground_regions':r['ground_regions'],'boundary_ownership':{'placement_id':r['boundary_placement_id'],'one_common_solid':True,'floor_y_m':pad['floor_y_m']},'surface_ownership':r['surface_ownership'],'replacement_ledger':ledger,'terrain_support_contract':{'foundation_bottom_y_m':pad.get('foundation_bottom_y_m'),'maximum_cut_m':pad.get('maximum_cut_m'),'maximum_fill_m':pad.get('maximum_fill_m'),'retaining_segments':pad.get('retaining_segments',[]),'retaining_tier_policy':pad.get('retaining_tier_policy'),'gate_ledger':pad['gate_ledger'],'external_apron_owned_polygons_xz_m':[q for q in pad['owned_polygons_xz_m'] if not same_polygon(frame,q)],'visible_support_geometry_required_before_runtime_acceptance':bool(pad.get('retaining_segments'))},'checks':r['checks']}
                out['resolved_properties'].append(record)
            except (KeyError,ValueError,TypeError,IndexError) as error:unresolved(pid,'malformed_or_incompatible_source_record',str(error))
        out['summary']={'resolved_plots':len(out['resolved_properties']),'unresolved_plots':len(out['unresolved']),'unresolved_reasons':dict(Counter(p['reason'] for p in out['unresolved'])),'instanced_placements':sum(len(r['placements']) for r in out['resolved_properties']),'unique_assets':len(out['asset_manifest']),'cache_templates_built':self.template_build_count,'common_sources_built':self.source_build_count,'per_plot_compile_count':0}
        return out
