"""Bounded fixtures only. No full city resolution or compilation."""
import copy,json,math,unittest
from unittest.mock import patch
from .resolver import *


def fixture(family='noble_estate',pid='P_TEST_01',variant=0,origin=(0,0),yaw=0,floor=7):
    p=recipes.example_plot(family,variant);p.update(id=pid,origin_xz_m=list(origin),yaw_rad=yaw);p['polygon_xz_m']=recipes.world_polygon(recipes.rect([0,0],p['width_m'],p['depth_m']),origin,yaw);p['gate_position_xz_m']=recipes.world_point([0,p['depth_m']/2],origin,yaw)
    direct=recipes.build_property_recipe({**p,'pad_y_m':floor});paths=[]
    for g,req in zip(direct['gates'],direct['external_frontage_requirements']):
        point=g['public_frontage_point_xz_m'];outside=[point[0]+math.sin(yaw)*4,point[1]+math.cos(yaw)*4]
        paths.append({'id':g['id']+':EXTERNAL','kind':'recipe_external_frontage_link','owner_plot_id':pid,'polyline_xz_m':[point,outside],'road_id':p['road_id'],'width_m':req['minimum_link_width_m']})
    paths.extend({'id':a['id'],'kind':'recipe_garden_path' if a.get('kind')=='garden_service_walk' else 'recipe_actual_door_link','owner_plot_id':pid,'polyline_xz_m':a['polyline_xz_m'],'width_m':a['width_m']} for a in direct['entrance_routes'])
    buildings=[{'id':q['id'],'plot_id':pid,'source_plot_id':pid,'source_recipe_placement_id':q['id'],'asset_key':q['asset_key'],'footprint_xz_m':q['footprint_xz_m']} for q in direct['placements'] if q['source_provider']=='ordinary_r2']
    pad={'id':pid+':PAD','plot_id':pid,'floor_y_m':floor,'source_plot_polygon_xz_m':p['polygon_xz_m'],'owned_polygons_xz_m':[p['polygon_xz_m']],'gate_xz_m':p['gate_position_xz_m'],'gate_ledger':[{'xz_m':g['public_frontage_point_xz_m'],'threshold_y_m':floor,'landing_y_m':floor} for g in direct['gates']]}
    return p,pad,buildings,paths,direct


def inputs(fixtures):
    plan={'plots':[f[0] for f in fixtures],'buildings':[b for f in fixtures for b in f[2]],'paths':[p for f in fixtures for p in f[3]]};h=sha(plan);terrain={'source_plan_sha256':h,'compound_pads':[f[1] for f in fixtures]};return copy.deepcopy(plan),copy.deepcopy(terrain),h


class PropertyResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures=[fixture('noble_estate','P_NOBLE_01',origin=(-180,-100),yaw=.27),fixture('noble_estate','P_NOBLE_04',origin=(80,-100),yaw=math.pi,floor=12),fixture('poor_block','P_POOR_01',origin=(80,70),yaw=.43),fixture('merchant_court','P_MERCHANT_01',origin=(-90,70),yaw=-.31)]
    def resolve(self,fs=None):
        plan,terrain,h=inputs(fs or self.fixtures);resolver=PropertyResolver();return resolver,resolver.resolve(plan,terrain,[p['id'] for p in plan['plots']],h)
    def test_exact_reframed_recipe_geometry_and_single_floor(self):
        resolver,out=self.resolve();self.assertFalse(out['unresolved']);self.assertEqual(out['summary']['resolved_plots'],4)
        for f,r in zip(self.fixtures,sorted(out['resolved_properties'],key=lambda x:[f[0]['id'] for f in self.fixtures].index(x['source_plot_id']))):
            expected={p['id']:p for p in f[4]['placements']}
            for p in r['placements']:
                q=expected[p['id']];self.assertEqual(p['asset_key'],q['asset_key']);self.assertEqual(p['position_m'],q['position_m']);self.assertEqual(p['yaw_rad'],q['yaw_rad']);self.assertEqual(p['footprint_xz_m'],q['footprint_xz_m']);self.assertEqual(p['ground_anchor']['support_points_xz_m'],q['ground_anchor']['support_points_xz_m']);self.assertEqual(p['position_m'][1],r['floor_y_m'])
            self.assertEqual(r['surface_ownership']['polygon_xz_m'],f[0]['polygon_xz_m'])
    def test_template_and_source_cache_reused_without_compiler(self):
        resolver,out=self.resolve();self.assertEqual(out['summary']['cache_templates_built'],3);self.assertEqual(out['summary']['per_plot_compile_count'],0);count=resolver.source_build_count
        plan,terrain,h=inputs(self.fixtures);again=resolver.resolve(plan,terrain,[f[0]['id'] for f in self.fixtures],h);self.assertEqual(resolver.source_build_count,count);self.assertEqual(resolver.template_build_count,3);self.assertEqual(out,again)
    def test_explicit_scope_no_replacement_of_unapproved_plot(self):
        plan,terrain,h=inputs(self.fixtures);out=PropertyResolver().resolve(plan,terrain,[self.fixtures[0][0]['id']],h);self.assertEqual(out['summary']['resolved_plots'],1);self.assertTrue(all(p['replacement_ids']==[] for p in out['unresolved']))
        with self.assertRaises(ValueError):PropertyResolver().resolve(plan,terrain,None,h)
    def test_irregular_and_unknown_property_kept_unresolved(self):
        plan,terrain,h=inputs(self.fixtures[:2]);plan['plots'][0]['polygon_xz_m'][0][0]+=2;plan['plots'][1]['property_type']='irregular_old_town';h=sha(plan);terrain['source_plan_sha256']=h;out=PropertyResolver().resolve(plan,terrain,[p['id'] for p in plan['plots']],h);self.assertFalse(out['resolved_properties']);self.assertEqual({p['reason'] for p in out['unresolved']},{'irregular_or_incomplete_buildable_frame','no_complete_recipe_for_property_type'});self.assertTrue(all(p['replacement_ids']==[] for p in out['unresolved']))
    def test_missing_pad_never_uses_per_building_floor(self):
        plan,terrain,h=inputs(self.fixtures[2:3]);terrain['compound_pads']=[];terrain['building_pads']=[{'plot_id':plan['plots'][0]['id'],'floor_y_m':5}];out=PropertyResolver().resolve(plan,terrain,[plan['plots'][0]['id']],h);self.assertEqual(out['unresolved'][0]['reason'],'missing_whole_compound_pad')
    def test_snapshot_mismatch_keeps_everything(self):
        plan,terrain,h=inputs(self.fixtures);terrain['source_plan_sha256']='0'*64;out=PropertyResolver().resolve(plan,terrain,[p['id'] for p in plan['plots']],h);self.assertFalse(out['resolved_properties']);self.assertFalse(out['asset_manifest']);self.assertEqual(out['summary']['unresolved_reasons'],{'terrain_source_snapshot_mismatch':4})
    def test_nonlevel_secondary_gate_is_rejected(self):
        plan,terrain,h=inputs(self.fixtures[:1]);terrain['compound_pads'][0]['gate_ledger'][1]['landing_y_m']+=.2;out=PropertyResolver().resolve(plan,terrain,[plan['plots'][0]['id']],h);self.assertEqual(out['unresolved'][0]['reason'],'missing_or_nonlevel_gate_landing')
    def test_missing_external_frontage_is_rejected(self):
        plan,terrain,h=inputs(self.fixtures[:1]);plan['paths']=[p for p in plan['paths'] if ':service_gate:EXTERNAL' not in p['id']];h=sha(plan);terrain['source_plan_sha256']=h;out=PropertyResolver().resolve(plan,terrain,[plan['plots'][0]['id']],h);self.assertEqual(out['unresolved'][0]['reason'],'missing_external_frontage_source_link')
    def test_reviewed_proxy_drift_is_rejected(self):
        plan,terrain,h=inputs(self.fixtures[:1]);plan['buildings'][0]['asset_key']='wrong';h=sha(plan);terrain['source_plan_sha256']=h;out=PropertyResolver().resolve(plan,terrain,[plan['plots'][0]['id']],h);self.assertEqual(out['unresolved'][0]['reason'],'reviewed_recipe_proxy_geometry_mismatch')
    def test_replacement_ledger_preserves_external_paths(self):
        resolver,out=self.resolve(self.fixtures[:1]);r=out['resolved_properties'][0];ledger=r['replacement_ledger'];self.assertEqual(set(ledger['replace_building_ids']),{x['id'] for x in self.fixtures[0][2]});self.assertTrue(all(':EXTERNAL' in i for i in ledger['preserve_external_path_ids']));self.assertFalse(set(ledger['preserve_external_path_ids'])&set(ledger['replace_internal_path_ids']));self.assertTrue(ledger['atomic_replacement_required'])
    def test_compiled_cache_requires_matching_source_and_resource(self):
        resolver,out=self.resolve(self.fixtures[:1]);compiled={k:{'master_source_sha256':v['master_source_sha256'],'sampling_resource':v['sampling_resource'],'compiled_asset_ref':'fixture-cache/'+k} for k,v in out['asset_manifest'].items()};plan,terrain,h=inputs(self.fixtures[:1]);hit=resolver.resolve(plan,terrain,[plan['plots'][0]['id']],h,compiled);self.assertTrue(all(a['cache_status']=='reuse_verified_compiled_asset' for a in hit['asset_manifest'].values()));key=next(iter(compiled));compiled[key]['sampling_resource']={'pitch':100};miss=resolver.resolve(plan,terrain,[plan['plots'][0]['id']],h,compiled);self.assertEqual(miss['asset_manifest'][key]['cache_status'],'compile_once_required')
    def test_mutated_source_mapping_cannot_reuse_old_snapshot_hash(self):
        plan,terrain,h=inputs(self.fixtures[:1]);plan['plots'][0]['origin_xz_m'][0]+=1;out=PropertyResolver().resolve(plan,terrain,[plan['plots'][0]['id']],h);self.assertEqual(out['unresolved'][0]['reason'],'source_mapping_not_bound_to_supplied_snapshot_hash')
    def test_unclassified_path_and_escaping_internal_path_preserved(self):
        for kind,points,reason in [('unknown_route',[[0,0],[1,1]],'unclassified_path_ownership'),('door_link',[[0,0],[999,999]],'internal_path_leaves_replacement_plot')]:
            plan,terrain,h=inputs(self.fixtures[:1]);pid=plan['plots'][0]['id'];plan['paths'].append({'id':'do_not_delete','owner_plot_id':pid,'kind':kind,'polyline_xz_m':points});h=sha(plan);terrain['source_plan_sha256']=h;out=PropertyResolver().resolve(plan,terrain,[pid],h);self.assertEqual(out['unresolved'][0]['reason'],reason);self.assertEqual(out['unresolved'][0]['replacement_ids'],[])
    def test_entire_frozen_variant_catalog_is_instanced_once(self):
        fs=[fixture(kind,'P_'+kind+'_'+str(v),v,origin=(v*100,100 if kind=='poor_block' else 0)) for kind in recipes.FAMILIES for v in range(3 if kind=='noble_estate' else 2 if kind=='poor_block' else 1)]
        resolver,out=self.resolve(fs);self.assertFalse(out['unresolved']);self.assertEqual(out['summary']['unique_assets'],25);self.assertEqual(out['summary']['common_sources_built'],25);self.assertEqual(out['summary']['cache_templates_built'],6);self.assertEqual(out['summary']['per_plot_compile_count'],0)
    def test_frozen_recipe_hashes_unchanged(self):
        m=json.loads((HERE/'freeze_manifest.json').read_text())
        for path,h in m['all_files_sha256'].items():self.assertEqual(hashlib.sha256((HERE/path).read_bytes()).hexdigest(),h,path)
if __name__=='__main__':unittest.main()
