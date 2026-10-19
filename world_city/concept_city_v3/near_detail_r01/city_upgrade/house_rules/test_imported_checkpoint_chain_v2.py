"""Recursive read-only checkpoint reuse; no sampling and no original writes."""
import copy,hashlib,json,unittest
from pathlib import Path
import test_imported_checkpoint_prefix_v1 as baseline
import imported_checkpoint_chain_v2 as imported
import checkpoint_store as checkpoint
baseline.imported=imported
class ChainedPrefixTests(baseline.ImportedPrefixTests):
    def nested(self):
        first=self.open();first.append(2,self.records[2],self.states[2])
        files=imported.file_inventory(self.delta);identity=copy.deepcopy(first.identity)
        new=copy.deepcopy(self.new_identity);new['header']['layer_engine_sha256']='c'*64
        second=imported.ImportedPrefixStore(self.delta,identity,files,self.root/'third',new,
            expected_owned_lows=self.lows,expected_compatibility=self.compatibility,original_count=3,repository_root=self.root)
        return first,second,files
    def test_recursive_prefix_and_append_preserve_records_state_and_bytes(self):
        original=imported.file_inventory(self.old);first,second,files=self.nested()
        self.assertEqual(second.completed_count,3);self.assertEqual(list(second.load_records()),self.records[:3])
        self.assertEqual(second.load_state(),self.states[2])
        segments=imported.producer_segments(second._original.reader)
        self.assertEqual([(r['first'],r['count'],r['producer']['layer_engine_sha256']) for r in segments],[(0,2,'a'*64),(2,1,'b'*64)])
        second.append(3,self.records[3],self.states[3]);self.assertEqual(list(second.load_records()),self.records)
        self.assertEqual(imported.file_inventory(self.old),original);self.assertEqual(imported.file_inventory(self.delta),files)
        self.assertEqual(second.load_state(),self.states[3])
    def test_recursive_original_tamper_rejected(self):
        _,second,_=self.nested();path=self.old/'chunk-00000000.json.gz';path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaises(checkpoint.CheckpointError):list(second.load_records())
    def test_recursive_delta_tamper_rejected(self):
        _,second,_=self.nested();path=self.delta/'chunk-00000000.json.gz';path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaises(checkpoint.CheckpointError):second.load_state()
    def test_global_coverage_count_mismatch_rejected_before_output(self):
        first=self.open();first.append(2,self.records[2],self.states[2]);target=self.root/'wrong'
        with self.assertRaises(checkpoint.CheckpointError):
            imported.ImportedPrefixStore(self.delta,first.identity,imported.file_inventory(self.delta),target,self.new_identity,
                expected_owned_lows=self.lows,expected_compatibility=self.compatibility,original_count=2,repository_root=self.root)
        self.assertFalse(target.exists())
if __name__=='__main__':unittest.main()
