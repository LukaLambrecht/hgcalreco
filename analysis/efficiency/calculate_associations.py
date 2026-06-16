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


def calculate_lc_event_metrics(collections, caloparticles, eventid, args):
    '''
    Calculate LayerCluster-to-CaloParticle metrics for a single event.

    Returns:
    - df_lc: one row per purity-matched LayerCluster.
    - df_cp_lc: one row per CaloParticle/layer with the summed LC efficiency.
    '''
    layerclusters = collections['layerclusters']

    # Case 1: recalculate LC-CP associations from rechits and CaloParticle hits.
    if args.recalculate:
        calohits_ee = collections['calohitees']
        calohits_heb = collections['calohithebs']
        calohits_hef = collections['calohithefs']
        rechits_ee = collections['rechitees']
        rechits_heb = collections['rechithebs']
        rechits_hef = collections['rechithefs']

        # Keep the calohit map construction as in the original code, even
        # though the current association calculation uses the rechit map below.
        calohit_map = {hit.id(): hit for hit in calohits_ee}
        calohit_map.update({hit.id(): hit for hit in calohits_heb})
        calohit_map.update({hit.id(): hit for hit in calohits_hef})
        rechit_map = {hit.id(): hit for hit in rechits_ee}
        rechit_map.update({hit.id(): hit for hit in rechits_heb})
        rechit_map.update({hit.id(): hit for hit in rechits_hef})

        cps_hits_per_layer = []
        for caloparticle in caloparticles:
            # Use rechits when rebuilding the hit lists used by the association
            # calculation, matching the previous inline implementation.
            cps_hits_per_layer.append(get_caloparticle_hits_per_layer(caloparticle, rechit_map))

        lcs_hits_per_layer = []
        delta_r_threshold = None
        #delta_r_threshold = 1.5
        for layercluster in layerclusters:
            if delta_r_threshold is not None and mindr([layercluster], caloparticles) > delta_r_threshold:
                lcs_hits_per_layer.append({0: {}})
                continue
            layer = get_layercluster_layer(layercluster)
            lc_hits_per_layer = {layer: get_layercluster_hits(layercluster, rechit_map)}
            lcs_hits_per_layer.append(lc_hits_per_layer)

        associations = get_associations(
            caloparticles=caloparticles,
            layerclusters=layerclusters,
            cps_hits_per_layer=cps_hits_per_layer,
            lcs_hits_per_layer=lcs_hits_per_layer,
            remove_unmatched_rechits=args.remove_unmatched_rechits,
            sum_lc_per_layer=args.sum_lc_per_layer,
            delta_r_threshold=delta_r_threshold)
        eff_matrix = get_cptolc_matrix(associations)
        pur_matrix = get_lctocp_matrix(associations)

    # Case 2: use the flattened association products already stored in the file.
    else:
        lctocp_lcidx = collections['lctocpassociation_lcids']
        lctocp_cpidx = collections['lctocpassociation_cpids']
        lctocp_score = collections['lctocpassociation_scores']
        cptolc_cpidx = collections['cptolcassociation_cpids']
        cptolc_lcidx = collections['cptolcassociation_lcids']
        cptolc_efrac = collections['cptolcassociation_efracs']

        pur_matrix = get_lctocp_matrix_from_builtin(
            lctocp_lcidx,
            lctocp_cpidx,
            lctocp_score,
            len(layerclusters),
            len(caloparticles))
        eff_matrix = get_cptolc_matrix_from_builtin(
            cptolc_cpidx,
            cptolc_lcidx,
            cptolc_efrac,
            len(caloparticles),
            len(layerclusters))

    # From here on, both paths have the same purity and efficiency matrices.
    threshold = None
    mapping = get_mapping(pur_matrix, threshold=threshold)
    (cptolc_ids, lctocp_ids) = mapping
    linked_lc_ids = np.nonzero(lctocp_ids != -1)[0]
    linked_lc_cp_ids = lctocp_ids[linked_lc_ids]

    lc_pur = pur_matrix[linked_lc_cp_ids, linked_lc_ids]
    lc_eff = eff_matrix[linked_lc_cp_ids, linked_lc_ids]

    lc_pt = np.array([caloparticles[int(idx)].pt() for idx in linked_lc_cp_ids])
    lc_eta = np.array([caloparticles[int(idx)].eta() for idx in linked_lc_cp_ids])
    lc_layer = np.array([get_layercluster_layer(layerclusters[int(idx)]) for idx in linked_lc_ids])
    lc_subdet = np.array([get_layercluster_subdetid(layerclusters[int(idx)]) for idx in linked_lc_ids])

    if args.recalculate:
        cps_eff = efficiency(
            caloparticles,
            layerclusters,
            cps_hits_per_layer,
            lcs_hits_per_layer,
            cptolc_ids,
            flatten=False)
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

    layers_per_cp = [list(el.keys()) for el in cps_eff]
    cp_layer = np.array(sum(layers_per_cp, []))
    cp_eff = np.array([cps_eff[idx][l] for idx in range(len(caloparticles)) for l in layers_per_cp[idx]])

    df_lc = pd.DataFrame.from_dict({
        'pur': lc_pur,
        'eff': lc_eff,
        'pt': lc_pt,
        'eta': lc_eta,
        'layer': lc_layer,
        'subdet': lc_subdet,
        'event': eventid
    })

    df_cp_lc = pd.DataFrame.from_dict({
        #'res': cp_res,
        'eff': cp_eff,
        'layer': cp_layer,
        'event': eventid
    })

    return df_lc, df_cp_lc


def calculate_tc_event_metrics(collections, caloparticles,
        eventid = 0,
        cp_selected_ids = None):
    '''
    Calculate TICLCandidate-to-CaloParticle metrics for a single event.

    Returns:
    - df_tc: one row per non-empty TICLCandidate kept by the mapping.
    - df_cp_tc: one row per CaloParticle with TC-level summary metrics.
    - has_empty_association_product: True when the Trackster association product
      exists but has no entries, in which case no TICLCandidate metrics are
      filled for this event.
    '''

    # get extra collections needed
    ticlcandidates = collections.get('ticlcandidates_merge')
    simtracksters_from_cps = collections.get('simtracksters_from_cps')
    tstocpsimts_tsidx = collections.get('tstocpsimtsassociation_tsids')
    tstocpsimts_simtsidx = collections.get('tstocpsimtsassociation_simtsids')
    tstocpsimts_sharedenergy = collections.get('tstocpsimtsassociation_sharedenergy')

    # handle special cases
    if ticlcandidates is None or tstocpsimts_tsidx is None: return None, None, False
    if len(tstocpsimts_tsidx) == 0: return None, None, True

    # The flattened Trackster-to-CP-SimTrackster association stores indices into
    # the ticlSimTracksters:fromCPs collection. In CMSSW 17 that collection is
    # compressed: CaloParticles without reconstructed content are removed before
    # writing, so the SimTrackster index is not generally the CaloParticle index
    # anymore, especially in pileup samples. The original CaloParticle index is
    # preserved as the SimTrackster seedIndex().
    simts_to_cp_indices = None
    if simtracksters_from_cps is not None:
        simts_to_cp_indices = [int(simts.seedIndex()) for simts in simtracksters_from_cps]

    # get purity and efficiency matrix
    tc_ts_indices, pur_matrix, eff_matrix = get_ticl_candidate_matrices_from_trackster_associations(
        ticlcandidates,
        tstocpsimts_tsidx,
        tstocpsimts_simtsidx,
        tstocpsimts_sharedenergy,
        len(caloparticles),
        simts_to_cp_indices=simts_to_cp_indices)

    # printouts for testing
    #print(len(caloparticles))
    #print(pur_matrix.shape)
    #print(eff_matrix.shape)
    #print(pur_matrix[:2, :10])
    #print(np.max(pur_matrix, axis=0)[:10])
    #print(np.argmax(pur_matrix, axis=0)[:10])

    # problem: for samples with pileup, the association above does not seem to work properly,
    # and there are many ticl candidates with 0 maximum purity
    # (i.e. they don't seem to be matched to any of the pileup caloparticles)...
    # so it seems we need to put some minimum threshold to do the matching correctly,
    # but this removes also genuinly unmatched (i.e. noisy) ticlcandidates...

    # make mapping
    threshold = 1e-12
    tc_mapping = get_tc_mapping(
        pur_matrix,
        threshold=threshold,
        exclude_empty=True,
        candidate_constituents=tc_ts_indices)
    (cptotc_ids, tctocp_ids) = tc_mapping

    # select specific caloparticles (optional)
    if cp_selected_ids is not None:
        caloparticles = [caloparticles[int(cpidx)] for cpidx in cp_selected_ids]
        cptotc_ids = [cptotc_ids[int(cpidx)] for cpidx in cp_selected_ids]
        tctocp_ids = np.where(np.isin(tctocp_ids, cp_selected_ids), tctocp_ids, -1)

    # get index linking in more suitable format
    linked_tc_ids = np.nonzero(tctocp_ids != -1)[0] # indices of ticlcandidates with a match
    linked_tc_cp_ids = tctocp_ids[linked_tc_ids] # indices of caloparticles mapped to ticlcandidates with a match

    # printouts for testing
    #print('Calculated TiclCandidate to CaloParticle mapping:')
    #print(f'  - Found {len(linked_tc_ids)} out of {len(ticlcandidates)} TiclCandidates with a match.')
    #print('  - Found following numbers of ticlcandidates per caloparticle: ' + str([len(el) for el in cptotc_ids]))

    # get the purity and efficiency of ticlcandidates with a match
    tc_pur = pur_matrix[linked_tc_cp_ids, linked_tc_ids]
    tc_eff = eff_matrix[linked_tc_cp_ids, linked_tc_ids]

    # get other relevant variables
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

    # make dataframes
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

    cp_tc_eff_primary = np.zeros(len(caloparticles))
    cp_tc_pur_primary = np.zeros(len(caloparticles))
    cp_tc_eff_sum = np.zeros(len(caloparticles))
    cp_tc_ntc = np.zeros(len(caloparticles), dtype=int)

    for cp_idx, tc_ids in enumerate(cptotc_ids):
        cp_tc_ntc[cp_idx] = len(tc_ids)
        if len(tc_ids) > 0:
            this_cp_eff = eff_matrix[cp_idx, tc_ids]
            primary_idx = np.argmax(this_cp_eff)
            primary_tc_id = tc_ids[primary_idx]
            cp_tc_eff_primary[cp_idx] = this_cp_eff[primary_idx]
            cp_tc_pur_primary[cp_idx] = pur_matrix[cp_idx, primary_tc_id]
            cp_tc_eff_sum[cp_idx] = np.sum(this_cp_eff)

    df_cp_tc = pd.DataFrame.from_dict({
        'eff_primary': cp_tc_eff_primary,
        'pur_primary': cp_tc_pur_primary,
        'eff_sum': cp_tc_eff_sum,
        'ntc': cp_tc_ntc,
        'pt': np.array([cp.pt() for cp in caloparticles]),
        'eta': np.array([cp.eta() for cp in caloparticles]),
        'event': eventid
    })

    return df_tc, df_cp_tc, False


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_test')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('-r', '--recalculate', default=False, action='store_true')
    parser.add_argument('--input_config', default=None, nargs='+')
    parser.add_argument('--input_config_type', default='centralreco', choices=['centralreco', 'customreco'])
    parser.add_argument('--do_lc_level', default=False, action='store_true')
    parser.add_argument('--do_tc_level', default=False, action='store_true')
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
    dfs_cp_lc = []
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
       
            # get caloparticles
            collections = reader.read_event(event)
            caloparticles = collections['caloparticles']

            # do some event selection
            #if len(caloparticles) < 2: continue

            # optional: filter caloparticles to keep only those from the primary interaction
            # and remove those from pileup.
            # note: this filtering is done based on the event() property, which is supposed to be 0
            #       for the primary interaction and > 0 for pileup.
            # update: this approach worked well when recalculating the scores, but that approach is deprecated now.
            #         when using the builtin associations, it's better not to filter the caloparticles at this stage,
            #         but instead just store their indices, and select them only after the mapping has been made.
            #         this is to avoid matching layerclusters / ticlcandidates to random caloparticles
            #         if their actual match (a caloparticle from pileup) was removed.
            cp_is_from_primary_interaction = np.array([(cp.eventId().event()==0) for cp in caloparticles])
            cp_from_primary_interaction_ids = np.nonzero(cp_is_from_primary_interaction)[0]
            #print(f'Found {len(cp_from_primary_interaction_ids)} out of {len(caloparticles)} CaloParticles from primary interaction.')
            if args.recalculate: caloparticles = [caloparticles[idx] for idx in cp_from_primary_interaction_ids]

            # calculate layercluster to caloparticle associations
            if args.do_lc_level:
                df_lc, df_cp = calculate_lc_event_metrics(collections, caloparticles, eventid, args)
                dfs_lc.append(df_lc)
                dfs_cp_lc.append(df_cp)

            # calculate ticl candidate to caloparticle associations for this event
            if args.do_tc_level:
                df_tc, df_cp_tc, has_empty_association_product = calculate_tc_event_metrics(
                    collections, caloparticles,
                    cp_selected_ids = cp_from_primary_interaction_ids,
                    eventid = eventid)
                if df_tc is not None: dfs_tc.append(df_tc)
                if df_cp_tc is not None: dfs_cp_tc.append(df_cp_tc)
                if has_empty_association_product: n_empty_tstocpsimts_events += 1

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
    if len(dfs_cp_lc) > 0: df_cp = pd.concat(dfs_cp_lc)
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
        plotting_commands = []
        if args.do_lc_level:
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_lc.py'), lc_output])
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_cp.py'), cp_lc_output])
        if args.do_tc_level:
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_tc.py'), tc_output])
        for command in plotting_commands:
            print(f'Running plotting script: {" ".join(command)}')
            subprocess.run(command, check=True)
