# Tools for calculating association scores and matrices between objects.

# Typical use case: calculate association between LayerClusters and CaloParticles.


import os
import sys
import numpy as np
import bisect

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_hits
from tools.geometrytools import get_caloparticle_hits_per_layer


def find_in_sorted_list(elem, sorted_list):
    i = bisect.bisect_left(sorted_list, elem)
    if i != len(sorted_list) and sorted_list[i] == elem: return i
    return -1

def in_sorted_list(elem, sorted_list):
    i = find_in_sorted_list(elem, sorted_list)
    return (i != -1)


def get_associations(
        caloparticles = None, calohits = None,
        layerclusters = None, rechits = None,
        cps_hits_per_layer = None,
        lcs_hits_per_layer = None,
        remove_unmatched_rechits = False,
        sum_lc_per_layer = False,
        delta_r_threshold = None):
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
            # note: need to use the rechits for retrieving the energy here, not the calohits!
            #       this is to be consistent with the layercluster energy scale,
            #       and was checked to be in sync with the definition in CMSSW.
            hits_per_layer = get_caloparticle_hits_per_layer(caloparticle, rechits)
            cps_hits_per_layer.append(hits_per_layer)

    # retrieve layer cluster energy deposits, if not yet provided
    if lcs_hits_per_layer is None:
        lcs_hits_per_layer = []
        for layercluster in layerclusters:
            layer = get_layercluster_layer(layercluster)
            hits_per_layer = {layer: get_layercluster_hits(layercluster, rechits)}
            lcs_hits_per_layer.append(hits_per_layer)

    # optional: remove rechits that do not correspond to a calo hit (e.g. detector noise)
    if remove_unmatched_rechits:

        # make a list of all calohit detids
        all_calohit_detids = []
        for cp in cps_hits_per_layer:
            for layer, dets in cp.items():
                for detid in dets.keys():
                    bisect.insort(all_calohit_detids, detid)
        
        # remove rechits not in this list of calohits
        for lc in lcs_hits_per_layer:
            for layer, dets in lc.items():
                newdets = {}
                for detid, val in dets.items():
                    detid_to_check = detid.rawId()
                    if not in_sorted_list(detid_to_check, all_calohit_detids): continue
                    newdets[detid] = val
                lc[layer] = newdets

    # optional (mainly intended for testing):
    # for each layer cluster, replace hits of the layer cluster
    # by union of hits of all layer clusters in that layer
    # (to check if at least in that case the efficiency is high)
    if sum_lc_per_layer:
        sum_hits_per_layer = {}
        for lc_hits_per_layer in lcs_hits_per_layer:
            layer = list(lc_hits_per_layer.keys())[0]
            hits = list(lc_hits_per_layer.values())[0]
            if layer not in sum_hits_per_layer.keys(): sum_hits_per_layer[layer] = hits.copy()
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

    # precompute layer cluster norms (denominator)
    lc_norms = []
    for lc_hits_per_layer in lcs_hits_per_layer:
        layer = next(iter(lc_hits_per_layer))
        hits = lc_hits_per_layer[layer]
        denom = 0.
        for e, f in hits.values():
            denom += e ** 2 # (in principle f*e but f is always 1)
        lc_norms.append(denom)

    # pre-fetch eta and phi (used for quick filtering in the loop below)
    cps_eta = [cp.eta() for cp in caloparticles]
    cps_phi = [cp.phi() for cp in caloparticles]
    lcs_eta = [lc.eta() for lc in layerclusters]
    lcs_phi = [lc.phi() for lc in layerclusters]
    dr2max = None if delta_r_threshold is None else delta_r_threshold**2

    # loop over calo particles
    res = []
    for cp_idx, cp_hits_per_layer in enumerate(cps_hits_per_layer):
        res.append([])

        # precompute norm per layer (denominator)
        cp_norm_per_layer = {}
        for layer, hits in cp_hits_per_layer.items():
            denom = 0.
            for e, f in hits.values(): denom += (f * e) ** 2
            cp_norm_per_layer[layer] = denom

        # loop over layer clusters
        for lc_idx, lc_hits_per_layer in enumerate(lcs_hits_per_layer):

            # temp printouts for debugging
            #if cp_idx==0 and lc_idx==6:
            #    layer = list(lc_hits_per_layer.keys())[0]
            #    print('CaloParticle')
            #    for detid, val in cp_hits_per_layer.get(layer, {}).items(): print(detid, val)
            #    print('LayerCluster')
            #    for detid, val in lc_hits_per_layer[layer].items(): print(detid.rawId(), val)

            # check number of layers for this layer cluster (should be 1)
            layers = list(lc_hits_per_layer.keys())
            if len(layers) != 1:
                msg = f'Something went wrong; expected 1 layer but found {len(layers)} ({layers}).'
                raise Exception(msg)

            # do geometric prefiltering
            if dr2max is not None:
                delta_eta = cps_eta[cp_idx] - lcs_eta[lc_idx]
                delta_phi = cps_phi[cp_idx] - lcs_phi[lc_idx]
                delta_phi = (delta_phi + np.pi) % (2*np.pi) - np.pi
                dr2 = delta_eta**2 + delta_phi**2
                if dr2 > dr2max:
                    res[-1].append({"cptolc": 0, "lctocp": 0})
                    continue

            # get hits for layer cluster and calo particle in this layer
            layer = layers[0]
            lc_hits = lc_hits_per_layer[layer]
            if layer not in cp_hits_per_layer:
                res[-1].append({"cptolc": 0, "lctocp": 0})
                continue
            cp_hits = cp_hits_per_layer.get(layer, {})

            # calculate association between the two collections of hits
            associations = get_hitcollection_association(cp_hits, lc_hits,
                denominator_1 = cp_norm_per_layer.get(layer, 0),
                denominator_2 = lc_norms[lc_idx])
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
    Input arguments:
    - associations: a 2D list of dicts of the form {"cptolc": ..., "lctocp": ...}
      (i.e. the output of get_associations).
    Returns:
    - a 2D numpy array with the cptolc scores.
    '''
    return get_matrix(associations, "cptolc")

def get_lctocp_matrix(associations):
    '''
    Utility function to extract matrix of layer cluster to calo particle scores.
    Input arguments:
    - associations: a 2D list of dicts of the form {"cptolc": ..., "lctocp": ...}
      (i.e. the output of get_associations).
    Returns:
    - a 2D numpy array with the lctocp scores.
    '''
    return get_matrix(associations, "lctocp")


def get_cptolc_matrix_from_builtin(cpids, lcids, scores, ncp, nlc, invert=True):
    '''
    Utility function to extract matrix of calo particle to layer cluster scores.
    Input arguments:
    - cpids, lcids, scores: flat arrays of the same length representing the flattened map
    - ncp, nlc: number of caloparticles and number of layerclusters
    Returns:
    - a 2D numpy array with the cptolc scores.
      the shape of the array is (number of caloparticles, number of layerclusters)
    '''

    # initializations
    res = np.ones((ncp, nlc))

    # loop over flat map
    for cpidx, lcidx, score in zip(cpids, lcids, scores):
        res[cpidx, lcidx] = score

    # convert from 0-is-good to 1-is-good convention when requested.
    if invert: res = 1 - res
    
    # return the matrix
    return res
    

def get_lctocp_matrix_from_builtin(lcids, cpids, scores, nlc, ncp, invert=True):
    '''
    Utility function to extract matrix of layer cluster to calo particle scores.
    Input arguments:
    - lcids, cpids, scores: flat arrays of the same length representing the flattened map
    - nlc, ncp: number of layerclusters and number of caloparticles
    Returns:
    - a 2D numpy array with the lctocp scores.
      the shape of the array is (number of caloparticles, number of layerclusters)
    '''

    # initializations
    res = np.ones((ncp, nlc))

    # loop over flat map
    for lcidx, cpidx, score in zip(lcids, cpids, scores):
        res[cpidx, lcidx] = score

    # convert from 0-is-good to 1-is-good convention when requested.
    if invert: res = 1 - res
    
    # return the matrix
    return res


def get_hitcollection_association(hits_1, hits_2, denominator_1=None, denominator_2=None):
    '''
    Base function for calculating association scores between two collections of hits.
    Input arguments:
    - hits_1 and hits_2: dicts of the form {detid: (energy, fraction)}
    Returns:
    Tuple of two elements:
        - Association score of 1 to 2.
        - Association score of 2 to 1.
    '''

    # calculate denominators if not provided
    if denominator_1 is None: denominator_1 = sum((e*f)**2 for e, f in hits_1.values())
    if denominator_2 is None: denominator_2 = sum((e*f)**2 for e, f in hits_2.values())

    # get keys that are in both hits_1 and hits_2
    common = hits_1.keys() & hits_2.keys()

    # calculate association of 1 to 2
    numerator_12 = 0.
    # shared hits
    for detid in common:
        e1, f1 = hits_1[detid]
        _, f2 = hits_2[detid]
        # custom definition
        #numerator_12 += (1 - f2)**2 * f1**2 * e1**2
        # CMSSW-synced definition
        numerator_12 += min((f2-f1)**2, f1**2) * (f1 * e1)**2
    # non-shared hits (f2 = 0)
    for detid in hits_1.keys() - common:
        e1, f1 = hits_1[detid]
        numerator_12 += f1**2 * (f1 * e1)**2
    association_12 = 0. if denominator_1 < 1e-12 else 1. - numerator_12 / denominator_1

    # calculate association of 2 to 1
    numerator_21 = 0.
    # shared hits
    for detid in common:
        e2, f2 = hits_2[detid]
        _, f1 = hits_1[detid]
        # custom definition
        #numerator_21 += (1 - f1)**2 * f2**2 * e2**2
        # CMSSW-synced definition
        numerator_21 += min((f2-f1)**2, f2**2) * (f2 * e2)**2
    # non-shared hits (f1 = 0)
    for detid in hits_2.keys() - common:
        e2, f2 = hits_2[detid]
        numerator_21 += f2**2 * (f2 * e2)**2
    association_21 = 0. if denominator_2 < 1e-12 else 1. - numerator_21 / denominator_2

    return association_12, association_21


def get_mapping(association_matrix, threshold=None):
    '''
    Calculate unique mapping between calo particles and layer clusters,
    based on a provided association score matrix.
    The association matrix is supposed to have shape (len(caloparticles), len(layerclusters)).
    Returns: a tuple of 2 elements:
    - lc_ids: list of lenght caloparticles, each element is an array with indices of mapped layerclusters
    - cp_ids: array of length layerclusters with index of mapped caloparticle
    If a threshold is provided, cp_ids can contain -1 if no caloparticle is above threshold for a layercluster,
    and lc_ids can contain empty lists if no layercluster is linked to a caloparticle.
    '''
    ncp, nlc = association_matrix.shape
    cp_ids = np.argmax(association_matrix, axis=0).astype(int)
    if threshold is not None:
        scores = association_matrix[cp_ids, range(nlc)]
        mask = (scores < threshold).astype(bool)
        cp_ids[mask] = -1
    lc_ids = []
    for cp_idx in range(ncp):
        lc_ids.append(np.nonzero(cp_ids==cp_idx)[0])
    return (lc_ids, cp_ids)
