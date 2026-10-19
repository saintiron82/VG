"""Parent-approved staged budget increase; preserve old contracts and active pins."""
import copy
import hashlib
import json
from pathlib import Path
import adapter as a
import output_reservations_v1 as old
import output_reservations_v2 as new

H=Path(__file__).resolve().parent


def run():
    old_config_path=H/'shared_output_budget.v1.json';oc=a.load(old_config_path)
    if oc['limit_bytes']!=180_000_000:raise ValueError('Expected original 180MB contract')
    nc={**oc,'schema':'riverstone.retained_output.shared_budget.v2',
        'book_path':str((H/'generated/shared_output_reservations.v2.json').relative_to(a.ROOT)),
        'limit_bytes':350_000_000,'min_free_disk_bytes':1073741824}
    cp=H/'shared_output_budget.v2.json';new_path=a.ROOT/nc['book_path']
    if cp.exists() or new_path.exists():raise ValueError('Existing migrated contract preserved; do not reinitialize')
    ob=old.ReservationBook(a.ROOT/oc['book_path'],a.ROOT,[a.ROOT/p for p in oc['retained_roots']],oc['limit_bytes'])
    nb=new.ReservationBook(new_path,a.ROOT,[a.ROOT/p for p in nc['retained_roots']],nc['limit_bytes'],min_free_disk_bytes=nc['min_free_disk_bytes'])
    # Fixed lock order: original book, then new book. Old writers are already
    # admitted; all NEW workers must use the new configuration after publication.
    with ob._locked() as original:
        original_bytes=ob.path.read_bytes();sha=hashlib.sha256(original_bytes).hexdigest()
        snapshot=H/'fixtures'/('shared_output_reservations_180mb_'+sha[:16]+'.json')
        if snapshot.exists() and snapshot.read_bytes()!=original_bytes:raise ValueError('Frozen budget snapshot differs')
        if not snapshot.exists():snapshot.write_bytes(original_bytes)
        with nb._locked() as migrated:
            migrated['assets']=copy.deepcopy(original['assets'])
            migrated['migration']={'original_book_path':oc['book_path'],'original_book_sha256':sha,
                'preserved_snapshot_path':str(snapshot.relative_to(a.ROOT)),'preserved_snapshot_sha256':a.sha(snapshot),
                'original_config_path':str(old_config_path.relative_to(a.ROOT)),'original_config_sha256':a.sha(old_config_path),
                'new_v1_admissions_allowed':False,'old_writer_policy':'Existing pinned v1 writers drain under their original smaller cap; same active scopes/caps remain protected here until all final QA writes finish.',
                'active_old_book_keys':[k for k,r in original['assets'].items() if r['state']=='ACTIVE'],
                'geometry_source_or_checkpoint_modified':False}
            summary=nb._summary(migrated)
            if summary['unreserved_bytes']<0 or summary['disk_free_after_active_caps_bytes']<nc['min_free_disk_bytes']:
                raise ValueError('New shared/disk guard fails before migration publication')
            nb._write(migrated)
        if ob.path.read_bytes()!=original_bytes:raise ValueError('Original ledger changed while migration lock held')
    # Config is the publication point for new workers; original remains intact.
    with cp.open('x') as f:json.dump(nc,f,indent=2);f.write('\n')
    report={'schema':'riverstone.retained_output.budget_migration.v2','old':migrated['migration'],
            'new_config_path':str(cp.relative_to(a.ROOT)),'new_config_sha256':a.sha(cp),
            'new_book_path':nc['book_path'],'new_book_sha256':a.sha(new_path),'summary_at_migration':summary,
            'old_helper_sha256':a.sha(old.__file__),'new_helper_sha256':a.sha(new.__file__)}
    a.write(H/'generated/shared_output_budget_migration.v2.json',report)
    print(json.dumps(report),flush=True)

if __name__=='__main__':run()
