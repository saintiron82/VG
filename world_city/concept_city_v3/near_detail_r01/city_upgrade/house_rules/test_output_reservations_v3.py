import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import namedtuple
from output_reservations_v3 import ReservationBook,ReservationError


def compete(root,key,q):
    root=Path(root);b=ReservationBook(root/'book',root,[root/'out'],100,0,0)
    try:b.reserve(key,[{'directory':'out','prefix':key}],60,{'key':key});q.put(True)
    except ReservationError:q.put(False)

class ReservationV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'out').mkdir();self.b=ReservationBook(self.root/'book',self.root,[self.root/'out'],100,0,0)
    def tearDown(self):
        for key in list(self.b._writers):self.b.release_writer(key)
        self.temp.cleanup()
    def claim(self,key,cap):return self.b.reserve(key,[{'directory':'out','prefix':key}],cap,{'key':key})
    def test_path_segments_and_prefix_temporary_names_match_exactly(self):
        self.b.reserve('unicode',[{'directory':'out','prefix':'한글'}],50,{'key':'unicode'})
        (self.root/'out/한글.tmp').write_bytes(b'x'*9)
        (self.root/'out/.tmp.한글').write_bytes(b'x'*11)
        (self.root/'out/한글2').mkdir();(self.root/'out/한글2/item').write_bytes(b'x'*7)
        s=self.b.inspect();self.assertEqual(s['assets']['unicode']['owned_bytes'],16)
        self.assertEqual(s['unowned_retained_bytes'],11);self.assertEqual(s['reserved_total_bytes'],61)
    def test_similar_directory_segment_is_not_an_owner(self):
        (self.root/'out/house').mkdir();(self.root/'out/house2').mkdir()
        self.b.reserve('asset',[{'directory':'out/house','prefix':''}],50,{'key':'asset'})
        (self.root/'out/house/a').write_bytes(b'x'*8);(self.root/'out/house2/a').write_bytes(b'x'*9)
        s=self.b.inspect();self.assertEqual(s['assets']['asset']['owned_bytes'],8);self.assertEqual(s['unowned_retained_bytes'],9)
    def test_active_caps_count_once_even_as_owned_bytes_change(self):
        self.claim('a',60);self.claim('b',40);(self.root/'out/a.tmp').write_bytes(b'x'*37)
        with self.b.writer('a'):
            s=self.b.check('a',23);self.assertEqual(s['reserved_total_bytes'],100);self.assertEqual(s['unowned_retained_bytes'],0)
            with self.assertRaises(ReservationError):self.b.check('a',24)
    def test_exceeded_active_cap_is_charged_at_observed_size(self):
        self.claim('a',60);(self.root/'out/a.tmp').write_bytes(b'x'*61)
        self.assertEqual(self.b.inspect()['reserved_total_bytes'],61)
        with self.b.writer('a'),self.assertRaises(ReservationError):self.b.check('a',0)
    def test_duplicate_asset_writers_are_rejected(self):
        self.claim('a',60);self.b.acquire_writer('a');other=ReservationBook(self.root/'book',self.root,[self.root/'out'],100,0,0)
        with self.assertRaises(ReservationError):other.acquire_writer('a')
        with self.assertRaises(ReservationError):other.release('a',{'key':'a'},'unsafe')
    def test_prewrite_requires_lifetime_writer(self):
        self.claim('a',60)
        with self.assertRaises(ReservationError):self.b.check('a',1)
    def test_fork_pid_cannot_write_or_release_parent_lease(self):
        self.claim('a',60);self.b.acquire_writer('a')
        with patch('output_reservations_v3.os.getpid',return_value=-99):
            with self.assertRaises(ReservationError):self.b.check('a',1)
            with self.assertRaises(ReservationError):self.b.release('a',{'key':'a'},'unsafe')
        self.assertEqual(self.b.record('a')['state'],'ACTIVE')
    def test_disk_floor_reserves_full_active_caps_not_only_missing_bytes(self):
        Disk=namedtuple('Disk','total used free');self.b=ReservationBook(self.root/'book',self.root,[self.root/'out'],100,0,1000)
        with patch('output_reservations_v3.shutil.disk_usage',return_value=Disk(2000,940,1060)):self.claim('a',60)
        (self.root/'out/a.done').write_bytes(b'x'*59)
        with self.b.writer('a'),patch('output_reservations_v3.shutil.disk_usage',return_value=Disk(2000,941,1059)),self.assertRaises(ReservationError):self.b.check('a',1)
    def test_cross_process_admission_is_atomic(self):
        q=multiprocessing.Queue();jobs=[multiprocessing.Process(target=compete,args=(str(self.root),k,q)) for k in ('a','b')]
        for j in jobs:j.start()
        for j in jobs:j.join(5);self.assertEqual(j.exitcode,0)
        self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),[False,True])
    def test_overlapping_scopes_and_changed_identity_fail(self):
        self.claim('a',50)
        with self.assertRaises(ReservationError):self.b.reserve('b',[{'directory':'out','prefix':'abc'}],10,{})
        with self.assertRaises(ReservationError):self.b.reserve('a',[{'directory':'out','prefix':'a'}],50,{'key':'different'})
    def test_unowned_files_and_release_preserved(self):
        self.claim('a',60);(self.root/'out/a.done').write_bytes(b'x'*20);(self.root/'out/foreign.tmp').write_bytes(b'x'*10)
        self.assertEqual(self.b.inspect()['reserved_total_bytes'],70)
        s=self.b.release('a',{'key':'a'},'verified');self.assertEqual(s['reserved_total_bytes'],30);self.assertTrue((self.root/'out/a.done').exists())

if __name__=='__main__':unittest.main()
