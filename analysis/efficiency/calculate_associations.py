# Calculate association scores and auxiliary variables


import os
import sys
import json
import time
import argparse
import numpy as np
import pandas as pd
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_subdetid
from tools.geometrytools import get_caloparticle_hits_per_layer
from tools.geometrytools import get_caloparticle_energy_per_layer
from tools.geometrytools import get_layercluster_hits
from tools.geometrytools import mindr
from tools.associationtools import get_associations
from tools.associationtools import get_cptolc_matrix, get_lctocp_matrix
from tools.associationtools import get_mapping
from tools.associationtools import get_cptolc_matrix_from_builtin
from tools.associationtools import get_lctocp_matrix_from_builtin
from tools.metrics import response
from tools.metrics import efficiency


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_test')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('-r', '--recalculate', default=False, action='store_true')
    parser.add_argument('--input_config', default=None, nargs='+')
    parser.add_argument('--input_config_type', default='centralreco', choices=['centralreco', 'customreco'])
    parser.add_argument('--remove_unmatched_rechits', default=False, action='store_true')
    parser.add_argument('--sum_lc_per_layer', default=False, action='store_true')
    parser.add_argument('--verbose', default=False, action='store_true')
    args = parser.parse_args()

    # set input configs
    input_configs = []
    if args.input_config is not None:
        # if input configs are specified on the command line, they take precedence
        input_configs = args.input_config[:]
    else:
        # else determine input configs automatically
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_baseline.json'))
        if args.recalculate:
            input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_hits.json'))
        else:
            input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_associations.json'))
    print('Found following input configs:')
    print(json.dumps(input_configs, indent=2))

    # initialize reader
    reader = Reader(input_configs)

    # loop over input files
    dfs_lc = []
    dfs_cp = []
    for file_idx, inputfile in enumerate(args.inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(args.inputfiles)}...')
        events = Events(inputfile)

        # loop over events
        for event_idx, event in enumerate(events):
            if args.verbose:
                if (event_idx+1) % 1 == 0: print(f'Reading event {event_idx+1}...')
            else:
                if (event_idx+1) % 1 == 0: print(f'Reading event {event_idx+1}...', end='\r')

            # make a unique event identifier
            # (note: only unique within one output file, not across files!)
            eventid = file_idx*1000000 + event_idx
       
            # get baseline collections
            collections = reader.read_event(event)
            caloparticles = collections['caloparticles']
            layerclusters = collections['layerclusters']

            # do some event selection
            if len(caloparticles) < 2: continue

            # optional: filter caloparticles to keep only those from the primary interaction
            # and remove those from pileup.
            # this filtering is done based on the event() property, which is supposed to be 0
            # for the primary interaction and > 0 for pileup.
            caloparticles = [cp for cp in caloparticles if cp.eventId().event()==0]

            # case of recalculating associations
            if args.recalculate:

                # load extra collections needed
                calohits_ee = collections['calohitees']
                calohits_heb = collections['calohithebs']
                calohits_hef = collections['calohithefs']
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
                    # note: use the rechit collection when building the
                    # caloparticle hit lists for association re-calculation!
                    cps_hits_per_layer.append(get_caloparticle_hits_per_layer(caloparticle, rechit_map))

                # get layerclusters in the same format
                lcs_hits_per_layer = []
                delta_r_threshold = None
                #delta_r_threshold = 1.5
                for layercluster in layerclusters:
                    # optional: skip this step for layerclusters that are too far away
                    # from any caloparticle anyway
                    if delta_r_threshold is not None and mindr([layercluster], caloparticles) > delta_r_threshold:
                        lcs_hits_per_layer.append({0: {}})
                        continue 
                    # get layer and hits
                    layer = get_layercluster_layer(layercluster)
                    lc_hits_per_layer = {layer: get_layercluster_hits(layercluster, rechit_map)}
                    lcs_hits_per_layer.append(lc_hits_per_layer)

                # calculate associations
                associations = get_associations(
                    caloparticles = caloparticles,
                    layerclusters = layerclusters,
                    cps_hits_per_layer = cps_hits_per_layer,
                    lcs_hits_per_layer = lcs_hits_per_layer,
                    remove_unmatched_rechits = args.remove_unmatched_rechits,
                    sum_lc_per_layer = args.sum_lc_per_layer,
                    delta_r_threshold = delta_r_threshold)
                eff_matrix = get_cptolc_matrix(associations)
                pur_matrix = get_lctocp_matrix(associations)

            # case of using builtin associations
            else:
                
                # load extra collections needed
                lctocp_lcidx = collections['lctocpassociation_lcids']
                lctocp_cpidx = collections['lctocpassociation_cpids']
                lctocp_score = collections['lctocpassociation_scores']
                cptolc_cpidx = collections['cptolcassociation_cpids']
                cptolc_lcidx = collections['cptolcassociation_lcids']
                cptolc_score = collections['cptolcassociation_scores']
                cptolc_efrac = collections['cptolcassociation_efracs']

                # get builtin associations
                pur_matrix = get_lctocp_matrix_from_builtin(lctocp_lcidx, lctocp_cpidx, lctocp_score, len(layerclusters), len(caloparticles))
                eff_matrix = get_cptolc_matrix_from_builtin(cptolc_cpidx, cptolc_lcidx, cptolc_efrac, len(caloparticles), len(layerclusters))

            # make mapping based on purity
            threshold = None
            #threshold = 0.1
            mapping = get_mapping(pur_matrix, threshold=threshold)
            (cptolc_ids, lctocp_ids) = mapping
            linked_lc_ids = np.nonzero(lctocp_ids!=-1)[0] # indices of layerclusters that are linked to a caloparticle
            linked_lc_cp_ids = lctocp_ids[linked_lc_ids] # indices of corresponding caloparticles

            # calculate metrics for layer clusters
            lc_pur = pur_matrix[linked_lc_cp_ids, linked_lc_ids]
            lc_eff = eff_matrix[linked_lc_cp_ids, linked_lc_ids]

            # calculate auxiliary variables for layer clusters
            lc_pt = np.array([caloparticles[int(idx)].pt() for idx in linked_lc_cp_ids])
            lc_eta = np.array([caloparticles[int(idx)].eta() for idx in linked_lc_cp_ids])
            lc_layer = np.array([get_layercluster_layer(layerclusters[int(idx)]) for idx in linked_lc_ids])
            lc_subdet = np.array([get_layercluster_subdetid(layerclusters[int(idx)]) for idx in linked_lc_ids])

            # calculate response per calo particle
            #cps_energy_per_layer = []
            #for cp_hits_per_layer in cps_hits_per_layer:
            #    energy_per_layer = get_caloparticle_energy_per_layer(cp_hits_per_layer, normalize=True)
            #    cps_energy_per_layer.append(energy_per_layer)
            #cps_res = response(caloparticles, cps_energy_per_layer, layerclusters, cptolc_ids, flatten=False)

            # calculate sum of layercluster efficiencies per layer and per calo particle.
            # update: do not sum layercluster efficiencies, but recalculate efficiency on unity of layerclusters.
            # note: this is not the same as the response, as only the energy fractions coming from the caloparticle
            #       are taken into account, not the full layercluster energy;
            #       hence this property can never by larger than one (while the response can).
            # note: cps_eff is a list (corresponding to caloparticles) of dicts of the form {layer: efficiency}
            if args.recalculate:
                cps_eff = efficiency(caloparticles, layerclusters, cps_hits_per_layer, lcs_hits_per_layer, cptolc_ids, flatten=False)
            else:
                cps_eff = []
                for cp_idx in range(len(caloparticles)):
                    this_cp_mask = (linked_lc_cp_ids == cp_idx)
                    layers = np.unique(lc_layer[this_cp_mask])
                    this_cp_eff = {}
                    for layer in layers:
                        this_layer_mask = (lc_layer == layer)
                        eff = np.sum(lc_eff[this_cp_mask & this_layer_mask])
                        this_cp_eff[layer] = eff
                    cps_eff.append(this_cp_eff)

            # flatten caloparticle metrics
            layers_per_cp = [list(el.keys()) for el in cps_eff]
            cp_layer = np.array(sum(layers_per_cp, []))
            #cp_res = np.array([cps_res[idx][l] for idx in range(len(caloparticles)) for l in layers_per_cp[idx]])
            cp_eff = np.array([cps_eff[idx][l] for idx in range(len(caloparticles)) for l in layers_per_cp[idx]])

            # store layercluster info in dataframe
            df_lc = pd.DataFrame.from_dict({
                'pur': lc_pur,
                'eff': lc_eff,
                'pt': lc_pt,
                'eta': lc_eta,
                'layer': lc_layer,
                'subdet': lc_subdet,
                'event': eventid
            })
            dfs_lc.append(df_lc)

            # store caloparticle info in dataframe
            df_cp = pd.DataFrame.from_dict({
                #'res': cp_res,
                'eff': cp_eff,
                'layer': cp_layer,
                'event': eventid
            })
            dfs_cp.append(df_cp)

            # stop processing if sufficient events have been processed
            if args.nentries > 0 and event_idx >= args.nentries-1: break

    # merge dataframes
    if len(dfs_lc) > 0: df_lc = pd.concat(dfs_lc)
    else:
        # this can happen if no events pass the selection,
        # e.g. if there are no reconstructed tracksters
        df_lc = pd.DataFrame.from_dict({
            'pur': [],
            'eff': [],
            'pt': [],
            'eta': [],
            'layer': [],
            'subdet': [],
            'event': []
        })
    if len(dfs_cp) > 0: df_cp = pd.concat(dfs_cp)
    else:
        # this can happen if no events pass the selection,
        # e.g. if there are no reconstructed tracksters
        df_cp = pd.DataFrame.from_dict({
            'res': [],
            'eff': [],
            'layer': [],
            'event': []
        })
    
    # write output file
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)
    df_lc.to_parquet(os.path.join(args.outputdir, 'metrics_lc.parquet'))
    df_cp.to_parquet(os.path.join(args.outputdir, 'metrics_cp.parquet'))
