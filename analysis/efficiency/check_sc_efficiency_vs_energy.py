# Check whether the SimCluster-level TICLCandidate total efficiency (eff_sum: summed
# over all matched TICLCandidates, not just the primary one) spike at 0 is driven by
# low-energy SimClusters, and whether that is consistent with the CaloParticle-level
# efficiency (which stays high) being an energy-weighted aggregate over its SimClusters.
#
# Uses the existing metrics_sc_tc.parquet / metrics_cp_tc.parquet produced by
# calculate_associations.py (--do_tc_level --gen_level both); no re-reco or
# re-running of the association calculation is needed, as long as those parquet
# files include the 'energy' column (added to calculate_tc_event_metrics's df_cp_tc
# alongside pt/eta).

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

METRIC = 'eff_sum'
METRIC_LABEL = 'SC/CP efficiency (total)'


def plot_hist(values, bins, xlabel, ylabel, color='dodgerblue', label=None, ax=None, fig=None):
    yvals, edges = np.histogram(values, bins=bins)
    if fig is None or ax is None:
        fig, ax = plt.subplots()
        ax.grid(visible=True, which='both', axis='both')
    ax.stairs(yvals, edges=edges, color=color, linewidth=3, label=label)
    if xlabel: ax.set_xlabel(xlabel, fontsize=15)
    if ylabel: ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    fig.tight_layout()
    return fig, ax


if __name__=='__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputdir', default='test_output_efficiency_cp_vs_sc')
    parser.add_argument('-o', '--outputdir', default='test_output_sc_efficiency_vs_energy')
    args = parser.parse_args()

    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    df_sc = pd.read_parquet(os.path.join(args.inputdir, 'metrics_sc_tc.parquet'))
    df_cp = pd.read_parquet(os.path.join(args.inputdir, 'metrics_cp_tc.parquet'))

    print(f'Loaded {len(df_sc)} SimCluster rows ({df_sc["event"].nunique()} events)'
          f' and {len(df_cp)} CaloParticle rows ({df_cp["event"].nunique()} events).')
    frac_zero = np.mean(df_sc[METRIC] == 0)
    print(f'Fraction of SimClusters with {METRIC} == 0: {frac_zero:.3f}')
    print(f'Fraction of CaloParticles with {METRIC} == 0: {np.mean(df_cp[METRIC] == 0):.3f}')

    # --- (1) efficiency vs energy: is the zero-efficiency population dominated by low energy? ---
    energy_bins = np.quantile(df_sc['energy'], np.linspace(0, 1, 11))
    energy_bins[0] = 0
    energy_bins = np.unique(energy_bins)
    frac_zero_per_bin, mean_eff_per_bin, median_energy_per_bin = [], [], []
    for lo, hi in zip(energy_bins[:-1], energy_bins[1:]):
        mask = (df_sc['energy'] >= lo) & (df_sc['energy'] < hi)
        if np.sum(mask) == 0: continue
        median_energy_per_bin.append(np.median(df_sc['energy'][mask]))
        frac_zero_per_bin.append(np.mean(df_sc[METRIC][mask] == 0))
        mean_eff_per_bin.append(np.mean(df_sc[METRIC][mask]))

    fig, ax = plt.subplots()
    ax.plot(median_energy_per_bin, frac_zero_per_bin, marker='o', linewidth=3, color='indianred', label=f'Fraction with {METRIC} = 0')
    ax.plot(median_energy_per_bin, mean_eff_per_bin, marker='o', linewidth=3, color='dodgerblue', label=f'Mean {METRIC}')
    ax.set_xlabel('SimCluster energy [GeV]', fontsize=15)
    ax.set_ylabel('Fraction / mean efficiency', fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    ax.legend(fontsize=13)
    ax.set_xscale('log')
    fig.tight_layout()
    fig.savefig(os.path.join(args.outputdir, 'sc_eff_vs_energy.png'), dpi=200, bbox_inches='tight')
    plt.close(fig)

    # --- (2) energy distribution split by whether the SimCluster got any TICLCandidate ---
    is_zero = (df_sc[METRIC] == 0).values
    bins = np.logspace(np.log10(max(df_sc['energy'].min(), 1e-3)), np.log10(df_sc['energy'].max()), 41)
    fig, ax = plot_hist(df_sc['energy'][is_zero], bins, 'SimCluster energy [GeV]', 'Number of SimClusters',
        color='indianred', label=f'{METRIC} = 0')
    plot_hist(df_sc['energy'][~is_zero], bins, None, None, color='dodgerblue', label=f'{METRIC} > 0', fig=fig, ax=ax)
    ax.set_xscale('log')
    ax.legend(fontsize=13)
    fig.savefig(os.path.join(args.outputdir, 'sc_energy_by_matched.png'), dpi=200, bbox_inches='tight')
    plt.close(fig)

    # --- (3) per-event energy-weighted SimCluster efficiency vs raw (unweighted) SimCluster ---
    #     efficiency vs CaloParticle efficiency: does weighting by energy turn the SC-level
    #     distribution (peak at 0) into something that looks like the CP-level one (peak near 1)?
    def weighted_mean(x, w):
        wsum = np.sum(w)
        return np.sum(x*w)/wsum if wsum > 0 else 0.

    # group by parent CaloParticle (via the 'cp_index' column added to metrics_sc_tc.parquet
    # by calculate_associations.py, from CaloParticle.simClusters() refs) rather than by event,
    # so SimClusters belonging to different primary particles in the same event (e.g. the two
    # back-to-back pions from AddAntiParticle) are not mixed together.
    if 'cp_index' in df_sc.columns:
        groupby_cols = ['event', 'cp_index']
        weight_label = 'per CaloParticle'
    else:
        groupby_cols = ['event']
        weight_label = 'per event'
        print("WARNING: 'cp_index' column not found in metrics_sc_tc.parquet"
              " (rerun calculate_associations.py to get it); falling back to per-event weighting,"
              " which mixes SimClusters from different primary CaloParticles together.")
    weighted_eff_per_group = df_sc.groupby(groupby_cols).apply(
        lambda g: weighted_mean(g[METRIC].values, g['energy'].values),
        include_groups=False)

    eff_max = max(1.2, np.quantile(df_sc[METRIC].values, 0.98) * 1.1)
    bins = np.linspace(0, eff_max, 31)
    fig, ax = plot_hist(df_sc[METRIC], bins, METRIC_LABEL, 'Number of entries (normalized)',
        color='indianred', label=f'SimCluster {METRIC} (unweighted, per SC)')
    yvals_w, _ = np.histogram(weighted_eff_per_group.values, bins=bins)
    yvals_w = yvals_w * (len(df_sc)/max(len(weighted_eff_per_group), 1))  # normalize to same area for shape comparison
    ax.stairs(yvals_w, edges=bins, color='seagreen', linewidth=3, label=f'SimCluster {METRIC} (energy-weighted, {weight_label})')
    yvals_cp, _ = np.histogram(df_cp[METRIC], bins=bins)
    yvals_cp = yvals_cp * (len(df_sc)/max(len(df_cp), 1))
    ax.stairs(yvals_cp, edges=bins, color='dodgerblue', linewidth=3, label=f'CaloParticle {METRIC}')
    ax.legend(fontsize=11)
    fig.savefig(os.path.join(args.outputdir, 'sc_eff_weighted_vs_cp_eff.png'), dpi=200, bbox_inches='tight')
    plt.close(fig)

    print(f'Plots written to {args.outputdir}')
