# Tools for calculating association scores and matrices between objects.

# Typical use case: calculate association between LayerClusters and CaloParticles.


import os
import sys
import numpy as np

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_hits
from tools.geometrytools import get_caloparticle_hits_per_layer


def get_associations(
        caloparticles=None, calohits=None,
        layerclusters=None, rechits=None,
        cps_hits_per_layer=None,
        lcs_hits_per_layer=None,
        sum_lc_per_layer = False):
    '''
    Calculate association scores between collections of caloparticles and layerclusters.
    Input arguments:
    --- option 1 ---
    - caloparticles: collection of calo particles (CaloParticle)
    - layerclusters: collection of layer clusters (LayerCluster)
    - calohits: dict mapping detid to CaloHit objects
    - rechits: dict mapping detid to RecHit objects
    --- option 2 ---
    - cps_hits_per_layer: list of dicts of the form {layer: {detid: (energy, fraction)}}
    - lcs_hits_per_layer: same for layerclusters
    Returns:
    - A 2D list over pairs of calo particles and layer clusters,
      where each element is a dict with the following items:
        - "cptolc": calo particle to layer cluster association score.
          This can be though of as the calo particle efficiency,
          i.e. fraction of the calo particle reconstructed in this layer cluster.
          Note that the calo particle deposits are limited to the layer of the layer cluster.
        - "lctocp": layer cluster to calo particle association score.
          This can be though of as the layer cluster purity,
          i.e. fraction of layer cluster coming from this calo particle.
    '''

    # retrieve calo particle energy deposits per layer, if not yet provided
    if cps_hits_per_layer is None:
        cps_hits_per_layer = []
        for caloparticle in caloparticles:
            hits_per_layer = get_caloparticle_hits_per_layer(caloparticle, calohits)
            cps_hits_per_layer.append(hits_per_layer)

    # retrieve layer cluster energy deposits, if not yet provided
    if lcs_hits_per_layer is None:
        lcs_hits_per_layer = []
        for layercluster in layerclusters:
            layer = get_layercluster_layer(layercluster)
            hits_per_layer = {layer: get_layercluster_hits(layercluster, rechits)}
            lcs_hits_per_layer.append(hits_per_layer)

    # optional (mainly intended for testing):
    # for each layer cluster, replace hits of the layer cluster
    # by union of hits of all layer clusters in that layer
    # (to check if at least in that case the efficiency is high)
    if sum_lc_per_layer:
        sum_hits_per_layer = {}
        for lc_hits_per_layer in lcs_hits_per_layer:
            layer = list(lc_hits_per_layer.keys())[0]
            hits = list(lc_hits_per_layer.values())[0]
            if layer not in sum_hits_per_layer.keys(): sum_hits_per_layer[layer] = hits
            else:
                for detid, (energy, fraction) in hits.items():
                    if detid not in sum_hits_per_layer[layer].keys():
                        sum_hits_per_layer[layer][detid] = (energy, fraction)
                    else:
                        previous_fraction = sum_hits_per_layer[layer][detid][1]
                        sum_hits_per_layer[layer][detid] = (energy, previous_fraction + fraction)
        new_lcs_hits_per_layer = []
        for lc_hits_per_layer in lcs_hits_per_layer:
            layer = list(lc_hits_per_layer.keys())[0]
            new_hits = sum_hits_per_layer[layer]
            new_lcs_hits_per_layer.append({layer: new_hits})
        lcs_hits_per_layer = new_lcs_hits_per_layer

    # loop over pairs of calo particles and layer clusters
    res = []
    for cp_hits_per_layer in cps_hits_per_layer:
        res.append([])
        for lc_hits_per_layer in lcs_hits_per_layer:

            # check number of layers for this layer cluster (should be 1)
            layers = list(lc_hits_per_layer.keys())
            if len(layers) != 1:
                msg = f'Something went wrong; expected 1 layer but found {len(layers)} ({layers}).'
                raise Exception(msg)

            # calculate association between the two collections of hits
            associations = get_hitcollection_association(cp_hits_per_layer, lc_hits_per_layer, layers=layers)
            res[-1].append({
                "cptolc": associations[0],
                "lctocp": associations[1]
            })
        
    return res


def get_matrix(associations, field):
    '''
    Internal helper function to extract matrix of a particular association score.
    '''
    return np.array([[el[field] for el in row] for row in associations])

def get_cptolc_matrix(associations):
    '''
    Utility function to extract matrix of calo particle to layer cluster scores.
    '''
    return get_matrix(associations, "cptolc")

def get_lctocp_matrix(associations):
    '''
    Utility function to extract matrix of layer cluster to calo particle scores.
    '''
    return get_matrix(associations, "lctocp")


def get_hitcollection_association(hits_1, hits_2, layers=None):
    '''
    Base function for calculating association scores between two collections of hits.
    Input arguments:
    - hits_1 and hits_2: dicts of the form {layer number: dict of the form {detid: (energy, fraction)}}
    - layers: list of layers to restrict both hits_1 and hits_2
      (default: do not restrict, use the union of all layers)
    Returns:
    Tuple of two elements:
        - Association score of 1 to 2.
        - Association score of 2 to 1.
    '''

    # restrict hit collections to provided layers
    if layers is not None:
        hits_1 = {layer: hits_1.get(layer, {}) for layer in layers}
        hits_2 = {layer: hits_2.get(layer, {}) for layer in layers}
    
    # loop over the union of all layers present in the hit collections
    all_layers = list(set(list(hits_1.keys()) + list(hits_2.keys())))
    hits = {}
    for layer in all_layers:
        h1 = hits_1.get(layer, {})
        h2 = hits_2.get(layer, {})

        # complement both collections with non-shared detids
        for detid in h1.keys():
            if detid not in h2.keys(): h2[detid] = (0, 0)
        for detid in h2.keys():
            if detid not in h1.keys(): h1[detid] = (0, 0)

        # add to merged collection
        for detid in h1.keys():
            e_1, f_1 = h1[detid]
            e_2, f_2 = h2[detid]
            hits[detid] = (e_1, f_1, e_2, f_2)

    # calculate association of 1 to 2
    #numerator = sum([min((f_2 - f_1)**2, f_1**2)*e_1**2 for e_1, f_1, e_2, f_2 in hits.values()])
    numerator = sum([(1 - f_2)**2 * f_1**2 * e_1**2 for e_1, f_1, e_2, f_2 in hits.values()])
    denominator = sum([(f_1 * e_1)**2 for e_1, f_1, e_2, f_2 in hits.values()])
    if denominator < 1e-12: association_12 = 0
    else: association_12 = 1 - numerator / denominator

    # calculate association of 2 to 1
    #numerator = sum([min((f_2 - f_1)**2, f_2**2)*e_2**2 for e_1, f_1, e_2, f_2 in hits.values()])
    numerator = sum([(1 - f_1)**2 * f_2**2 * e_2**2 for e_1, f_1, e_2, f_2 in hits.values()])
    denominator = sum([(f_2 * e_2)**2 for e_1, f_1, e_2, f_2 in hits.values()])
    if denominator < 1e-12: association_21 = 0 
    else: association_21 = 1 - numerator / denominator

    # return results
    return (association_12, association_21)


def get_mapping(association_matrix):
    '''
    Calculate unique mapping between calo particles and layer clusters,
    based on a provided association score matrix.
    The association matrix is supposed to have shape (len(caloparticles), len(layerclusters)).
    Returns: a tuple of 2 elements:
    - list of lenght caloparticles, each element is an array with indices of mapped layerclusters
    - array of length layerclusters with indices of mapped caloparticles
    '''
    ncp, nlc = association_matrix.shape
    cp_ids = np.argmax(association_matrix, axis=0).astype(int)
    lc_ids = []
    for cp_idx in range(ncp):
        lc_ids.append(np.nonzero(cp_ids==cp_idx)[0])
    return (lc_ids, cp_ids)
