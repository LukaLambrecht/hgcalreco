import os
import sys
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_caloparticle_layers


def efficiency(caloparticle, calohits, layercluster, rechits):
    '''
    Calculate various efficiency metrics for a given simcluster and layercluster.
    In more detail:
    - "efficiency": sim cluster efficiency, i.e. fraction of sim cluster reconstructed in this layer cluster.
    - "purity": layer cluster purity, i.e. fraction of layer cluster coming from this sim cluster.
    '''

    # find layer of layercluster
    layer = get_layercluster_layer(layercluster)

    # split caloparticle in layers
    caloparticle_layers = get_caloparticle_layers(caloparticle)

    # find truth energy from this caloparticle in detector elements
    # note: limited to the layer corresponding to the layer cluster!
    cp_hits = {}
    if layer in caloparticle_layers.keys():
        for detid, fraction in caloparticle_layers[layer]:
            energy = 0
            if detid in calohits.keys(): energy = calohits[detid].energy()
            cp_hits[detid] = (energy, fraction)

    # find reco energy from layer cluster in detector elements
    lc_hits = {}
    for hf in layercluster.hitsAndFractions():
        detid = hf.first
        fraction = hf.second
        if detid in rechits.keys(): energy = rechits[detid].energy()
        lc_hits[detid] = (energy, fraction)

    # complement both collections with non-shared detids
    for detid in cp_hits.keys():
        if detid not in lc_hits.keys(): lc_hits[detid] = (0, 0)
    for detid in lc_hits.keys():
        if detid not in cp_hits.keys(): cp_hits[detid] = (0, 0)

    # make merged collection
    hits = {}
    for detid in cp_hits.keys():
        cp_e, cp_f = cp_hits[detid]
        lc_e, lc_f = lc_hits[detid]
        hits[detid] = (cp_e, cp_f, lc_e, lc_f)

    # calculate efficiency
    numerator = sum([min((lc_f - cp_f)**2, cp_f**2)*cp_e**2 for cp_e, cp_f, lc_e, lc_f in hits.values()])
    denominator = sum([(cp_f*cp_e)**2 for cp_e, cp_f, lc_e, lc_f in hits.values()])
    if denominator < 1e-12:
        # this can happen if the calo particle has no hits in the layer of the provided superlcuster
        eff = 0
    else:
        # default case
        eff = 1 - numerator / denominator

    # calculate purity
    numerator = sum([min((lc_f - cp_f)**2, lc_f**2)*lc_e**2 for cp_e, cp_f, lc_e, lc_f in hits.values()])
    denominator = sum([(lc_f*lc_e)**2 for cp_e, cp_f, lc_e, lc_f in hits.values()])
    pur = 1 - numerator / denominator

    # group results
    result = {
        "efficiency": eff,
        "purity": pur
    }

    return result
