# Tools for calculating association scores and matrices between objects.

# Typical use case: calculate association between LayerClusters and CaloParticles.


import os
import sys
import numpy as np

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_layer


def response(caloparticles, cps_energy_per_layer, layerclusters, lcs_ids, flatten=False):
    
    response = []

    # loop over calo particles
    for cp, cp_energy_per_layer, lc_ids in zip(caloparticles, cps_energy_per_layer, lcs_ids):
        
        # sum layer cluster energies per layer
        lc_energies = np.array([layerclusters[int(idx)].energy() for idx in lc_ids])
        lc_layers = np.array([get_layercluster_layer(layerclusters[int(idx)]) for idx in lc_ids])
        lc_energy_sum_per_layer = {layer: 0 for layer in cp_energy_per_layer.keys()}
        for layer in np.unique(lc_layers):
            energy_sum = np.sum(lc_energies[lc_layers==layer])
            lc_energy_sum_per_layer[layer] = energy_sum

        # normalize caloparticle energy
        total = sum(list(cp_energy_per_layer.values()))
        scale = cp.energy() / total

        # calculate response
        this_response = {}
        for layer, cp_energy in cp_energy_per_layer.items():
            if cp_energy < 1e-12: continue
            cp_energy_scaled = scale*cp_energy
            this_response[layer] = lc_energy_sum_per_layer[layer] / cp_energy_scaled

        response.append(this_response)

    if flatten:
        # make flat 1D arrays
        layers = np.array(sum([list(el.keys()) for el in response], []))
        response = np.array(sum([list(el.values()) for el in response], []))
        return (layers, response)

    return response
