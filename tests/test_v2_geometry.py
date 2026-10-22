import math

import numpy as np
import pytest
from shapely import union_all

from luad_tissue.v2.geometry import GeometryError, power_geometry, sector_triangle_area


def jittered(n=14, pitch=8., sd=1.2, seed=1):
    rng = np.random.default_rng(seed)
    grid = np.stack(np.meshgrid(np.arange(n), np.arange(n)), -1).reshape(-1, 2) * pitch
    return grid + rng.normal(0, sd, grid.shape), rng.uniform(3.5, 7., len(grid))


def test_closed_form_areas_match_polygons_and_cells_never_overlap():
    xy, rho = jittered()
    g = power_geometry(xy, rho)
    polygons = [g.polygon(k, quad_segs=64) for k in range(g.n)]
    shapely_area = np.array([p.area for p in polygons])
    assert not g.hidden.any()
    assert np.allclose(shapely_area, g.area, rtol=2e-3, atol=1e-6)
    total = sum(p.area for p in polygons)
    assert abs(total - union_all(polygons).area) <= 1e-6 * total


def test_interfaces_are_symmetric_chords():
    xy, rho = jittered(seed=4)
    g = power_geometry(xy, rho)
    k = int(np.argmax(g.pair_length))
    a, b = g.polygon(int(g.pair_i[k]), 64), g.polygon(int(g.pair_j[k]), 64)
    shared = a.buffer(1e-6).intersection(b.buffer(1e-6)).area / 2e-6
    assert shared == pytest.approx(g.pair_length[k], rel=2e-3)
    assert np.allclose(np.hypot(*g.pair_normal.T), 1)


def test_isolated_bodies_are_disks_and_gaps_follow_h04():
    g = power_geometry(np.array([[0., 0.], [100., 0.]]), np.array([4., 5.]))
    assert g.area == pytest.approx([math.pi * 16, math.pi * 25], rel=1e-9)
    near = power_geometry(np.array([[0., 0.], [8.8, 0.]]), np.array([4., 4.]))
    far = power_geometry(np.array([[0., 0.], [9.2, 0.]]), np.array([4., 4.]))
    assert len(near.contacts(1.)[0]) == 1 and near.pair_length[0] == 0
    assert len(far.contacts(1.)[0]) == 0


def test_large_equal_radii_reduce_to_a_voronoi_tiling():
    grid = np.stack(np.meshgrid(np.arange(9), np.arange(9)), -1).reshape(-1, 2) * 10. + 1e-3 * np.arange(81)[:, None]
    g = power_geometry(grid, np.full(81, 20.))
    interior = [(r * 9 + c) for r in range(2, 7) for c in range(2, 7)]
    assert np.allclose(g.area[interior], 100., rtol=1e-3)


def test_signed_sector_area_is_additive():
    A, B = np.array([3., -1.]), np.array([-2., 4.])
    M = (A + B) / 2
    whole = sector_triangle_area(A, B, 2.5)
    assert whole == pytest.approx(sector_triangle_area(A, M, 2.5) + sector_triangle_area(M, B, 2.5))


def test_invalid_input_is_rejected():
    with pytest.raises(GeometryError):
        power_geometry(np.array([[0., 0.]]), np.array([0.]))
    with pytest.raises(GeometryError):
        power_geometry(np.array([[np.nan, 0.]]), np.array([1.]))
