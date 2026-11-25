# Common definitions for the surface density study (see README.md).


import numpy as np


# Layer parameters of the D127 geometry, from the HGCAL geometry parameters (HGCalParameters: zLayerHex,
# rMinLayHex, rMaxLayHex), dumped with dump_layer_radii_cfg.py.
# Layer numbers 1-47 (CE-E: 1-26, CE-H: 27-47; the CE-H layers 34-47 have silicon inside and scintillator outside).

# |z| position (cm) of the silicon layers
# (the scintillator layers in CE-H sit 0.19 cm closer to the interaction point, which is neglected here)
LAYER_Z = {
    1: 322.161, 2: 323.136, 3: 325.218, 4: 326.193, 5: 328.275, 6: 329.250, 7: 331.332, 8: 332.307,
    9: 334.389, 10: 335.364, 11: 337.446, 12: 338.421, 13: 340.503, 14: 341.478, 15: 343.560, 16: 344.535,
    17: 346.617, 18: 347.592, 19: 350.002, 20: 350.977, 21: 353.384, 22: 354.359, 23: 356.766, 24: 357.741,
    25: 360.148, 26: 361.123,
    27: 367.966, 28: 374.271, 29: 380.576, 30: 386.881, 31: 393.186, 32: 399.491, 33: 405.796, 34: 412.106,
    35: 418.411, 36: 424.716, 37: 431.021, 38: 439.241, 39: 447.466, 40: 455.691, 41: 463.916, 42: 472.141,
    43: 480.366, 44: 488.591, 45: 496.816, 46: 505.041, 47: 513.266,
}

# radial range (cm) of the silicon part of each layer
_SI_RMIN = [31.4] * 26 + [34.86] * 7 + [41.86] * 4 + [48.34] * 10
_SI_RMAX = [154, 154, 154.995, 154.995, 156.049, 156.049, 157.102, 157.102, 158.156, 158.156, 159.21, 159.21,
            160.263, 160.263, 161.317, 161.317, 162.371, 162.371, 163.425, 163.425, 164.59, 164.59, 165.756, 165.756,
            166.922, 166.922,
            169.942, 172.115, 174.289, 176.462, 183.034, 191.018, 199.003, 153.705, 153.705, 153.705, 153.705,
            137.852, 137.852, 120.76, 120.76, 120.76, 120.76, 104.59, 104.59, 104.59, 104.59]
# radial range (cm) of the scintillator part of the CE-H layers 34-47
_SC_RMIN = [154.506, 154.506, 154.506, 154.506, 138.252, 138.252, 118.699, 118.699, 118.699, 118.699,
            104.183, 104.183, 104.183, 104.183]
_SC_RMAX = [200.506, 209.413, 215.616, 218.718, 233.116, 243.496, 254.339, 259.879, 259.879, 259.879,
            259.879, 259.879, 243.496, 243.496]
LAYER_SI_RMAX = {layer: _SI_RMAX[layer - 1] for layer in range(1, 48)}
# active radial range of each layer: from the inner edge of the silicon to the outer edge of the silicon or scintillator
# (the active area is approximated by a full ring; its real edges follow the wafer and tile boundaries)
LAYER_RMIN = {layer: _SI_RMIN[layer - 1] for layer in range(1, 48)}
LAYER_RMAX = {layer: (_SC_RMAX[layer - 34] if layer >= 34 else _SI_RMAX[layer - 1]) for layer in range(1, 48)}
LAYERS = sorted(LAYER_Z.keys())
N_EE_LAYERS = 26

# particle categories (in addition to all particles)
CATEGORIES = ['all', 'charged', 'neutral']
CATEGORY_LABELS = {'all': 'All particles', 'charged': 'Charged', 'neutral': 'Neutral'}

# PDG ids of (stable) charged particles, by absolute value
CHARGED_PDGIDS = {11, 13, 211, 321, 2212, 3112, 3222, 3312, 3334}


def layer_label(layer):
    '''Label of a layer, e.g. "Layer 27 (CE-H 1), |z| = 368.0 cm".'''
    part = f'CE-E {layer}' if layer <= N_EE_LAYERS else f'CE-H {layer - N_EE_LAYERS}'
    return f'Layer {layer} ({part}), |z| = {LAYER_Z[layer]:.1f} cm'


def ring_areas(r_edges, rmin=0., rmax=np.inf):
    '''Area (cm^2) of the rings between consecutive radii, restricted to the range [rmin, rmax].'''
    r_edges = np.clip(np.asarray(r_edges, dtype=float), rmin, rmax)
    return np.pi * (r_edges[1:]**2 - r_edges[:-1]**2)


def active_ring_areas(r_edges):
    '''Active area (cm^2) of the rings between consecutive radii per layer, array of shape (layers, radial bins).'''
    return np.array([ring_areas(r_edges, LAYER_RMIN[layer], LAYER_RMAX[layer]) for layer in LAYERS])


def load_particles(inputfile):
    '''Load the output of extract_boundary_particles.py: dict of per-particle arrays, plus the event index per particle.'''
    data = np.load(inputfile)
    particles = {key: data[key] for key in ['x', 'y', 'z', 'px', 'py', 'pz', 'pdgid']}
    offsets = data['event_offsets']
    particles['event'] = np.repeat(np.arange(len(offsets) - 1), np.diff(offsets))
    return particles, len(offsets) - 1


def get_layer_counts(particles, nevents, r_edges, zmin_boundary=290., min_momentum=0.):
    '''
    Extrapolate the selected particles in a straight line to each layer and count them per event and radial bin
    (summed over both endcaps), for each category. Particles crossing a layer outside its active radial range
    (LAYER_RMIN, LAYER_RMAX) are ignored.
    Selection: boundary crossing with zmin_boundary <= |z| < |z| of the first layer, moving away from the
    interaction point, and momentum >= min_momentum.
    Returns a dict category -> array of shape (events, layers, radial bins), and the number of selected particles per event.
    '''
    z0 = particles['z'].astype(float)
    pz = particles['pz'].astype(float)
    p = np.sqrt(particles['px'].astype(float)**2 + particles['py'].astype(float)**2 + pz**2)
    mask = (np.abs(z0) >= zmin_boundary) & (np.abs(z0) < LAYER_Z[LAYERS[0]]) & (z0 * pz > 0) & (p >= min_momentum)
    x0, y0, z0 = particles['x'][mask].astype(float), particles['y'][mask].astype(float), z0[mask]
    tx, ty = particles['px'][mask] / pz[mask], particles['py'][mask] / pz[mask]
    event = particles['event'][mask]
    charged = np.isin(particles['pdgid'][mask], list(CHARGED_PDGIDS))
    sel = {'all': np.ones(len(z0), dtype=bool), 'charged': charged, 'neutral': ~charged}
    nbins = len(r_edges) - 1
    counts = {cat: np.zeros((nevents, len(LAYERS), nbins)) for cat in CATEGORIES}
    for lidx, layer in enumerate(LAYERS):
        dz = np.sign(z0) * LAYER_Z[layer] - z0
        r = np.hypot(x0 + tx * dz, y0 + ty * dz)
        rbin = np.searchsorted(r_edges, r, side='right') - 1
        inrange = (rbin >= 0) & (rbin < nbins) & (r >= LAYER_RMIN[layer]) & (r < LAYER_RMAX[layer])
        for cat in CATEGORIES:
            m = sel[cat] & inrange
            counts[cat][:, lidx, :] = np.bincount(event[m] * nbins + rbin[m], minlength=nevents * nbins).reshape(nevents, nbins)
    return counts, np.bincount(event, minlength=nevents)
