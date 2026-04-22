# Test response calculation


import os
import sys
import argparse
import numpy as np
import pandas as pd
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_layercluster_layer
from tools.associationtools import get_associations
from tools.associationtools import get_cptolc_matrix, get_lctocp_matrix
from tools.geometrytools import get_caloparticle_hits_per_layer
from tools.geometrytools import get_caloparticle_energy_per_layer
from tools.geometrytools import get_layercluster_hits
from tools.associationtools import get_mapping
from tools.metrics import response


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('--input_config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    args = parser.parse_args()

    # initialize reader
    reader = Reader(args.input_config)

    # loop over input files
    for file_idx, inputfile in enumerate(args.inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(args.inputfiles)}...')
        events = Events(inputfile)

        # loop over events
        for event_idx, event in enumerate(events):
            if (event_idx+1) % 10 == 0:
                print(f'Reading event {event_idx+1}...', end='\r')

            # break loop
            if args.nentries > 0 and event_idx >= args.nentries: break

            # get collections
            collections = reader.read_event(event)
            caloparticles = collections['caloparticles']
            simclusters = collections['simclusters']
            calohits_ee = collections['calohitees']
            calohits_heb = collections['calohithebs']
            calohits_hef = collections['calohithefs']
            tracksters = collections['tracksters']
            layerclusters = collections['layerclusters']
            rechits_ee = collections['rechitees']
            rechits_heb = collections['rechithebs']
            rechits_hef = collections['rechithefs']

            # make dicts mapping ID to object
            calohit_map = {hit.id(): hit for hit in calohits_ee}
            calohit_map.update({hit.id(): hit for hit in calohits_heb})
            calohit_map.update({hit.id(): hit for hit in calohits_hef})
            rechit_map = {hit.id(): hit for hit in rechits_ee}
            rechit_map.update({hit.id(): hit for hit in rechits_heb})
            rechit_map.update({hit.id(): hit for hit in rechits_hef})

            # split caloparticles per layer
            cps_hits_per_layer = []
            for caloparticle in caloparticles:
                cps_hits_per_layer.append(get_caloparticle_hits_per_layer(caloparticle, calohit_map))
            
            # get layerclusters in the same format
            lcs_hits_per_layer = []
            for layercluster in layerclusters:
                layer = get_layercluster_layer(layercluster)
                lc_hits_per_layer = {layer: get_layercluster_hits(layercluster, rechit_map)}
                lcs_hits_per_layer.append(lc_hits_per_layer)

            # calculate associations
            associations = get_associations(
                cps_hits_per_layer=cps_hits_per_layer,
                lcs_hits_per_layer=lcs_hits_per_layer,
                sum_lc_per_layer = False)
            eff_matrix = get_cptolc_matrix(associations)
            pur_matrix = get_lctocp_matrix(associations)

            # make mapping based on purity
            mapping = get_mapping(pur_matrix)
            (lc_ids, cp_ids) = mapping

            # calculate metrics for calo particles
            cps_energy_per_layer = []
            for cp_hits_per_layer in cps_hits_per_layer:
                cps_energy_per_layer.append(get_caloparticle_energy_per_layer(cp_hits_per_layer, normalize=False))
            cp_layer, cp_res = response(caloparticles, cps_energy_per_layer, layerclusters, lc_ids, flatten=True)
