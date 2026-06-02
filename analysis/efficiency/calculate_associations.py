# Calculate association scores and auxiliary variables


import os
import sys
import json
import time
import argparse
import subprocess
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
from tools.lcassociationtools import get_associations
from tools.lcassociationtools import get_cptolc_matrix, get_lctocp_matrix
from tools.lcassociationtools import get_mapping
from tools.lcassociationtools import get_cptolc_matrix_from_builtin
from tools.lcassociationtools import get_lctocp_matrix_from_builtin
from tools.tcassociationtools import get_ticl_candidate_matrices_from_trackster_associations
from tools.tcassociationtools import get_mapping as get_tc_mapping
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
    parser.add_argument('--make_plots', default=False, action='store_true')
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
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_ticl.json'))
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
    dfs_tc = []
    dfs_cp_tc = []
    n_empty_tstocpsimts_events = 0
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
            ticlcandidates = collections.get('ticlcandidates_merge')

            # do some event selection
            if len(caloparticles) < 2: continue

            # optional: filter caloparticles to keep only those from the primary interaction
            # and remove those from pileup.
            # this filtering is done based on the event() property, which is supposed to be 0
            # for the primary interaction and > 0 for pileup.
            caloparticles = [cp for cp in caloparticles if cp.eventId().event()==0]
            tstocpsimts_tsidx = None
            tstocpsimts_simtsidx = None
            tstocpsimts_sharedenergy = None
            tstocpsimts_score = None

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
                tstocpsimts_tsidx = collections.get('tstocpsimtsassociation_tsids')
                tstocpsimts_simtsidx = collections.get('tstocpsimtsassociation_simtsids')
                tstocpsimts_sharedenergy = collections.get('tstocpsimtsassociation_sharedenergy')
                tstocpsimts_score = collections.get('tstocpsimtsassociation_scores')

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

            # calculate and store TICLCandidate - CaloParticle metrics.
            # The scores are derived from the merged Trackster to
            # SimTrackster-from-CP shared-energy associations,
            # rather than the CP to LC associations as used above.
            # This avoids summing layer-normalized CP -> LC efficiencies
            # over multi-layer objects.
            if ticlcandidates is not None and tstocpsimts_tsidx is not None and len(tstocpsimts_tsidx) > 0:
                tc_ts_indices, tc_pur_matrix, tc_eff_matrix = get_ticl_candidate_matrices_from_trackster_associations(
                    ticlcandidates,
                    tstocpsimts_tsidx,
                    tstocpsimts_simtsidx,
                    tstocpsimts_sharedenergy,
                    tstocpsimts_score,
                    len(caloparticles))

                # get the mapping
                # note: purity-based, same as above for layerclusters and caloparticles.
                # note: output is the following:
                #       - cptotc_ids: 2D list with indices of matched ticlcandidates for each caloparticle.
                #       - tctocp_ids: simple 1D array with index of matched caloparticle for each ticlcandidate.
                #       - linked_tc_ids: simple 1D array with indices of ticlcandidates with a match
                #         (should be all ticlcandidates, unless a threshold was applied).
                #       - linked_tc_cp_ids: simple 1D array with indices of matched caloparticle for each ticlcandidate with a match.
                threshold = None
                tc_mapping = get_tc_mapping(tc_pur_matrix, threshold=threshold)
                (cptotc_ids, tctocp_ids) = tc_mapping
                linked_tc_ids = np.nonzero(tctocp_ids!=-1)[0]
                linked_tc_cp_ids = tctocp_ids[linked_tc_ids]

                # get purity and efficiency per ticlcandidate with respect to its matched caloparticle
                tc_pur = tc_pur_matrix[linked_tc_cp_ids, linked_tc_ids]
                tc_eff = tc_eff_matrix[linked_tc_cp_ids, linked_tc_ids]

                # get auxiliary variables for ticlcandidates
                tc_caloparticle_pt = np.array([caloparticles[int(idx)].pt() for idx in linked_tc_cp_ids])
                tc_caloparticle_eta = np.array([caloparticles[int(idx)].eta() for idx in linked_tc_cp_ids])
                tc_pt = np.array([ticlcandidates[int(idx)].pt() for idx in linked_tc_ids])
                tc_eta = np.array([ticlcandidates[int(idx)].eta() for idx in linked_tc_ids])
                tc_energy = np.array([ticlcandidates[int(idx)].energy() for idx in linked_tc_ids])
                tc_raw_energy = np.array([ticlcandidates[int(idx)].rawEnergy() for idx in linked_tc_ids])
                tc_ntracksters = np.array([len(ticlcandidates[int(idx)].tracksters()) for idx in linked_tc_ids])
                tc_nlayerclusters = np.array([
                    len(set(
                        lc_idx
                        for ts_ptr in ticlcandidates[int(idx)].tracksters()
                        for lc_idx in ts_ptr.get().vertices()
                    ))
                    for idx in linked_tc_ids
                ])

                # fill data structure for ticlcandidates
                df_tc = pd.DataFrame.from_dict({
                    'pur': tc_pur,
                    'eff': tc_eff,
                    'caloparticle_pt': tc_caloparticle_pt,
                    'caloparticle_eta': tc_caloparticle_eta,
                    'pt': tc_pt,
                    'eta': tc_eta,
                    'energy': tc_energy,
                    'raw_energy': tc_raw_energy,
                    'ntracksters': tc_ntracksters,
                    'nlayerclusters': tc_nlayerclusters,
                    'event': eventid
                })
                dfs_tc.append(df_tc)

                # initialize variables per caloparticle
                # note: in all these metrics, "primary" means the ticlcandidate with the highest efficiency
                #       out of all (purity-)matched ticlcandidates to this caloparticle
                cp_tc_eff_primary = np.zeros(len(caloparticles))
                cp_tc_pur_primary = np.zeros(len(caloparticles))
                cp_tc_eff_sum = np.zeros(len(caloparticles))
                cp_tc_ntc = np.zeros(len(caloparticles), dtype=int)

                # loop over caloparticles and matched ticlcandidates
                for cp_idx, tc_ids in enumerate(cptotc_ids):
                    cp_tc_ntc[cp_idx] = len(tc_ids) # number of matched ticlcandidates
                    if len(tc_ids) > 0:
                        this_cp_eff = tc_eff_matrix[cp_idx, tc_ids]
                        primary_idx = np.argmax(this_cp_eff)
                        primary_tc_id = tc_ids[primary_idx]
                        # (note: this is the ticlcandidate with highest efficiency
                        #        out of all ticlcandidates that are (purity-)matched to this caloparticle).
                        cp_tc_eff_primary[cp_idx] = this_cp_eff[primary_idx] # efficiency of highest-efficiency purity-matched ticlcandidate
                        cp_tc_pur_primary[cp_idx] = tc_pur_matrix[cp_idx, primary_tc_id] # purity of highest-efficiency purity-matched ticlcandidate
                        cp_tc_eff_sum[cp_idx] = np.sum(this_cp_eff) # efficiency sum of purity-matched ticlcandidates

                # add to data structure
                df_cp_tc = pd.DataFrame.from_dict({
                    'eff_primary': cp_tc_eff_primary,
                    'pur_primary': cp_tc_pur_primary,
                    'eff_sum': cp_tc_eff_sum,
                    'ntc': cp_tc_ntc,
                    'pt': np.array([cp.pt() for cp in caloparticles]),
                    'eta': np.array([cp.eta() for cp in caloparticles]),
                    'event': eventid
                })
                dfs_cp_tc.append(df_cp_tc)

            # check for existing but empty simtracksters
            elif ticlcandidates is not None and tstocpsimts_tsidx is not None:
                n_empty_tstocpsimts_events += 1

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
    if len(dfs_tc) > 0: df_tc = pd.concat(dfs_tc)
    else:
        df_tc = pd.DataFrame.from_dict({
            'pur': [],
            'eff': [],
            'pt': [],
            'eta': [],
            'candidate_pt': [],
            'candidate_eta': [],
            'candidate_energy': [],
            'candidate_raw_energy': [],
            'ntracksters': [],
            'nlayerclusters': [],
            'event': []
        })
    if len(dfs_cp_tc) > 0: df_cp_tc = pd.concat(dfs_cp_tc)
    else:
        df_cp_tc = pd.DataFrame.from_dict({
            'eff_primary': [],
            'pur_primary': [],
            'eff_sum': [],
            'ntc': [],
            'pt': [],
            'eta': [],
            'event': []
        })
    if n_empty_tstocpsimts_events > 0:
        msg = 'WARNING: Found empty Trackster-to-CP-SimTrackster association products'
        msg += f' in {n_empty_tstocpsimts_events} processed events. TICLCandidate metrics'
        msg += ' were not filled for those events.'
        print(msg)
    
    # write output file
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)
    lc_output = os.path.join(args.outputdir, 'metrics_lc.parquet')
    cp_lc_output = os.path.join(args.outputdir, 'metrics_cp_lc.parquet')
    tc_output = os.path.join(args.outputdir, 'metrics_tc.parquet')
    cp_tc_output = os.path.join(args.outputdir, 'metrics_cp_tc.parquet')
    df_lc.to_parquet(lc_output)
    df_cp.to_parquet(cp_lc_output)
    df_tc.to_parquet(tc_output)
    df_cp_tc.to_parquet(cp_tc_output)

    if args.make_plots:
        plotting_commands = [
            [sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_lc.py'), lc_output],
            [sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_cp.py'), cp_lc_output],
            [sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_tc.py'), tc_output],
        ]
        for command in plotting_commands:
            print(f'Running plotting script: {" ".join(command)}')
            subprocess.run(command, check=True)
