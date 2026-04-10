# Tools for retrieving geometric information from objects.

# Typical use case: retrieve HGCal layer number(s) from LayerClusters and CaloParticles.


import ROOT
ROOT.gSystem.Load("libFWCoreFWLite")
ROOT.FWLiteEnabler.enable()
ROOT.gSystem.Load("libDataFormatsDetId")
ROOT.gSystem.Load("libDataFormatsForwardDetId")
ROOT.gInterpreter.Declare('#include "DataFormats/ForwardDetId/interface/HGCalDetId.h"')


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
    # offsets:
    # - EE starts at 0
    # - HSi starts at however many EE layers there are; exact value to check
    #   (and may also depend on exact geometry used).
    # - HSc physically starts only a few layers after HSi (i.e. the first few HE layers are all HSi),
    #   but the layer index seems to use the same offset.
    if subdetid == 0: pass # EE starts at 0
    elif subdetid == 1: layer += 26
    elif subdetid == 2: layer += 26
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

def get_layercluster_hits(layercluster, rechits):
    '''
    Get energy deposits of this layer cluster.
    Returns:
    - a dict of the form {detid: (energy, fraction)},
      where energy is the total energy deposted in that detector element,
      and  fraction is the fraction of that energy coming from this layercluster.
    '''
    layer = get_layercluster_layer(layercluster)
    hits = {}
    for hf in layercluster.hitsAndFractions():
        detid = hf.first
        fraction = hf.second
        if detid in rechits.keys(): energy = rechits[detid].energy()
        hits[detid] = (energy, fraction)
    return hits

def get_simcluster_detids_per_layer(simcluster, **kwargs):
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

def get_caloparticle_detids_per_layer(caloparticle, split_per_simcluster=False, **kwargs):
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
        res.append(get_simcluster_detids_per_layer(sc, **kwargs))
    if split_per_simcluster: return res

    # merge
    merged = {}
    for el in res:
        for key, val in el.items():
            if key in merged: merged[key] += val
            else: merged[key] = val
    return merged

def get_caloparticle_hits_per_layer(caloparticle, calohits):
    '''
    Returns:
    - a dict of the form {layer: {detid: (energy, fraction)}},
      where energy is the total energy deposited in that detector element,
      and  fraction is the fraction of that energy coming from this calo particle.
    Notes:
    - The total energy is taken from the calohits collection;
      this is not directly comparable to the energy from the rechits collection
      for the same detector element!
    '''
    caloparticle_per_layer = get_caloparticle_detids_per_layer(caloparticle)
    hits_per_layer = {}
    for layer, detids in caloparticle_per_layer.items():
        hits_per_layer[layer] = {}
        for (detid, fraction) in detids:
            energy = 0
            if detid in calohits.keys(): energy = calohits[detid].energy()
            hits_per_layer[layer][detid] = (energy, fraction)
    return hits_per_layer

def get_caloparticle_energy_per_layer(cp_hits_per_layer, normalize=False):
    '''
    Returns:
    - a dict of the form {layer: sum over energy of hits in this layer}
    Notes:
    - The total energy is taken from the calohits collection;
      this is not directly comparable to the energy from the rechits collection
      for the same detector element!
    '''
    energy_per_layer = {}
    for layer, hits in cp_hits_per_layer.items():
        energy = sum([hit[0]*hit[1] for hit in hits.values()])
        energy_per_layer[layer] = energy
    if normalize:
        total = sum(list(energy_per_layer.values()))
        for key, val in energy_per_layer.items():
            energy_per_layer[key] = val / total
    return energy_per_layer
