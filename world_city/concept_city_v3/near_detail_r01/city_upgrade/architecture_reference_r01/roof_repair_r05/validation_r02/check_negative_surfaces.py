"""Reuse the frozen explicit two-cell fixture suite; never mutates candidate files."""
import sys,json
from pathlib import Path
H=Path(__file__).resolve().parents[1];A=H.parent
sys.path.insert(0,str(A/'roof_repair_r04/validation_r01'))
from test_surface_rejections import surface_tests,ref,save
r=surface_tests();assert len(r)==10 and all(x['rejected']for x in r.values());save(H/'validation_r02/negative_surfaces.json',{'schema':'riverstone.roof_r05.exterior_negative_regression.v1','reused_test_driver':ref(A/'roof_repair_r04/validation_r01/test_surface_rejections.py'),'tests':r,'negative_rejected':len(r),'candidate_files_mutated':False});print(json.dumps({'negative_rejected':len(r)}))
