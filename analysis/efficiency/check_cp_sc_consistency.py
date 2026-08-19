# Check whether the SimCluster-based and CaloParticle-based TICLCandidate efficiency
# (eff_sum) pipelines are mutually consistent: for a given primary CaloParticle, does
# the energy-weighted average of its *own constituent SimClusters'* eff_sum values
# match the eff_sum computed directly for that CaloParticle?
#
# Unlike check_sc_efficiency_vs_energy.py (which works from the already-produced
# metrics_*.parquet files and can only average per *event*, mixing together all
# primary particles in that event, since the parquet files don't carry a per-SimCluster
# parent-CaloParticle index), this script re-reads the re-reco'd file directly so it can
# group SimClusters by their actual parent CaloParticle (via CaloParticle.simClusters()
# refs), giving a true per-particle, apples-to-apples comparison.

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from calculate_associations import calculate_tc_event_metrics


def plot_scatter(xvals, yvals, xlabel, ylabel, color='dodgerblue'):
    fig, ax = plt.subplots()
    ax.scatter(xvals, yvals, color=color, s=10, alpha=0.3)
    lims = [0, max(1.05, np.max(xvals) if len(xvals) else 1, np.max(yvals) if len(yvals) else 1)]
    ax.plot(lims, lims, color='grey', linestyle='--', linewidth=1.5, label='y = x')
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    ax.legend(fontsize=13)
    fig.tight_layout()
    return fig, ax


if __name__=='__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-o', '--outputdir', default='test_output_cp_sc_consistency')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    args = parser.parse_args()

    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    input_configs = [
        os.path.join(topdir, 'configs/input_config_customreco_baseline.json'),
        os.path.join(topdir, 'configs/input_config_customreco_ticl.json'),
        os.path.join(topdir, 'configs/input_config_customreco_associations.json'),
        os.path.join(topdir, 'configs/input_config_customreco_sc_associations.json'),
    ]
    reader = Reader(input_configs, exclude=['tracksters', 'layerclusters'])

    cp_own_eff = []
    cp_weighted_sc_eff = []
    cp_energy = []
    cp_nsc = []
    cp_nsc_matched_in_table = []  # sanity check: how many of a CP's SimClusters were found in the SC table

    events = Events(args.inputfile)
    for event_idx, event in enumerate(events):
        if (event_idx+1) % 10 == 0: print(f'Reading event {event_idx+1}...', end='\r')
        if args.nentries > 0 and event_idx >= args.nentries: break

        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        simclusters = collections['simclusters']

        cp_is_from_primary_interaction = np.array([(cp.eventId().event()==0) for cp in caloparticles])
        cp_from_primary_interaction_ids = np.nonzero(cp_is_from_primary_interaction)[0]
        sc_is_from_primary_interaction = np.array([(sc.eventId().event()==0) for sc in simclusters])
        sc_from_primary_interaction_ids = np.nonzero(sc_is_from_primary_interaction)[0]
        # position within the SC-level per-event table (ascending original index -> row offset)
        sc_orig_to_row = {int(orig): row for row, orig in enumerate(sc_from_primary_interaction_ids)}

        df_tc, df_cp_tc, has_empty = calculate_tc_event_metrics(
            collections, caloparticles,
            cp_selected_ids=cp_from_primary_interaction_ids,
            eventid=event_idx)
        df_tc_sc, df_sc_tc, has_empty_sc = calculate_tc_event_metrics(
            collections, simclusters,
            cp_selected_ids=sc_from_primary_interaction_ids,
            eventid=event_idx,
            simtracksters_key='simtracksters_from_scs',
            tstosimts_tsids_key='tstoscsimtsassociation_tsids',
            tstosimts_simtsids_key='tstoscsimtsassociation_simtsids',
            tstosimts_sharedenergy_key='tstoscsimtsassociation_sharedenergy')
        if df_cp_tc is None or df_sc_tc is None: continue

        sc_eff = df_sc_tc['eff_sum'].values
        sc_energy = df_sc_tc['energy'].values

        for row_idx, cp_orig_idx in enumerate(cp_from_primary_interaction_ids):
            cp = caloparticles[int(cp_orig_idx)]
            sc_refs = cp.simClusters()
            this_sc_effs, this_sc_energies = [], []
            n_found = 0
            for sc_ref in sc_refs:
                orig_idx = int(sc_ref.key())
                row = sc_orig_to_row.get(orig_idx)
                if row is None: continue  # e.g. a non-primary-interaction SimCluster listed under this CP (shouldn't normally happen)
                n_found += 1
                this_sc_effs.append(sc_eff[row])
                this_sc_energies.append(sc_energy[row])
            if len(this_sc_energies) == 0 or np.sum(this_sc_energies) == 0: continue

            this_sc_effs = np.array(this_sc_effs)
            this_sc_energies = np.array(this_sc_energies)
            weighted_eff = np.sum(this_sc_effs*this_sc_energies)/np.sum(this_sc_energies)

            cp_own_eff.append(df_cp_tc['eff_sum'].values[row_idx])
            cp_weighted_sc_eff.append(weighted_eff)
            cp_energy.append(df_cp_tc['energy'].values[row_idx])
            cp_nsc.append(len(sc_refs))
            cp_nsc_matched_in_table.append(n_found)

    print()
    cp_own_eff = np.array(cp_own_eff)
    cp_weighted_sc_eff = np.array(cp_weighted_sc_eff)
    cp_energy = np.array(cp_energy)
    cp_nsc = np.array(cp_nsc)
    cp_nsc_matched_in_table = np.array(cp_nsc_matched_in_table)

    print(f'Found {len(cp_own_eff)} primary CaloParticles with >=1 SimCluster energy in the table.')
    print(f'SimClusters per CaloParticle found in SC table vs total (sanity check on linkage):'
          f' {np.sum(cp_nsc_matched_in_table)} / {np.sum(cp_nsc)}')
    print(f'Mean |cp_own_eff - cp_weighted_sc_eff| = {np.mean(np.abs(cp_own_eff-cp_weighted_sc_eff)):.4f}')
    print(f'Median |cp_own_eff - cp_weighted_sc_eff| = {np.median(np.abs(cp_own_eff-cp_weighted_sc_eff)):.4f}')
    print(f'Fraction of CaloParticles with own eff_sum in [0.99, 1.01]: {np.mean((cp_own_eff>=0.99)&(cp_own_eff<=1.01)):.4f}')
    print(f'Fraction of CaloParticles with own eff_sum == 0: {np.mean(cp_own_eff==0):.4f}')
    print(f'Fraction of CaloParticles with weighted_sc_eff == 0 (all own SimClusters eff_sum==0): {np.mean(cp_weighted_sc_eff==0):.4f}')
    pd.DataFrame.from_dict({
        'cp_own_eff': cp_own_eff, 'cp_weighted_sc_eff': cp_weighted_sc_eff,
        'cp_energy': cp_energy, 'cp_nsc': cp_nsc,
    }).to_parquet(os.path.join(args.outputdir, 'cp_sc_consistency.parquet'))

    fig, ax = plot_scatter(cp_own_eff, cp_weighted_sc_eff,
        'CaloParticle eff_sum (own, direct)', 'CaloParticle eff_sum (from energy-weighted SimClusters)')
    fig.savefig(os.path.join(args.outputdir, 'cp_own_vs_weighted_sc_eff.png'), dpi=200, bbox_inches='tight')
    plt.close(fig)

    diff = cp_weighted_sc_eff - cp_own_eff
    fig, ax = plt.subplots()
    yvals, edges = np.histogram(diff, bins=np.linspace(-1.1, 1.1, 45))
    ax.stairs(yvals, edges=edges, color='indianred', linewidth=3)
    ax.set_xlabel('weighted SC eff_sum - own CP eff_sum', fontsize=15)
    ax.set_ylabel('Number of CaloParticles', fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    fig.tight_layout()
    fig.savefig(os.path.join(args.outputdir, 'cp_vs_weighted_sc_eff_diff.png'), dpi=200, bbox_inches='tight')
    plt.close(fig)

    print(f'Plots written to {args.outputdir}')
