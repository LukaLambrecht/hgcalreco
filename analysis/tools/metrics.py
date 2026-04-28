# Tools for calculating evaluation metrics.


import os
import sys
import numpy as np

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_zside
from tools.geometrytools import get_layercluster_energy_sum_per_layer
from tools.associationtools import get_associations


def caloparticle_response(caloparticle, cp_energy_per_layer, layerclusters):
    '''
    Calculate response, i.e. reconstructed energy over true energy, for a single CaloParticle
    Input arguments:
    - caloparticle: a given CaloParticle.
    - cp_energy_per_layer: pre-calculated energy per layer of the CaloParticle.
    - layerclusters: list of LayerClusters to include in the response calculation.
    '''
    
    # sum layer cluster energies per layer
    lc_energy_sum_per_layer = get_layercluster_energy_sum_per_layer(
        layerclusters,
        keys = cp_energy_per_layer.keys()
    )

    # normalize caloparticle energy
    # note: this is done because the energies per layer and the total CaloParticle energy are not the same quantity;
    #       the CaloParticle energy is the true particle energy, but the CaloParticle energy per layer
    #       is some measure of energy deposited/collected per layer, the sum of which is not necessarily equal to the former.
    total = sum(list(cp_energy_per_layer.values()))
    scale = caloparticle.energy() / total

    # calculate response
    response = {}
    for layer, cp_energy in cp_energy_per_layer.items():
        if cp_energy < 1e-12: continue
        lc_energy = lc_energy_sum_per_layer[layer]
        if lc_energy < 1e-12: continue # to check if this improves the distribution, but not clear if it makes sense
        cp_energy_scaled = scale*cp_energy
        response[layer] = lc_energy / cp_energy_scaled

    return response


def response(caloparticles, cps_energy_per_layer, layerclusters, lcs_ids, flatten=False):
    '''
    Calculate response, i.e. reconstructed energy over true energy.
    Same as caloparticle_response, but loop over multiple CaloParticles per event.
    Input arguments:
    - caloparticles: list of CaloParticles in event.
    - cps_energy_per_layer: pre-calculated energy per layer of each CaloParticle.
    - layerclusters: list of LayerClusters in event.
    - lcs_ids: mapping of CaloParticles to LayerClusters,
    '''

    response = []

    # loop over calo particles
    for caloparticle, cp_energy_per_layer, lc_ids in zip(caloparticles, cps_energy_per_layer, lcs_ids):

        # get layerclusters for this caloparticle
        lcs = [layerclusters[int(idx)] for idx in lc_ids]

        # calculate response
        response.append(caloparticle_response(caloparticle, cp_energy_per_layer, lcs))

    # flatten if requested
    if flatten:
        # make flat 1D arrays
        # note: if False, output is of the form [{layer: response}] with one element in the list per CaloParticle;
        #       if True, output is of the form (list of layer numbers, list of responses) where CaloParticles are concatenated.
        layers = np.array(sum([list(el.keys()) for el in response], []))
        response = np.array(sum([list(el.values()) for el in response], []))
        return (layers, response)

    else: return response


def caloparticle_efficiency(cp_hits_per_layer, lcs_hits_per_layer):
    '''
    Calculate efficiency, i.e. fraction of CaloParticle energy found in LayerClusters.
    Note: this is calculated re-using the same code as calculating the efficiency-based association
          between individual CaloParitcles and LayerClusters, but summing the LayerClusters per layer!
    Input arguments:
    - cp_hits_per_layer: pre-calculated hits (energy and fraction) per layer of a given CaloParticle.
    - lcs_hits_per_layer: same format for LayerClusters (assumed to be linked to this CaloParticle).
    '''
    
    efficiency = {}

    # loop over layers
    layers = np.unique([list(el.keys())[0] for el in lcs_hits_per_layer])
    for layer in layers:
        # find clusters for this layer
        this_lcs = [el for el in lcs_hits_per_layer if list(el.keys())[0]==layer]
        # calculate efficiency
        efficiency[layer] = get_associations(
            cps_hits_per_layer = [cp_hits_per_layer],
            lcs_hits_per_layer = this_lcs,
            sum_lc_per_layer=True)[0][0]["cptolc"]
    return efficiency


def efficiency(cps_hits_per_layer, lcs_hits_per_layer, lcs_ids, flatten=False):
    '''
    Calculate efficiency, i.e. fraction of CaloParticle energy found in LayerClusters.
    Same as caloparticle_efficiency, but loop over multiple CaloParticles per event.
    Input arguments:
    - cps_hits_per_layer: pre-calculated hits (energy and fraction) per layer for each CaloParticle.
    - lcs_hits_per_layer: same format for LayerClusters.
    - lcs_ids: mapping of CaloParticles to LayerClusters.
    '''

    efficiency = []

    # loop over calo particles
    for cp_hits_per_layer, lc_ids in zip(cps_hits_per_layer, lcs_ids):

        # get layerclusters for this caloparticle
        this_lcs_hits_per_layer = [lcs_hits_per_layer[int(idx)] for idx in lc_ids]

        # calculate efficiency
        efficiency.append(caloparticle_efficiency(cp_hits_per_layer, this_lcs_hits_per_layer))

    # flatten if requested
    if flatten:
        # make flat 1D arrays
        # note: if False, output is of the form [{layer: efficiency}] with one element in the list per CaloParticle;
        #       if True, output is of the form (list of layer numbers, list of efficiencys) where CaloParticles are concatenated.
        layers = np.array(sum([list(el.keys()) for el in efficiency], []))
        efficiency = np.array(sum([list(el.values()) for el in efficiency], []))
        return (layers, efficiency)

    else: return efficiency
