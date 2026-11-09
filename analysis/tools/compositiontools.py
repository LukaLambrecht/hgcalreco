# Tools for calculating the composition of reco and truth objects in terms of HGCAL subdetectors
# (CE-E silicon "ee", CE-H silicon "hsi", CE-H scintillator "hsci").
#
# Typical use case: investigate which part of HGCAL the LayerClusters of a TICLCandidate
# (and the energy of its matched truth object) come from.


import os
import numpy as np
import pandas as pd


# subdetector names, in order, and the corresponding DetId::Detector values
SUBDETS = ['ee', 'hsi', 'hsci']
DETID_DETECTORS = {8: 0, 9: 1, 10: 2} # HGCalEE, HGCalHSi, HGCalHSc -> index in SUBDETS


def get_layercluster_info(layerclusters):
    '''
    Get the subdetector index (in SUBDETS, or -1 if unknown) and energy of each LayerCluster.
    Note: the subdetector is taken from the seed DetId (bits 28-31 of the raw id),
          which is much faster than casting DetIds for O(100k) LayerClusters per event.
    '''
    subdets = np.array([DETID_DETECTORS.get((lc.seed().rawId() >> 28) & 0xF, -1) for lc in layerclusters], dtype=int)
    energies = np.array([lc.energy() for lc in layerclusters], dtype=float)
    return subdets, energies


def get_ticl_candidate_composition(ticlcandidates, lc_subdets, lc_energies):
    '''
    Get the number of LayerClusters and their energy per subdetector for each TICLCandidate.
    The energy of a LayerCluster shared by several Tracksters is counted with its share
    (1 / vertex multiplicity), as in TICL; the number of LayerClusters counts unique LayerClusters.
    Returns:
    - a DataFrame with one row per TICLCandidate (index = TICLCandidate index) and columns
      nlc_<subdet> and e_<subdet> for each subdetector;
    - a boolean mask of length nlc indicating which LayerClusters are used in any TICLCandidate.
    '''
    ntc = len(ticlcandidates)
    nlc = np.zeros((ntc, len(SUBDETS)), dtype=int)
    elc = np.zeros((ntc, len(SUBDETS)))
    used = np.zeros(len(lc_subdets), dtype=bool)
    for tc_idx, tc in enumerate(ticlcandidates):
        lc_fractions = {}
        for ts_ptr in tc.tracksters():
            trackster = ts_ptr.get()
            for lc_idx, multiplicity in zip(trackster.vertices(), trackster.vertex_multiplicity()):
                lc_fractions[int(lc_idx)] = lc_fractions.get(int(lc_idx), 0.) + 1. / max(multiplicity, 1.)
        if len(lc_fractions) == 0: continue
        lc_ids = np.array(list(lc_fractions.keys()), dtype=int)
        fractions = np.array(list(lc_fractions.values()))
        subdets = lc_subdets[lc_ids]
        valid = (subdets >= 0)
        np.add.at(nlc[tc_idx], subdets[valid], 1)
        np.add.at(elc[tc_idx], subdets[valid], (lc_energies[lc_ids] * fractions)[valid])
        used[lc_ids] = True
    data = {}
    for idx, subdet in enumerate(SUBDETS):
        data[f'nlc_{subdet}'] = nlc[:, idx]
        data[f'e_{subdet}'] = elc[:, idx]
    return pd.DataFrame(data), used


def get_event_layercluster_summary(lc_subdets, lc_energies, used_in_tc):
    '''
    Get a one-row summary of all LayerClusters in an event, per subdetector:
    number of LayerClusters and their total energy (nlc_<subdet>, e_<subdet>),
    and the same for the LayerClusters used in any TICLCandidate (nlc_tc_<subdet>, e_tc_<subdet>).
    '''
    row = {}
    for idx, subdet in enumerate(SUBDETS):
        mask = (lc_subdets == idx)
        row[f'nlc_{subdet}'] = int(np.sum(mask))
        row[f'e_{subdet}'] = float(np.sum(lc_energies[mask]))
        row[f'nlc_tc_{subdet}'] = int(np.sum(mask & used_in_tc))
        row[f'e_tc_{subdet}'] = float(np.sum(lc_energies[mask & used_in_tc]))
    return row


def get_truth_composition(truth_ids, lc_ids, shared_energies, lc_subdets, selected_truth_ids):
    '''
    Get the energy per subdetector of the given truth objects, as the sum of their shared energy
    with all LayerClusters (from a flattened truth-to-LayerCluster or LayerCluster-to-truth map).
    Note: this only counts energy in cells that are part of a LayerCluster.
    Input arguments:
    - truth_ids, lc_ids, shared_energies: flat arrays of the same length representing the map.
    - lc_subdets: subdetector index for each LayerCluster.
    - selected_truth_ids: truth ids (as used in truth_ids) for which to return the composition.
    Returns a DataFrame with one row per selected truth object and columns truthe_<subdet>.
    '''
    truth_ids = np.asarray(truth_ids, dtype=np.int64)
    lc_ids = np.asarray(lc_ids, dtype=np.int64)
    shared_energies = np.asarray(shared_energies, dtype=float)
    selected_truth_ids = np.asarray(selected_truth_ids, dtype=np.int64)
    position = {int(t): idx for idx, t in enumerate(selected_truth_ids)}
    energies = np.zeros((len(selected_truth_ids), len(SUBDETS)))
    if len(truth_ids) > 0 and len(selected_truth_ids) > 0:
        mask = np.isin(truth_ids, selected_truth_ids)
        rows = np.array([position[int(t)] for t in truth_ids[mask]], dtype=int)
        subdets = lc_subdets[lc_ids[mask]]
        valid = (subdets >= 0)
        np.add.at(energies, (rows[valid], subdets[valid]), shared_energies[mask][valid])
    return pd.DataFrame({f'truthe_{subdet}': energies[:, idx] for idx, subdet in enumerate(SUBDETS)})


# Tools for analysing the stored output of analysis/efficiency/calculate_associations.py (with --do_composition).

# labels and colours per subdetector (fixed order, same as SUBDETS)
SUBDET_LABELS = {'ee': 'CE-E', 'hsi': 'CE-H silicon', 'hsci': 'CE-H scintillator'}
SUBDET_COLORS = {'ee': '#2a78d6', 'hsi': '#eb6834', 'hsci': '#1baf7a'}

# truth object types and labels (same as in run-hgcal-reco-scan/plot_grid_result.py)
TRUTH_TYPES = {
    'cp': 'CaloParticle',
    'sc': 'SimCluster',
    'truthbranch-signal': 'TruthBranch ("signal") particle',
    'truthbranch-caloboundary': 'TruthBranch ("caloBoundary") particle',
}

# truth categories based on the fraction of the truth energy (in LayerClusters) in CE-E
TRUTH_CATEGORIES = {
    'ee': {'label': r'CE-E dominated ($f_{CE-E} \geq 2/3$)', 'range': (2./3, np.inf), 'color': '#2a78d6'},
    'mixed': {'label': r'Mixed ($1/3 < f_{CE-E} < 2/3$)', 'range': (1./3, 2./3), 'color': '#6b6b6b'},
    'h': {'label': r'CE-H dominated ($f_{CE-E} \leq 1/3$)', 'range': (-np.inf, 1./3), 'color': '#eb6834'},
}


def add_fractions(df, prefix, outprefix):
    '''
    Add columns <outprefix><subdet> with the fraction per subdetector
    of the columns <prefix><subdet> (NaN if the total is zero).
    '''
    total = sum(df[f'{prefix}{s}'] for s in SUBDETS)
    for s in SUBDETS:
        df[f'{outprefix}{s}'] = np.where(total > 0, df[f'{prefix}{s}'] / total.where(total > 0, 1), np.nan)
    return df


def get_truth_category(f_ee):
    '''Get the truth category (key in TRUTH_CATEGORIES) for an array of CE-E energy fractions.'''
    f_ee = np.asarray(f_ee)
    category = np.full(len(f_ee), '', dtype=object)
    for key, info in TRUTH_CATEGORIES.items():
        low, high = info['range']
        mask = (f_ee >= low) & (f_ee <= high) if key != 'mixed' else (f_ee > low) & (f_ee < high)
        category[mask] = key
    return category


def load_composition(effdir, truth_type='truthbranch-signal'):
    '''
    Load the TICLCandidate and truth object dataframes for a given truth type
    from an efficiency output directory, and link them
    (via the truth_index and primary_tc_index columns stored by calculate_associations.py).
    Returns:
    - df_tc: one row per TICLCandidate matched to a selected (primary-interaction) truth object,
      with composition columns (nlc_<subdet>, e_<subdet>), fractions (fn_<subdet>: LayerCluster count,
      fe_<subdet>: energy), the index of the matched truth object (truth_index),
      whether it is the primary TICLCandidate of that truth object (is_primary),
      and the category of the matched truth object (category).
    - df_truth: one row per selected truth object, with its composition (truthe_<subdet>),
      fractions (ftruth_<subdet>), category (see TRUTH_CATEGORIES),
      the composition of its primary TICLCandidate (columns of df_tc with prefix "primary_", NaN if none),
      and the combined composition of all its matched TICLCandidates (prefix "all_", NaN if none).
    '''
    df_tc = pd.read_parquet(os.path.join(effdir, f'metrics_tc_{truth_type}.parquet'))
    df_truth = pd.read_parquet(os.path.join(effdir, f'metrics_{truth_type}_tc.parquet'))
    if 'nlc_ee' not in df_tc.columns or 'truthe_ee' not in df_truth.columns:
        raise Exception(f'No composition columns found in {effdir} (run with --do_composition).')
    if 'truth_index' not in df_tc.columns or 'primary_tc_index' not in df_truth.columns:
        raise Exception(f'No TICLCandidate - truth links found in {effdir} (produced with an older version).')

    # primary TICLCandidates
    primary_keys = df_truth[['event', 'truth_index', 'primary_tc_index']].rename(columns={'primary_tc_index': 'tc_index'})
    df_tc = df_tc.merge(primary_keys.assign(is_primary=True), on=['event', 'truth_index', 'tc_index'], how='left')
    df_tc['is_primary'] = df_tc['is_primary'].eq(True)

    # fractions and categories
    add_fractions(df_tc, 'nlc_', 'fn_')
    add_fractions(df_tc, 'e_', 'fe_')
    add_fractions(df_truth, 'truthe_', 'ftruth_')
    df_truth['category'] = get_truth_category(df_truth['ftruth_ee'])
    df_tc = df_tc.merge(df_truth[['event', 'truth_index', 'category']], on=['event', 'truth_index'], how='left')

    # add primary TICLCandidate composition to truth objects
    columns = ['energy', 'raw_energy', 'nlayerclusters']
    columns += [f'{p}{s}' for p in ['nlc_', 'e_', 'fn_', 'fe_'] for s in SUBDETS]
    primary = df_tc[df_tc['is_primary']][['event', 'truth_index'] + columns]
    primary = primary.rename(columns={c: f'primary_{c}' for c in columns})
    df_truth = df_truth.merge(primary, on=['event', 'truth_index'], how='left')

    # add the combined composition of all matched TICLCandidates to truth objects
    # (sums over TICLCandidates, so a LayerCluster shared between TICLCandidates is counted once per
    #  TICLCandidate in all_nlc_<subdet>, while the energies are split according to the LayerCluster sharing)
    columns = ['energy', 'raw_energy'] + [f'{p}{s}' for p in ['nlc_', 'e_'] for s in SUBDETS]
    combined = df_tc.groupby(['event', 'truth_index'])[columns].sum().reset_index()
    combined = combined.rename(columns={c: f'all_{c}' for c in columns})
    df_truth = df_truth.merge(combined, on=['event', 'truth_index'], how='left')
    add_fractions(df_truth, 'all_nlc_', 'all_fn_')
    add_fractions(df_truth, 'all_e_', 'all_fe_')
    return df_tc, df_truth


def load_event_lc(effdir):
    '''Load the per-event LayerCluster summary (metrics_event_lc.parquet).'''
    return pd.read_parquet(os.path.join(effdir, 'metrics_event_lc.parquet'))
