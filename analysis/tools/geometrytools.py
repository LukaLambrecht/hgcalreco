import os
import sys
import ROOT
ROOT.gSystem.Load("libDataFormatsDetId")
ROOT.gSystem.Load("libDataFormatsForwardDetId")


def get_detid_subdetid(detid):
    detid = ROOT.DetId(detid)
    detid = ROOT.HGCalDetId(detid)
    det = detid.det()
    if det == ROOT.DetId.HGCalEE: return 0
    elif det == ROOT.DetId.HGCalHSi: return 1
    elif det == ROOT.DetId.HGCalHSc: return 2
    raise Exception('Detector type not recognized.')

def cast_detid(detid):
    detid = ROOT.DetId(detid)
    detid = ROOT.HGCalDetId(detid)
    subdetid = get_detid_subdetid(detid)
    if subdetid == 0: return ROOT.HGCSiliconDetId(detid)
    elif subdetid == 1: return ROOT.HGCSiliconDetId(detid)
    elif subdetid == 2: return ROOT.HGCScintillatorDetId(detid)
    raise Exception('Subdetector id not recognized.')

def get_detid_zside(detid):
    detid = cast_detid(detid)
    zside = detid.zside()
    return zside

def get_detid_layer(detid, absolute_value=False):
    detid = cast_detid(detid)
    layer = detid.layer()
    zside = detid.zside()
    subdetid = get_detid_subdetid(detid)
    if subdetid == 0: pass
    elif subdetid == 1: layer += 28 # exact value to check
    elif subdetid == 2: layer += 40 # exact value to check
    else: raise Exception('Subdetector id not recognized.')
    if absolute_value: return layer
    else: return zside * layer

def get_layercluster_subdetid(layercluster):
    '''
    Get subdetector ID of a layer cluster
    Note: assumes all hits are in the same subdetector!
    '''
    detid = layercluster.hitsAndFractions()[0].first
    subdetid = get_detid_subdetid(detid)
    return subdetid
   
def get_layercluster_layer(layercluster, **kwargs):
    '''
    Get layer number of a layer cluster
    Note: assumes all hits are in the same layer!
    '''
    detid = layercluster.hitsAndFractions()[0].first
    layer = get_detid_layer(detid, **kwargs)
    return layer

def get_layercluster_zside(layercluster):
    '''
    Get z-side of a layer cluster
    Note: assumes all hits are on the same side!
    '''
    detid = layercluster.hitsAndFractions()[0].first
    layer = get_detid_zside(detid)
    return layer

def get_simcluster_layers(simcluster, **kwargs):
    '''
    Get layer numbers with corresponding detids and fractions of a sim cluster
    '''
    res = {}
    hits = simcluster.hits_and_fractions()
    for hit in hits:
        detid = hit.first
        fraction = hit.second
        layer = get_detid_layer(detid, **kwargs)
        if layer in res: res[layer].append((detid, fraction))
        else: res[layer] = [(detid, fraction)]
    return res

def get_caloparticle_layers(caloparticle, split_per_simcluster=False, **kwargs):
    '''
    Get layer numbers with corresponding detids of a calo particle
    Note: If split_per_simcluster is False, the output is a simple dict
          of the form <layer number> -> <list of detids>.
          Else it is a list of such dicts (one per simcluster).
    '''
    
    # get result per simcluster
    res = []
    for sc_ref in caloparticle.simClusters():
        sc = sc_ref.get()
        res.append(get_simcluster_layers(sc, **kwargs))
    if split_per_simcluster: return res

    # merge
    merged = {}
    for el in res:
        for key, val in el.items():
            if key in merged: merged[key] += val
            else: merged[key] = val
    return merged
