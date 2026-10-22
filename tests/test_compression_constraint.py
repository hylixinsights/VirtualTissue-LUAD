import copy
from pathlib import Path
import numpy as np
import pytest
from luad_tissue.io import read_json
from luad_tissue.v2.mechanics import Tissue
from luad_tissue.v2.autonomous import AutonomousSimulation
from v2_synthetic import synthetic_atlas

ROOT=Path(__file__).resolve().parents[1]

def setup():
    p=read_json(ROOT/'contracts/runtime-v2.json')
    p['mechanics']['compression_constraint']=dict(area_floor_fraction_by_label={},fallback_fraction=.3,max_backtracks=10)
    p['biology']['initialize_cycle_phase_from_annotation']=False
    return synthetic_atlas(),p

def test_extreme_motion_cannot_hide_or_delete_cells():
    atlas,p=setup();t=Tissue.from_atlas(atlas,p)
    idx,geo=t.geometry();initial=t.xy.copy();weights=t.kappa.copy()
    velocity=(t.centre-t.xy[idx])*30
    t.relax(idx,geo,.5,velocity)
    idx,geo=t.geometry()
    assert t.valid_areas(geo,t.floor_fractions()[idx]*t.A0_base[idx]).all()
    assert not geo.hidden.any() and t.check_invariants()['acting_total']==t.n_initial_roi
    assert np.array_equal(t.xy[t.fixed],initial[t.fixed]) and np.array_equal(t.kappa,weights)
    assert t.constraint_rejections>0
    assert np.allclose(t.path_um,np.linalg.norm(t.xy-initial,axis=1))

def test_unaffordable_growth_and_insertion_are_rejected_without_mutation():
    atlas,p=setup();t=Tissue.from_atlas(atlas,p)
    g=int(np.argmin(np.linalg.norm(t.xy-t.centre,axis=1)))
    area=t.A0.copy();xy=t.xy.copy();n=len(t.ids)
    assert not t.grow(g,area[g]*100)
    assert np.array_equal(t.A0,area)
    assert not t.can_insert(t.labels[g],t.xy[g]+.001,area[g]*100,t.kappa[g])
    assert len(t.ids)==n and np.array_equal(t.xy,xy)
    assert t.growth_blocked==1 and t.insertion_blocked==1

def test_local_jam_does_not_freeze_a_distant_island():
    from shapely.geometry import Point
    _,p=setup();p['mechanics']['compression_constraint'].update(fallback_fraction=.8,max_backtracks=1)
    xy=np.array([[0.,0.],[4.,0.],[100.,0.],[104.,0.]])
    polygons=[Point(*a).buffer(2,quad_segs=32) for a in xy]
    t=Tissue([1,2,3,4],['B_cell']*4,['roi']*4,xy,[q.area for q in polygons],polygons,[50,0],150,200,p)
    idx,geo=t.geometry();before=t.xy.copy()
    t.xy[1]=t.xy[0]+.01
    t.xy[2:]+=np.array([0.,1.])
    t.guard_motion(before,idx,geo)
    assert np.allclose(t.xy[2:]-before[2:],[0.,1.])
    assert t.valid_areas(t.geometry()[1],t.floor_fractions()*t.A0_base).all()
    assert t.global_rollbacks==0

def test_constrained_static_control_and_unknown_initial_cycle_phase():
    atlas,p=setup();s=AutonomousSimulation(atlas,p,'static',21).run(60)
    assert np.array_equal(s.tissue.xy,s.tissue.xy0)
    assert not s.events and not s.decisions
    assert s.summary()['final']['hidden']==0
    s=AutonomousSimulation(atlas,p,'S1',21)
    assert all(not b.get('initial_phase') for b in s.bio)
    s.run(120)
    assert all(m['hidden']==0 and m['area_min_over_floor']>=1-1e-8 for m in s.metrics)

@pytest.mark.skipif(not (ROOT/'outputs/atlas_B27.json.gz').exists(),reason='Private B27 atlas unavailable')
def test_measured_holdout_initial_fit_keeps_every_body_visible():
    p=read_json(ROOT/'contracts/runtime-v2-calibrated.json')
    t=Tissue.from_atlas(read_json(ROOT/'outputs/atlas_B27.json.gz'),p)
    assert t.fit['hidden']==0 and t.fit['fallback_iterations']>0
    idx,geo=t.geometry()
    assert np.max(abs(np.log(geo.area/t.measured_area)))<.01
    assert t.valid_areas(geo,t.floor_fractions()[idx]*t.A0_base[idx]).all()
    assert np.array_equal(t.xy,t.xy0)
