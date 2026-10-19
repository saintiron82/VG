#!/usr/bin/env python3
"""Unchanged source/hash-checked runner; capsule-only invocation is required."""
import importlib.util,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[4]
p=H/'frozen_run_validation_r01.py'
s=importlib.util.spec_from_file_location('gate_runner',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.H=H
if __name__=='__main__':raise SystemExit(m.main())
