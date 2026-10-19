import copy, unittest
import author_facility_roofs as a
import finish_roofs as f

class FinishedRoofContracts(unittest.TestCase):
 def source(self,cut=False):
  m=a.new_master('tiny_roof',{'slate':'646f73','slate_dark':'4a565c'})
  ops=[a.shared.prism('slope',[[0,1.4],[1,2.4],[1,3],[0,2]],0,1,'slate')]
  if cut:ops.append({'id':'exact_hip_trim','action':'cut','part':'solid','shape':{'kind':'box','min':[-.1,0,.55],'max':[1.1,4,1.1]}})
  m['components']=[a.comp('roof',ops),a.comp('ridge',[a.shared.box('roof_ridge',[.9,2.6,0],[1.1,3,1],'slate_dark')])];m['instances']=[{'id':'roof','component':'roof'},{'id':'ridge','component':'ridge'}];return m
 def item(self):return {'master_path':'fixture','master_sha256':'fixture','render_path':'fixture','render_sha256':'fixture','pitch_m':.5,'palette_id_counts':{},'slots':{'slate':{'operation_role_counts':{'roof_covering':1}},'slate_dark':{'operation_role_counts':{'roof_ridge':1}}}}
 def descriptor(self,m):return a.describe('tiny',self.item(),m,allow_terminal_component_cuts=True)
 def test_terminal_cut_preserved_and_scoped(self):
  m=self.source(True);d=self.descriptor(m);self.assertFalse(d['pending']);n=f.finish(d,m,a.read(f.RULES));self.assertEqual(len(n['assembly_cuts']),1);self.assertEqual(n['assembly_cuts'][0]['metadata']['source_cut_id'],'exact_hip_trim');self.assertTrue(all(v.startswith('plane_') for v in n['assembly_cuts'][0]['selector']['instance']))
 def test_nonterminal_cut_pending(self):
  m=self.source(True);m['components'][0]['operations'].append(a.shared.box('late_roof_fill',[0,1.4,.6],[1,1.6,.8],'slate'));d=self.descriptor(m);self.assertTrue(d['pending']);self.assertFalse(d['preserved_terminal_component_cuts'])
 def test_feature_selector_pending(self):
  m=self.source(True);m['components'][0]['operations'][-1]['selector']={'feature':'slope'};d=self.descriptor(m);self.assertTrue(d['pending'])
 def test_flatten_preserves_compiled_geometry_and_cut(self):
  m=self.source(True);d=self.descriptor(m);near=f.finish(d,m,a.read(f.RULES));flat=f.flatten(near);opts={'max_candidate_cells':150000,'max_output_cells':50000};x=a.core.compile_master(near,{'pitch':.05},**opts);y=a.core.compile_master(flat,{'pitch':.05},**opts);self.assertEqual({(*r[:3],r[5]) for r in x['cells']},{(*r[:3],r[5]) for r in y['cells']});self.assertEqual(len(flat['components']),len(flat['instances']));self.assertTrue(all('shared_row_source' in c['metadata'] for c in flat['components']))
 def test_ridge_is_segmented_prisms_with_sealed_bed(self):
  m=self.source();d=self.descriptor(m);near=f.finish(d,m,a.read(f.RULES));c=next(c for c in near['components'] if c['id'].startswith('finished_ridge_'));self.assertGreaterEqual(len(c['operations']),4);self.assertEqual(c['operations'][0]['shape']['kind'],'box');self.assertTrue(all(o['shape']['kind']=='extrusion' for o in c['operations'][1:]));self.assertFalse(any(c['id'].startswith('retained_ridge_') for c in near['components']))
 def test_eaves_have_recessed_backing_and_real_fascia(self):
  m=self.source();d=self.descriptor(m);near=f.finish(d,m,a.read(f.RULES));under=next(c for c in near['components'] if c['id']=='plane_000_underlay')['operations'][0]['shape'];edge=next(c for c in near['components'] if c['id']=='plane_000_finished_edges');self.assertEqual(under['z_min'],.05);self.assertEqual(under['polygon'][0][0],.05);self.assertTrue(any('eave_segment' in o['id'] for o in edge['operations']));self.assertTrue(any('verge' in o['id'] for o in edge['operations']))
 def test_rigid_source_and_palette_unchanged(self):
  m=self.source();before=copy.deepcopy(m);m['instances'][0]['transform']={'basis':[[0,0,-1],[0,1,0],[1,0,0]],'translation':[3,0,4]};before=copy.deepcopy(m);near=f.finish(self.descriptor(m),m,a.read(f.RULES));flat=f.flatten(near);self.assertEqual(m,before);self.assertEqual(flat['materials'],m['materials']);self.assertFalse(flat['metadata']['runtime_activation']);f.layers.SpatialSource(flat,.05)
 def test_suffix_overlapping_source_instance_ids(self):
  m=self.source();m['instances'].append({'id':'second_roof','component':'roof','transform':{'translation':[7,0,0]}});near=f.finish(self.descriptor(m),m,a.read(f.RULES));selected=[i for i in near['instances'] if i['id'].endswith('_second_roof')];self.assertTrue(selected);self.assertTrue(all(i['metadata']['source_identity']['instance']=='second_roof' for i in selected))
 def test_original_instance_and_paint_order_retained(self):
  import expand_facilities as expand
  m=self.source();m['instances']=list(reversed(m['instances']));near=expand.ordered_finish(self.descriptor(m),m,a.read(f.RULES),'roof_tile');ids=[i['metadata']['source_identity']['instance'] for i in near['instances']];self.assertEqual(ids[0],'ridge');self.assertEqual(ids[-1],'roof')

if __name__=='__main__':unittest.main()
