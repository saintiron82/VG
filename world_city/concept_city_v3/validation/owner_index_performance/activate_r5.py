"""Explicit process-local r5 hook. Never edits source files or other processes.

The caller must opt in, identify r5, and keep the returned handle until restore.
A context manager restores the exact original callable even on export failure.
"""
import functools, hashlib, json, marshal, os, types
from pathlib import Path
from .prefilter import OwnerLookup

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir())
REVIEW_NAME='review_0152fd53ccd0.json'
REVIEW_SHA256='a48a1466c37f0ceaf08ae41b576a06f4b5f53803855ff936c2e3c302bd502bf0'


def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _json_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _index_hash(index):return _json_hash([[list(k),v] for k,v in sorted(index.cells.items())])
def _callable_binding(f):
 raw=getattr(f,'__wrapped__',f)
 return dict(module=raw.__module__,qualname=raw.__qualname__,code_sha256=hashlib.sha256(marshal.dumps(raw.__code__)).hexdigest(),cache_parameters=f.cache_parameters() if hasattr(f,'cache_parameters') else None)


def _validate_seal():
 if _sha(HERE/REVIEW_NAME)!=REVIEW_SHA256:raise ValueError('Lookup review seal changed')
 review=json.loads((HERE/REVIEW_NAME).read_text())
 if review['status']!='pass_bounded_lookup_candidate' or review['boundary_parity']['queries']!=1114007 or review['boundary_parity']['failures']:raise ValueError('Lookup review incomplete')
 for r in review['evidence']:
  if _sha(ROOT/r['path'])!=r['sha256']:raise ValueError('Changed lookup evidence: '+r['path'])
 return review


def _validate_original(source):
 """Compare the live callable with the function compiled from sealed bytes."""
 module_code=compile(Path(source.__file__).read_text(),source.__file__,'exec')
 expected=next(c for c in module_code.co_consts if isinstance(c,types.CodeType) and c.co_name=='owner_at')
 original=source.owner_at
 if type(original) is not type(functools.lru_cache()(lambda:None)) or not hasattr(original,'__wrapped__'):raise ValueError('Original owner callable has already been replaced')
 if original.__wrapped__.__code__!=expected or original.__wrapped__.__globals__ is not source.__dict__:raise ValueError('Original owner function binding changed')
 if original.cache_parameters()!=dict(maxsize=262144,typed=False):raise ValueError('Original owner cache contract changed')
 return original


class Activation:
 def __init__(self,source,original,lookup,report,hashes,index_hash):
  self.source=source;self.original=original;self.lookup=lookup;self.report=report;self.hashes=hashes;self.index_hash=index_hash;self.active=True
 def __enter__(self):return self
 def __exit__(self,*exc):self.restore();return False
 def restore(self):
  if not self.active:return self.report
  if self.source.owner_at is not self.lookup.owner_at:raise RuntimeError('r5 owner callable was replaced by another hook; refusing to overwrite it')
  self.source.owner_at=self.original;self.active=False
  self.report['restoration']=dict(restored_exact_original_callable=self.source.owner_at is self.original,callable=_callable_binding(self.source.owner_at),accelerated_cache_info=self.lookup.owner_at.cache_info()._asdict())
  changes=[str(p) for p,h in self.hashes.items() if _sha(p)!=h]
  if self.source.INDEX is not self.lookup.index or _index_hash(self.source.INDEX)!=self.index_hash:changes.append('source owner index')
  if _json_hash(self.source._owners())!=json.loads((HERE/'candidate_binding.json').read_text())['ordered_owners_sha256']:changes.append('ordered owner snapshot')
  self.report['restoration']['changed_immutable_inputs']=changes
  self.report['status']='restored' if not changes else 'failed_changed_inputs'
  if changes:raise RuntimeError('r5 immutable inputs changed: '+repr(changes))
  return self.report


def activate(source,*,opt_in=False,export_revision=None):
 """Use opt_in from an explicit --r5-owner-prefilter CLI flag, never by default."""
 if opt_in is not True or export_revision!='r5':raise ValueError('Explicit r5-only opt-in is required')
 review=_validate_seal();lookup=OwnerLookup(source);original=_validate_original(source)
 expected=source.geo._SpatialIndex(32)
 for i,r in enumerate(lookup.owners):expected.add(i,r['polygon_xz_m'])
 if dict(expected.cells)!=dict(source.INDEX.cells):raise ValueError('Live owner index no longer matches the sealed ordered records')
 fixtures=json.loads((HERE/'fixtures.json').read_text());points=fixtures['benchmark_points'][::10]+fixtures['vertices'][::128]
 for p in points:
  if original.__wrapped__(*p)!=lookup.lookup(*p):raise ValueError('Activation owner parity failed at '+repr(p))
 # All fail-closed checks complete before the single process-local replacement.
 inputs=[HERE/REVIEW_NAME,HERE/'prefilter.py',HERE/'candidate_binding.json',Path(source.__file__),Path(source.geo.__file__),Path(__file__)]
 hashes={p:_sha(p) for p in inputs};index_hash=_index_hash(source.INDEX)
 report=dict(schema='riverstone.r5_owner_prefilter_activation.v1',status='active',export_revision='r5',explicit_opt_in=True,pid=os.getpid(),review_sha256=REVIEW_SHA256,activation_source_sha256=_sha(__file__),source_files_modified=False,scope='Only this process: upstream.owner_at callable; no adjacency/interface skip.',runtime_parity_points=len(points),before=dict(callable=_callable_binding(original),index_sha256=index_hash,ordered_owners_sha256=_json_hash(lookup.owners),source_hashes={str(p.relative_to(ROOT)):h for p,h in hashes.items()}),after=dict(callable=_callable_binding(lookup.owner_at),same_index_object=True,same_ordered_owner_objects=True),restoration=None)
 source.owner_at=lookup.owner_at
 return Activation(source,original,lookup,report,hashes,index_hash)
