# Calculate association scores and auxiliary variables


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


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputfile', default='output_test.parquet')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('--sum_lc_per_layer', default=False, action='store_true')
    args = parser.parse_args()

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config_customreco.json')

    # initialize reader
    reader = Reader(input_config)

    # loop over input files
    dfs = []
    for file_idx, inputfile in enumerate(args.inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(args.inputfiles)}...')
        events = Events(inputfile)

        # loop over events
        for event_idx, event in enumerate(events):
            if (event_idx+1) % 10 == 0:
                print(f'Reading event {event_idx+1}...', end='\r')
        
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

            # do some event selection
            if len(caloparticles) < 2: continue
            if len(tracksters) < 1: continue

            # calculate associations
            associations = get_associations(caloparticles, calohit_map, layerclusters, rechit_map,
                sum_lc_per_layer = args.sum_lc_per_layer)
            eff_matrix = get_cptolc_matrix(associations)
            pur_matrix = get_lctocp_matrix(associations)

            # make association based on purity (least ambiguous of the two)
            pur_max_ids = np.argmax(pur_matrix, axis=0).astype(int) # index of calo particle for each layer cluster
            pur = pur_matrix[pur_max_ids, range(len(layerclusters))]
            eff = eff_matrix[pur_max_ids, range(len(layerclusters))]

            # calculate auxiliary variables
            pt = np.array([caloparticles[int(idx)].pt() for idx in pur_max_ids])
            eta = np.array([caloparticles[int(idx)].eta() for idx in pur_max_ids])
            layer = np.array([get_layercluster_layer(lc) for lc in layerclusters])

            # store in dataframe
            df = pd.DataFrame.from_dict({
                'pur': pur,
                'eff': eff,
                'pt': pt,
                'eta': eta,
                'layer': layer
            })
            dfs.append(df)

            # stop processing if sufficient events have been processed
            if args.nentries > 0 and event_idx > args.nentries: break

    # merge dataframes
    df = pd.concat(dfs)
    
    # write output file
    outputdir = os.path.dirname(args.outputfile)
    if len(outputdir) > 0 and not os.path.exists(outputdir): os.makedirs(outputdir)
    df.to_parquet(args.outputfile)
