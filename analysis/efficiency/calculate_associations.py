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
from tools.tcassociationtools import get_all_ticl_candidate_trackster_indices
from tools.metrics import response
from tools.metrics import efficiency
from tools.truthbranchtools import get_level_partition
from tools.truthbranchtools import prune_truth
from tools.truthbranchtools import get_shared_energy_matrix
from tools.truthbranchtools import get_matrices_from_shared_energy
from tools.truthbranchtools import get_purity_matrix_from_scores
from tools.truthbranchtools import get_ticl_candidate_matrices


# truth Branches that can be used as truth objects (see tools/truthbranchtools.py):
# name of the truth object type in this script -> truth level in the MC-truth graph
TRUTH_BRANCH_LEVELS = {
    'truthbranch-signal': 'signal',
    'truthbranch-caloboundary': 'caloBoundary',
}


def calculate_lc_event_metrics(collections, caloparticles, eventid, args,
        lctotruth_lcids_key='lctocpassociation_lcids',
        lctotruth_truthids_key='lctocpassociation_cpids',
        lctotruth_scores_key='lctocpassociation_scores',
        truthtolc_truthids_key='cptolcassociation_cpids',
        truthtolc_lcids_key='cptolcassociation_lcids',
        truthtolc_scores_key='cptolcassociation_scores',
        matrices=None,
        truth_selected_ids=None):
    '''
    Calculate LayerCluster-to-truth-object metrics for a single event.
    Despite the "caloparticles" name (kept for backwards compatibility), the truth
    object list can be CaloParticles, SimClusters, or truth Branches (see tools/truthbranchtools.py):
    all expose the .pt()/.eta() used below. For CaloParticles and SimClusters, which collections to
    read the flattened associations from is controlled by the lctotruth_*/truthtolc_* keys (default:
    CaloParticle-based, exactly as before). Pass the SimCluster equivalents (see
    input_config_customreco_sc_associations.json) to get SimCluster-based metrics
    instead. For truth Branches, pass the precomputed (purity, efficiency) matrices
    with the matrices argument instead.
    Optionally, truth_selected_ids restricts the output to the given truth objects
    (after the mapping is made, i.e. LayerClusters mapped to other truth objects are dropped).

    Returns:
    - df_lc: one row per purity-matched LayerCluster.
    - df_cp_lc: one row per truth-object/layer with the summed LC efficiency.
    '''
    layerclusters = collections['layerclusters']

    # Case 0: use precomputed purity and efficiency matrices.
    if matrices is not None:
        pur_matrix, eff_matrix = matrices

    # Case 1: recalculate LC-CP associations from rechits and CaloParticle hits.
    elif args.recalculate:
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
        lctocp_lcidx = collections[lctotruth_lcids_key]
        lctocp_cpidx = collections[lctotruth_truthids_key]
        lctocp_score = collections[lctotruth_scores_key]
        cptolc_cpidx = collections[truthtolc_truthids_key]
        cptolc_lcidx = collections[truthtolc_lcids_key]
        cptolc_score = collections[truthtolc_scores_key]

        # purity = 1 - reco-normalized score (LC to CP),
        # efficiency = 1 - sim-normalized score (CP to LC, normalized per layer)
        pur_matrix = get_lctocp_matrix_from_builtin(
            lctocp_lcidx,
            lctocp_cpidx,
            lctocp_score,
            len(layerclusters),
            len(caloparticles))
        eff_matrix = get_cptolc_matrix_from_builtin(
            cptolc_cpidx,
            cptolc_lcidx,
            cptolc_score,
            len(caloparticles),
            len(layerclusters))

    # From here on, both paths have the same purity and efficiency matrices.
    threshold = None
    mapping = get_mapping(pur_matrix, threshold=threshold)
    (cptolc_ids, lctocp_ids) = mapping
    if matrices is not None:
        # LayerClusters without any shared energy with a truth object are unmatched
        # (for the precomputed matrices, all-zero columns would otherwise map to index 0)
        lctocp_ids = np.where(np.max(pur_matrix, axis=0) > 0, lctocp_ids, -1) if pur_matrix.shape[0] > 0 \
            else np.full(len(layerclusters), -1)
    if truth_selected_ids is not None:
        lctocp_ids = np.where(np.isin(lctocp_ids, truth_selected_ids), lctocp_ids, -1)
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

    truth_ids = range(len(caloparticles)) if truth_selected_ids is None else [int(idx) for idx in truth_selected_ids]
    layers_per_cp = {idx: list(cps_eff[idx].keys()) for idx in truth_ids}
    cp_layer = np.array(sum(layers_per_cp.values(), []))
    cp_eff = np.array([cps_eff[idx][l] for idx in truth_ids for l in layers_per_cp[idx]])

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
        cp_selected_ids = None,
        ticlcandidates_key='ticlcandidates_merge',
        simtracksters_key='simtracksters_from_cps',
        tstosimts_tsids_key='tstocpsimtsassociation_tsids',
        tstosimts_simtsids_key='tstocpsimtsassociation_simtsids',
        tstosimts_sharedenergy_key='tstocpsimtsassociation_sharedenergy',
        matrices=None):
    '''
    Calculate TICLCandidate-to-truth-object metrics for a single event.
    Despite the "caloparticles" name (kept for backwards compatibility), the truth
    object list can be CaloParticles, SimClusters, or truth Branches (see tools/truthbranchtools.py):
    all expose the .pt()/.eta() used below. For CaloParticles and SimClusters, which collections
    to read the SimTrackster/association products from is controlled by the
    simtracksters_key/tstosimts_*_key arguments (default: CaloParticle-based, exactly as before).
    Pass the SimCluster equivalents (see input_config_customreco_sc_associations.json)
    to get SimCluster-based metrics instead. For truth Branches, pass the precomputed
    (Trackster indices per TICLCandidate, purity, efficiency) with the matrices argument instead.

    Returns:
    - df_tc: one row per non-empty TICLCandidate kept by the mapping.
    - df_cp_tc: one row per truth object with TC-level summary metrics.
    - has_empty_association_product: True when the Trackster association product
      exists but has no entries, in which case no TICLCandidate metrics are
      filled for this event.
    '''

    # get extra collections needed
    ticlcandidates = collections.get(ticlcandidates_key)
    if ticlcandidates is None: return None, None, False

    # use precomputed matrices if provided
    if matrices is not None:
        tc_ts_indices, pur_matrix, eff_matrix = matrices
        return _calculate_tc_event_metrics_from_matrices(ticlcandidates, caloparticles,
            tc_ts_indices, pur_matrix, eff_matrix, eventid=eventid, cp_selected_ids=cp_selected_ids)

    simtracksters_from_cps = collections.get(simtracksters_key)
    tstocpsimts_tsidx = collections.get(tstosimts_tsids_key)
    tstocpsimts_simtsidx = collections.get(tstosimts_simtsids_key)
    tstocpsimts_sharedenergy = collections.get(tstosimts_sharedenergy_key)

    # handle special cases
    if tstocpsimts_tsidx is None: return None, None, False
    if len(tstocpsimts_tsidx) == 0: return None, None, True

    # The flattened Trackster-to-SimTrackster association stores indices into
    # the ticlSimTracksters collection (":fromCPs" for CaloParticles, the
    # inclusive/unlabeled instance for SimClusters). In CMSSW 17 the CP-derived
    # collection is compressed: CaloParticles without reconstructed content are
    # removed before writing, so the SimTrackster index is not generally the
    # truth-object index anymore, especially in pileup samples. The SimCluster-
    # derived instance skips unreconstructed SimClusters inline during
    # construction rather than compressing afterwards, but the effect on indexing
    # is the same. In both cases the original truth-object index is preserved as
    # the SimTrackster seedIndex().
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

    return _calculate_tc_event_metrics_from_matrices(ticlcandidates, caloparticles,
        tc_ts_indices, pur_matrix, eff_matrix, eventid=eventid, cp_selected_ids=cp_selected_ids)


def _calculate_tc_event_metrics_from_matrices(ticlcandidates, caloparticles,
        tc_ts_indices, pur_matrix, eff_matrix,
        eventid = 0,
        cp_selected_ids = None):
    '''
    Calculate TICLCandidate-to-truth-object metrics from the purity- and efficiency-like matrices
    (see calculate_tc_event_metrics for more info).
    '''

    # handle special case of no truth objects
    if len(caloparticles) == 0: return None, None, False

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
        'energy': np.array([cp.energy() for cp in caloparticles]),
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
    parser.add_argument('--gen_level', default=['cp'], nargs='+', choices=['cp', 'sc', 'both'] + list(TRUTH_BRANCH_LEVELS.keys()),
        help='Truth object(s) to use for LayerCluster- and TICLCandidate-level metrics (one or more of):'
             ' CaloParticles ("cp", default, unchanged behavior), SimClusters ("sc"),'
             ' "both" (= cp and sc), or truth Branches of the MC-truth graph at a given truth level'
             f' ({", ".join(TRUTH_BRANCH_LEVELS.keys())}; requires a re-reco output with the truth graph'
             ' associations, see tools/truthbranchtools.py). Applies to --do_lc_level and --do_tc_level alike.')
    parser.add_argument('--remove_unmatched_rechits', default=False, action='store_true')
    parser.add_argument('--sum_lc_per_layer', default=False, action='store_true')
    parser.add_argument('--make_plots', default=False, action='store_true')
    parser.add_argument('--verbose', default=False, action='store_true')
    args = parser.parse_args()
    gen_levels = set(args.gen_level)
    if 'both' in gen_levels: gen_levels = (gen_levels - {'both'}) | {'cp', 'sc'}
    branch_levels = [level for level in TRUTH_BRANCH_LEVELS if level in gen_levels]
    if args.recalculate and gen_levels != {'cp'}:
        raise NotImplementedError('--recalculate is only supported together with --gen_level cp.')

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
            if 'sc' in gen_levels:
                sc_config = os.path.join(topdir, f'configs/input_config_{args.input_config_type}_sc_associations.json')
                if os.path.exists(sc_config):
                    input_configs.append(sc_config)
                else:
                    print(f'WARNING: --gen_level sc requested but {sc_config} does not exist; skipping SimCluster-level associations.')
            if len(branch_levels) > 0:
                input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_truth_associations.json'))
    print('Found following input configs:')
    print(json.dumps(input_configs, indent=2))

    # initialize reader
    # note: skip setting up Handles for collections this invocation will never use.
    # "tracksters" (baseline.json's raw CLUE3DHigh Trackster collection) is not read
    # anywhere in this script; "layerclusters" is only used by --do_lc_level; and
    # "simclusters" only when --gen_level sc/both together with --do_lc_level and/or
    # --do_tc_level. Constructing a Handle for a collection carries a large, mostly
    # fixed memory cost (C++ dictionary/template instantiation) regardless of whether
    # the underlying product actually exists in the file, so skipping the ones that
    # are provably unused for this invocation meaningfully reduces peak memory.
    exclude = ['tracksters']
    if not args.do_lc_level:
        exclude.append('layerclusters')
    need_simclusters = 'sc' in gen_levels and (args.do_lc_level or args.do_tc_level)
    if not need_simclusters:
        exclude.append('simclusters')
    reader = Reader(input_configs, exclude=exclude)

    # loop over input files
    dfs_lc = []
    dfs_cp_lc = []
    dfs_lc_sc = []
    dfs_sc_lc = []
    dfs_tc = []
    dfs_cp_tc = []
    dfs_tc_sc = []
    dfs_sc_tc = []
    n_empty_tstocpsimts_events = 0
    n_empty_tstoscsimts_events = 0
    dfs_branch = {level: {'lc': [], 'truth_lc': [], 'tc': [], 'truth_tc': []} for level in branch_levels}
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

            # calculate layercluster to caloparticle and/or simcluster associations
            if args.do_lc_level:
                if 'cp' in gen_levels:
                    df_lc, df_cp = calculate_lc_event_metrics(collections, caloparticles, eventid, args)
                    dfs_lc.append(df_lc)
                    dfs_cp_lc.append(df_cp)
                if 'sc' in gen_levels:
                    simclusters = collections['simclusters']
                    df_lc_sc, df_sc_lc = calculate_lc_event_metrics(collections, simclusters, eventid, args,
                        lctotruth_lcids_key='lctoscassociation_lcids',
                        lctotruth_truthids_key='lctoscassociation_scids',
                        lctotruth_scores_key='lctoscassociation_scores',
                        truthtolc_truthids_key='sctolcassociation_scids',
                        truthtolc_lcids_key='sctolcassociation_lcids',
                        truthtolc_scores_key='sctolcassociation_scores')
                    dfs_lc_sc.append(df_lc_sc)
                    dfs_sc_lc.append(df_sc_lc)

            # calculate ticl candidate to caloparticle and/or simcluster associations
            if args.do_tc_level:
                if 'cp' in gen_levels:
                    df_tc, df_cp_tc, has_empty_association_product = calculate_tc_event_metrics(
                        collections, caloparticles,
                        cp_selected_ids = cp_from_primary_interaction_ids,
                        eventid = eventid)
                    if df_tc is not None: dfs_tc.append(df_tc)
                    if df_cp_tc is not None: dfs_cp_tc.append(df_cp_tc)
                    if has_empty_association_product: n_empty_tstocpsimts_events += 1
                if 'sc' in gen_levels:
                    simclusters = collections['simclusters']
                    sc_is_from_primary_interaction = np.array([(sc.eventId().event()==0) for sc in simclusters])
                    sc_from_primary_interaction_ids = np.nonzero(sc_is_from_primary_interaction)[0]
                    df_tc_sc, df_sc_tc, has_empty_association_product_sc = calculate_tc_event_metrics(
                        collections, simclusters,
                        cp_selected_ids = sc_from_primary_interaction_ids,
                        eventid = eventid,
                        simtracksters_key='simtracksters_from_scs',
                        tstosimts_tsids_key='tstoscsimtsassociation_tsids',
                        tstosimts_simtsids_key='tstoscsimtsassociation_simtsids',
                        tstosimts_sharedenergy_key='tstoscsimtsassociation_sharedenergy')
                    if df_tc_sc is not None: dfs_tc_sc.append(df_tc_sc)
                    if df_sc_tc is not None:
                        # Attach the parent CaloParticle's original index for each SimCluster
                        # row. SimCluster itself carries no back-reference to its parent
                        # CaloParticle, so this is built from CaloParticle.simClusters()
                        # (a RefVector into the same "simclusters" collection; .key() gives
                        # the original index), the same approach used to group SimClusters
                        # by parent CaloParticle in check_cp_sc_consistency.py.
                        sc_to_cp_index = {}
                        for cp_idx in cp_from_primary_interaction_ids:
                            for sc_ref in caloparticles[int(cp_idx)].simClusters():
                                sc_to_cp_index[int(sc_ref.key())] = int(cp_idx)
                        df_sc_tc['cp_index'] = np.array([
                            sc_to_cp_index.get(int(orig_idx), -1)
                            for orig_idx in sc_from_primary_interaction_ids
                        ])
                        dfs_sc_tc.append(df_sc_tc)
                    if has_empty_association_product_sc: n_empty_tstoscsimts_events += 1

            # calculate layercluster and/or ticl candidate to truth branch associations
            for level in branch_levels:
                graph = collections['truthgraph']
                truth, truth_selected_ids = get_level_partition(graph, TRUTH_BRANCH_LEVELS[level])
                # keep only truth objects that are selected or share energy with a reco object
                branch_id_arrays = []
                if args.do_lc_level: branch_id_arrays.append(collections['lctobranch_branchids'])
                if args.do_tc_level: branch_id_arrays.append(collections['tctobranch_branchids'])
                truth, truth_selected_ids = prune_truth(truth, truth_selected_ids, *branch_id_arrays)
                if args.do_lc_level:
                    layerclusters = collections['layerclusters']
                    lc_layers = np.array([get_layercluster_layer(lc) if len(lc.hitsAndFractions()) > 0 else -1
                                          for lc in layerclusters])
                    shared = get_shared_energy_matrix(
                        collections['lctobranch_lcids'], collections['lctobranch_branchids'],
                        collections['lctobranch_sharedenergy'], truth, len(layerclusters))
                    _, eff_matrix = get_matrices_from_shared_energy(shared, reco_groups=lc_layers)
                    pur_matrix = get_purity_matrix_from_scores(
                        collections['lctobranch_lcids'], collections['lctobranch_branchids'],
                        collections['lctobranch_scores'], truth, len(layerclusters))
                    df_lc_b, df_b_lc = calculate_lc_event_metrics(collections, truth, eventid, args,
                        matrices=(pur_matrix, eff_matrix),
                        truth_selected_ids=truth_selected_ids)
                    dfs_branch[level]['lc'].append(df_lc_b)
                    dfs_branch[level]['truth_lc'].append(df_b_lc)
                if args.do_tc_level:
                    ticlcandidates = collections['ticlcandidates_merge']
                    tc_ts_indices = get_all_ticl_candidate_trackster_indices(ticlcandidates)
                    pur_matrix, eff_matrix = get_ticl_candidate_matrices(ticlcandidates, tc_ts_indices,
                        collections['tctobranch_tsids'], collections['tctobranch_branchids'],
                        collections['tctobranch_sharedenergy'], truth)
                    df_tc_b, df_b_tc, _ = calculate_tc_event_metrics(collections, truth,
                        eventid = eventid,
                        cp_selected_ids = truth_selected_ids,
                        matrices = (tc_ts_indices, pur_matrix, eff_matrix))
                    if df_tc_b is not None: dfs_branch[level]['tc'].append(df_tc_b)
                    if df_b_tc is not None:
                        df_b_tc['pdgid'] = np.array([truth[int(idx)].pdgId() for idx in truth_selected_ids])
                        dfs_branch[level]['truth_tc'].append(df_b_tc)

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
    if len(dfs_lc_sc) > 0: df_lc_sc = pd.concat(dfs_lc_sc)
    else:
        df_lc_sc = pd.DataFrame.from_dict({
            'pur': [],
            'eff': [],
            'pt': [],
            'eta': [],
            'layer': [],
            'subdet': [],
            'event': []
        })
    if len(dfs_sc_lc) > 0: df_sc_lc = pd.concat(dfs_sc_lc)
    else:
        df_sc_lc = pd.DataFrame.from_dict({
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
    if len(dfs_tc_sc) > 0: df_tc_sc = pd.concat(dfs_tc_sc)
    else:
        df_tc_sc = pd.DataFrame.from_dict({
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
    if len(dfs_sc_tc) > 0: df_sc_tc = pd.concat(dfs_sc_tc)
    else:
        df_sc_tc = pd.DataFrame.from_dict({
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
    if n_empty_tstoscsimts_events > 0:
        msg = 'WARNING: Found empty Trackster-to-SC-SimTrackster association products'
        msg += f' in {n_empty_tstoscsimts_events} processed events. TICLCandidate metrics'
        msg += ' (SimCluster truth) were not filled for those events.'
        print(msg)

    # write output file
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)
    lc_output = os.path.join(args.outputdir, 'metrics_lc_cp.parquet')
    cp_lc_output = os.path.join(args.outputdir, 'metrics_cp_lc.parquet')
    tc_output = os.path.join(args.outputdir, 'metrics_tc_cp.parquet')
    cp_tc_output = os.path.join(args.outputdir, 'metrics_cp_tc.parquet')
    df_lc.to_parquet(lc_output)
    df_cp.to_parquet(cp_lc_output)
    df_tc.to_parquet(tc_output)
    df_cp_tc.to_parquet(cp_tc_output)
    if args.do_lc_level and 'sc' in gen_levels:
        lc_sc_output = os.path.join(args.outputdir, 'metrics_lc_sc.parquet')
        sc_lc_output = os.path.join(args.outputdir, 'metrics_sc_lc.parquet')
        df_lc_sc.to_parquet(lc_sc_output)
        df_sc_lc.to_parquet(sc_lc_output)
    if args.do_tc_level and 'sc' in gen_levels:
        tc_sc_output = os.path.join(args.outputdir, 'metrics_tc_sc.parquet')
        sc_tc_output = os.path.join(args.outputdir, 'metrics_sc_tc.parquet')
        df_tc_sc.to_parquet(tc_sc_output)
        df_sc_tc.to_parquet(sc_tc_output)
    branch_outputs = {}
    for level in branch_levels:
        for key, reco in [('lc', 'lc'), ('tc', 'tc')]:
            if not getattr(args, f'do_{reco}_level'): continue
            dfs_reco, dfs_truth = dfs_branch[level][key], dfs_branch[level][f'truth_{key}']
            df_reco = pd.concat(dfs_reco) if len(dfs_reco) > 0 else pd.DataFrame()
            df_truth = pd.concat(dfs_truth) if len(dfs_truth) > 0 else pd.DataFrame()
            reco_output = os.path.join(args.outputdir, f'metrics_{reco}_{level}.parquet')
            truth_output = os.path.join(args.outputdir, f'metrics_{level}_{reco}.parquet')
            df_reco.to_parquet(reco_output)
            df_truth.to_parquet(truth_output)
            branch_outputs[(level, reco)] = (reco_output, truth_output)

    if args.make_plots:
        plotting_commands = []
        if args.do_lc_level:
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_lc.py'), lc_output])
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_cp.py'), cp_lc_output])
        if args.do_tc_level and 'cp' in gen_levels:
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_tc.py'), tc_output])
        if args.do_tc_level and 'sc' in gen_levels:
            plotting_commands.append([sys.executable, os.path.join(os.path.dirname(__file__), 'plot_metrics_tc.py'), tc_sc_output,
                '--truth-inputfile', sc_tc_output, '--truth-mode', 'sc'])
        for command in plotting_commands:
            print(f'Running plotting script: {" ".join(command)}')
            subprocess.run(command, check=True)
