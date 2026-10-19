#!/usr/bin/env python3
"""Use the unchanged R9 finite-crop preparer for local junction tests."""
import importlib.util,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[4]
p=H/"frozen_finite_preparer_r01.py"
s=importlib.util.spec_from_file_location("gate_finite_preparer",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.H=H
if __name__=="__main__":m.main()
