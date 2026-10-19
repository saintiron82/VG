import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import adapter as a
import checkpoint_store
import imported_checkpoint_prefix_v1 as imports
import layered_compile as old
import layered_compile_import_v3_r01 as new
import layered_qa as qa
import replay_certificate_qa as replay
import verify_imported_prefix_replay_v1 as prefix_replay
from test_bounded_surface_export import source


class ActualImportedPrefix(unittest.TestCase):
    def test_old_prefix_then_new_suffix_exact_and_only_one_historical_session_left(self):
        with tempfile.TemporaryDirectory(dir=old.HERE) as directory:
            d=Path(directory);out=d/'outputs';out.mkdir()
            master=source(True)
            master['constraints'].append({'id':'connected_body','kind':'connected','selector':{}})
            sp=d/'source.json';a.write(sp,master)
            cat=d/'catalog.json';a.write(cat,{'assets':[{'asset_key':'import_fixture',
                'source_master_path':str(sp.relative_to(a.ROOT)),'source_sha256':a.sha(sp),
                'emitted_master_path':str(sp.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(sp)}]})
            rules=a.load(old.HERE/'layer_rules.v1.json');rules['chunk_edge_fine_cells']=4
            rules['memory_limit_bytes']=268435456
            rules['shared_output_reservation']={'book_path':str((d/'book.json').relative_to(a.ROOT)),
                'retained_roots':[str(out.relative_to(a.ROOT)),str((old.HERE/'replay_code').relative_to(a.ROOT))],
                'limit_bytes':10000000,'asset_cap_bytes':1000000,'min_free_disk_bytes':1073741824}
            rp=d/'old_rules.json';a.write(rp,rules)
            policy={'enabled_asset_keys':['import_fixture'],'max_sessions':2,'per_session_wall_seconds':900,
                    'soft_stop_seconds':840,'fixture_stop_after_chunks':2}
            pp=d/'old_policy.json';a.write(pp,policy)
            stopped=old.run('import_fixture',out/'old',rp,cat,True,pp)
            self.assertEqual(stopped['completed_chunks'],2)
            cp=out/'old/import_fixture.layered.checkpoint';manifest=a.load(cp/'manifest.json')
            ledger=out/'old/import_fixture.layered.checkpoint_sessions.json'
            pins=imports.file_inventory(cp)
            contract={'original_directory':str(cp.relative_to(a.ROOT)), 'original_identity':manifest['identity'],
                      'original_files':pins,'original_count':2,'expected_owned_lows':manifest['identity']['owned_lows'],
                      'original_session_ledger':{'path':str(ledger.relative_to(a.ROOT)),'sha256':a.sha(ledger)}}
            ip=d/'import.json';a.write(ip,contract)
            proof=d/'prefix_replay.json';self.assertEqual(prefix_replay.verify(ip,proof),0)
            newrules=copy.deepcopy(rules)
            newrules['imported_checkpoint_prefix']={'path':str(ip.relative_to(a.ROOT)),'sha256':a.sha(ip),
                'independent_prefix_replay':{'path':str(proof.relative_to(a.ROOT)),'sha256':a.sha(proof)}}
            nr=d/'new_rules.json';a.write(nr,newrules)
            np=d/'new_policy.json';policy.pop('fixture_stop_after_chunks');a.write(np,policy)
            actual_compile=new.prepared_sampling_v3.compile_prepared;calls=[]
            def compile(plan,**kwargs):
                calls.append((plan.pitch,copy.deepcopy(kwargs['cell_bounds'])))
                return actual_compile(plan,**kwargs)
            with patch.object(new.prepared_sampling_v3,'compile_prepared',side_effect=compile):
                stats=new.run('import_fixture',out/'new',nr,cat,True,np)
            self.assertEqual(len(calls),6)
            self.assertEqual([b['min'][0] for pitch,b in calls if pitch==.05],[6,10,14])
            self.assertEqual(stats['checkpoint']['imported_complete_chunks'],2)
            self.assertEqual(stats['checkpoint']['new_delta_chunks'],3)
            self.assertEqual(stats['checkpoint']['sessions_started'],2)
            self.assertEqual(imports.file_inventory(cp),pins)
            self.assertTrue(all(c['pass'] for c in stats['constraints']))
            self.assertEqual(stats['reference_full_fine_cells'],80)
            self.assertEqual([r['producer']['producer_id'] for r in stats['chunks']],
                             ['imported_reference_core']*2+['new_prepared_v3']*3)
            self.assertEqual(stats['sampling_backend']['sampler_id'],'explicit_imported_prefix_then_prepared_v3')
            self.assertEqual(stats['compiled_header']['sampling_backend']['sampler_id'],'common.prepared_sampling_v3')
            self.assertTrue(replay.verify(out/'new/import_fixture.layered.stats.json')['pass'])
            with self.assertRaises(a.UnsupportedSurface):
                new.run('import_fixture',out/'new',nr,cat,True,np,True)
            with gzip.open(a.ROOT/stats['files']['.render.json']['path'],'rt') as f:render=json.load(f)
            reference=a.core.compile_master(master,{'pitch':.05});cells={tuple(row[:3]):row for row in reference['cells']}
            expected=qa.Fingerprint();occupied=qa.Fingerprint()
            for row in reference['cells']:
                occupied.add(row)
                for axis in range(3):
                    for sign in (-1,1):
                        neighbor=list(row[:3]);neighbor[axis]+=sign
                        if tuple(neighbor) not in cells:
                            expected.add([axis,sign,row[axis]+(sign>0),row[(axis+1)%3],row[(axis+2)%3],row[5]])
            self.assertEqual(occupied.as_dict(),qa._fingerprint(stats['full_fine_fingerprint']))
            self.assertEqual(expected.as_dict(),qa._fingerprint(stats['fine_face_fingerprint']))


if __name__=='__main__':unittest.main()
