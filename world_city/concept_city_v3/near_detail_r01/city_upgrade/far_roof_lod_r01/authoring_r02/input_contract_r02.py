"""Frozen roof input adapter plus conservative common-source bounds auditing.

Raw/canonical roof solids, material ownership and the source union are unchanged.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'expansion_r01'))
from input_contract import *
from input_contract import inspect as frozen_inspect
import source_bounds


def inspect(key,mapping,source,master):
    contract=frozen_inspect(key,mapping,source,master)
    if contract['status']!='SUPPORTED_INPUT_UNBUILT':return contract
    try:
        audit=source_bounds.audit_paints(master,source_parts,mapping['pitch_m'],set(contract['materials']))
        strict=source_bounds.strict_cut_proofs(master,source_parts,mapping['pitch_m'],set(contract['materials']))
    except (ValueError,KeyError,OverflowError)as exc:
        code='ROOF_CUT_CONSERVATIVE_DISJOINTNESS_UNPROVEN'if str(exc).startswith('ROOF_CUT_')else 'SOURCE_CONSERVATIVE_BOUNDS_UNSUPPORTED'
        return reject(key,[code],[str(exc)])
    contract['source_paint_bounds_audit']=audit
    contract['strict_cut_exclusion_proofs']=strict
    contract['conservative_bounds_helper']=ref(Path(source_bounds.__file__))
    contract['frozen_roof_input_adapter']=ref(H/'input_contract.py')
    return contract
