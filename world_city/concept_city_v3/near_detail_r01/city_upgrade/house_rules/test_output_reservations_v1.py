import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from output_reservations_v1 import ReservationBook,ReservationError


def compete(root,key,queue):
    root=Path(root);book=ReservationBook(root/'ledger.json',root,[root/'outputs'],100,0)
    try:book.reserve(key,[{'directory':'outputs','prefix':key}],60,{'source':key});queue.put(True)
    except ReservationError:queue.put(False)


class Reservations(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'outputs').mkdir()
        self.book=ReservationBook(self.root/'ledger.json',self.root,[self.root/'outputs'],100,0)
    def tearDown(self):self.temp.cleanup()
    def claim(self,key,cap):return self.book.reserve(key,[{'directory':'outputs','prefix':key}],cap,{'source':key})
    def test_actual_growth_consumes_reserved_remaining_without_extra_capacity(self):
        self.claim('a',60);self.claim('b',40);(self.root/'outputs/a.bin').write_bytes(b'a'*50)
        s=self.book.check('a',10);self.assertEqual(s['reserved_total_bytes'],100)
        self.assertEqual(s['assets']['a']['remaining_reserved_bytes'],10)
        with self.assertRaises(ReservationError):self.book.check('a',11)
    def test_competing_processes_cannot_both_overbook(self):
        q=multiprocessing.Queue();jobs=[multiprocessing.Process(target=compete,args=(str(self.root),key,q)) for key in ('a','b')]
        for j in jobs:j.start()
        for j in jobs:j.join(5);self.assertEqual(j.exitcode,0)
        self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),[False,True])
    def test_resume_identity_and_budget_are_pinned(self):
        self.claim('a',50);self.claim('a',50)
        with self.assertRaises(ReservationError):self.claim('a',51)
        with self.assertRaises(ReservationError):self.book.reserve('a',[{'directory':'outputs','prefix':'a'}],50,{'source':'changed'})
    def test_foreign_and_temporary_files_count(self):
        self.claim('a',50);(self.root/'outputs/foreign.partial').write_bytes(b'x'*51)
        with self.assertRaises(ReservationError):self.book.check('a',1)
    def test_overlapping_scopes_fail(self):
        self.claim('a',50)
        with self.assertRaises(ReservationError):self.book.reserve('other',[{'directory':'outputs','prefix':'abc'}],10,{'source':'other'})
    def test_release_keeps_payloads_and_history(self):
        self.claim('a',80);p=self.root/'outputs/a.bin';p.write_bytes(b'x'*20)
        s=self.book.release('a',{'source':'a'},'QA passed');self.assertEqual(s['reserved_total_bytes'],20);self.assertTrue(p.exists())
        self.assertEqual(self.book.record('a')['state'],'RELEASED')
    def test_root_contract_and_external_paths_rejected(self):
        self.claim('a',50)
        with self.assertRaises(ReservationError):ReservationBook(self.root/'ledger.json',self.root,[self.root/'outputs'],101,0).inspect()
        with self.assertRaises(ReservationError):self.book.reserve('x',[{'directory':'elsewhere','prefix':''}],1,{})
    def test_active_reservations_do_not_expire(self):
        self.claim('a',80);again=ReservationBook(self.root/'ledger.json',self.root,[self.root/'outputs'],100,0)
        self.assertEqual(again.inspect()['remaining_reserved_bytes'],80)
        with self.assertRaises(ReservationError):again.reserve('b',[{'directory':'outputs','prefix':'b'}],21,{})

if __name__=='__main__':unittest.main()
