# Tools for calculating evaluation metrics.


import os
import sys
import numpy as np

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_zside
from tools.geometrytools import get_layercluster_energy_sum_per_layer


def response(caloparticles, cps_energy_per_layer, layerclusters, lcs_ids, flatten=False):
    '''
    Calculate response, i.e. reconstructed energy over true energy.
    Input arguments:
    - caloparticles: list of CaloParticles in event.
    - cps_energy_per_layer: pre-calculated energy per layer of each CaloParticle.
    - layerclusters: list of LayerClusters in event.
    - lcs_ids: mapping of CaloParticles to LayerClusters,
    '''
    
    response = []

    # loop over calo particles
    for cp, cp_energy_per_layer, lc_ids in zip(caloparticles, cps_energy_per_layer, lcs_ids):
        
        # sum layer cluster energies per layer
        lc_energy_sum_per_layer = get_layercluster_energy_sum_per_layer(
            [layerclusters[int(idx)] for idx in lc_ids],
            keys = cp_energy_per_layer.keys()
        )

        # normalize caloparticle energy
        # note: this is done because the energies per layer and the total CaloParticle energy are not the same quantity;
        #       the CaloParticle energy is the true particle energy, but the CaloParticle energy per layer
        #       is some measure of energy deposited/collected per layer, the sum of which is not necessarily equal to the former.
        total = sum(list(cp_energy_per_layer.values()))
        scale = cp.energy() / total
        #scale = 1

        # calculate response
        this_response = {}
        for layer, cp_energy in cp_energy_per_layer.items():
            if cp_energy < 1e-12: continue
            lc_energy = lc_energy_sum_per_layer[layer]
            if lc_energy < 1e-12: continue # to check if this improves the distribution, but not clear if it makes sense
            cp_energy_scaled = scale*cp_energy
            this_response[layer] = lc_energy / cp_energy_scaled

        response.append(this_response)

        # printouts for testing
        #print('----')
        #print(cp.energy())
        #print(cp.eta())
        #print(cp_energy_per_layer)
        #print(sum(list(cp_energy_per_layer.values())))
        #print(lc_ids)
        #print([get_layercluster_zside(layerclusters[int(lc_idx)]) for lc_idx in lc_ids])
        #print(lc_energy_sum_per_layer)
        #print(sum(list(lc_energy_sum_per_layer.values())))
        #print(response)
        #print(np.mean(np.array(list(this_response.values()))))

    if flatten:
        # make flat 1D arrays
        # note: if False, output is of the form [{layer: response}] with one element in the list per CaloParticle;
        #       if True, output is of the form (list of layer numbers, list of responses) where CaloParticles are concatenated.
        layers = np.array(sum([list(el.keys()) for el in response], []))
        response = np.array(sum([list(el.values()) for el in response], []))
        return (layers, response)

    return response
