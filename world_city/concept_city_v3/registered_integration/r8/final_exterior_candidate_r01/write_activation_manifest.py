"""Bind actual final110 outputs; source totals alone never grant acceptance."""
import json,pathlib,sys
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a
D=pathlib.Path(__file__).resolve().parent
ref=lambda p:dict(path=a.rel(p),sha256=a.sha(p))
def main(binding,authored,precision,runtime,output):
 bp,ap,pp,rp=[a.source_file(p)for p in (binding,authored,precision,runtime)];op=(a.ROOT/output).resolve();op.relative_to(a.ROOT.resolve());assert not op.exists();b=a.load(bp);s=a.load(rp);assert s['r8_provenance']['binding_sha256']==a.digest(b)
 pz=pp.parent/'runtime_precision_ledger.json';wl=rp.parent/'runtime_winding_ledger.json';p=a.load(pz);w=a.load(wl);assert p['source']==ref(ap)and p['runtime_scene']==ref(pp);assert w['source_scene']==ref(pp)and w['derived_scene']==ref(rp)
 data=dict(schema='riverstone.wholecity.exterior_activation_candidate.v1',status='ACTUAL_SCENE_BUILT_VISUAL_AND_TRAVERSAL_PENDING',binding=ref(bp),authored_scene=ref(ap),precision_normalized_scene=ref(pp),scene=ref(rp),runtime_precision_ledger=ref(pz),runtime_winding_ledger=ref(wl),source_guard=ref(ap.parent/'surface_guard.json'),build_read_closure=ref(ap.parent/'build_read_closure.json'),counts=s['counts'],ordinary_holdings=110,withdrawn_proposal_retained_hall_domain=1,interpretation='Holdings and components are not a building count. Old building_masses metadata is planning inventory, not current built geometry.',limits=['Final registered visual review and all481 composed controller cases remain pending.','Ten exact runtime rows preserve float32 vertex sets but change rendering and derived collision normals. Precise source remains intact.','Seven projected-vertical nonzero source fragments remain represented; only exact float32 3D-zero faces are removed by the separate declared sanitation stage.','Interiors, economy, live city NPC navigation, wall walks and microtexture polish are outside this exterior/layout milestone.'])
 op.write_text(json.dumps(data,indent=2)+'\n');print(ref(op),flush=True)
if __name__=='__main__':main(*sys.argv[1:])
