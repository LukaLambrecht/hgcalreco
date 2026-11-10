# Plot how the TICLCandidate and LayerCluster composition per HGCAL subdetector (see also ../ticlcandidate-composition),
# and the purity and efficiency per truth category, change along 1D CLUE parameter scans.
#
# Input: a grid scan output directory (containing one directory per grid, with one job directory
# per grid point), where calculate_associations.py was run with --do_composition.
#
# For each grid, a summary table with one row per grid point is first derived from the stored
# dataframes (and written to <outputdir>/<grid>/summary_<truth type>.csv), and then plotted vs the scanned parameter:
# - LayerClusters per subdetector (all, and in any TICLCandidate), relative to the default point;
# - fraction of LayerClusters (count, energy) per subdetector ending up in any TICLCandidate;
# - energy fraction per subdetector of the primary / all matched TICLCandidates;
# - primary / all matched TICLCandidate energy / truth energy per subdetector;
# - efficiency and purity (primary / all matched) per truth category.


import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)

from tools.compositiontools import SUBDETS, SUBDET_LABELS, SUBDET_COLORS
from tools.compositiontools import TRUTH_TYPES, TRUTH_CATEGORIES
from tools.compositiontools import load_composition, load_event_lc
sys.path.append(thisdir)
from scanutils import DEFAULT_INPUT, DEFAULT_PARAMS, PARAM_LABELS
from scanutils import get_grid_jobs, make_axes, savefig


def get_job_summary(effdir, truth_type):
    '''One row of summary numbers for one grid point.'''
    row = {}
    df_event = load_event_lc(effdir)
    for s in SUBDETS:
        for q in ['nlc', 'e']:
            row[f'{q}_{s}'] = df_event[f'{q}_{s}'].mean()
            row[f'{q}_tc_{s}'] = df_event[f'{q}_tc_{s}'].mean()
            row[f'{q}_tc_fraction_{s}'] = df_event[f'{q}_tc_{s}'].sum() / df_event[f'{q}_{s}'].sum()
    df_tc, df_truth = load_composition(effdir, truth_type=truth_type)
    selections = {'primary': df_tc[df_tc['is_primary']], 'all': df_tc}
    for selname, df in selections.items():
        etot = sum(df[f'e_{s}'].sum() for s in SUBDETS)
        for s in SUBDETS:
            row[f'{selname}_fe_{s}'] = df[f'e_{s}'].sum() / etot
            mask = (df_truth[f'ftruth_{s}'] >= 0.05) & np.isfinite(df_truth[f'{selname}_e_{s}'])
            ratio = (df_truth[f'{selname}_e_{s}'] / df_truth[f'truthe_{s}'])[mask]
            row[f'{selname}_capture_{s}'] = np.median(ratio) if len(ratio) > 0 else np.nan
    # metrics: (dataframe, column) for efficiency and purity w.r.t. primary and all matched TICLCandidates
    metrics = {'eff_primary': (df_truth, 'eff_primary'), 'eff_all': (df_truth, 'eff_sum'),
               'pur_primary': (df_truth, 'pur_primary'), 'pur_all': (df_tc, 'pur')}
    for metric, (df, column) in metrics.items():
        row[metric] = df[column].mean()
        for key in TRUTH_CATEGORIES:
            values = df[df['category'] == key][column]
            row[f'{metric}_{key}'] = values.mean() if len(values) > 0 else np.nan
            row[f'{metric}_{key}_err'] = values.std() / np.sqrt(len(values)) if len(values) > 1 else np.nan
    for key in TRUTH_CATEGORIES:
        row[f'ntruth_{key}'] = int(np.sum(df_truth['category'] == key))
    return row


def get_grid_summary(griddir, truth_type):
    '''Summary table (one row per successful grid point) for one grid.'''
    rows = []
    for jobdir, param_name, param_value, effdir in get_grid_jobs(griddir):
        row = {'job': jobdir, 'param_name': param_name, 'param_value': param_value}
        row.update(get_job_summary(effdir, truth_type))
        rows.append(row)
    if len(rows) == 0: return None
    return pd.DataFrame(rows).sort_values(by='param_value').reset_index(drop=True)


def plot_grid(df, truth_type, outputdir):
    x = df['param_value'].values
    param_name = df['param_name'].iloc[0]
    default = df[np.isclose(df['param_value'], DEFAULT_PARAMS.get(param_name, np.nan))]
    tlabel = TRUTH_TYPES[truth_type]
    d = {c: df[c].values for c in df.columns} # numpy arrays, for plotting
    style = dict(linewidth=2, marker='o', markersize=4)

    # LayerClusters per subdetector relative to the default point
    if len(default) == 1:
        for q, qlabel in [('nlc', 'Number of LayerClusters'), ('e', 'LayerCluster energy')]:
            fig, ax = make_axes(df, f'{qlabel} per event\n(relative to default parameters)')
            for s in SUBDETS:
                ax.plot(x, d[f'{q}_{s}'] / default[f'{q}_{s}'].iloc[0], color=SUBDET_COLORS[s],
                    linestyle='-', label=f'{SUBDET_LABELS[s]}, all', **style)
                ax.plot(x, d[f'{q}_tc_{s}'] / default[f'{q}_tc_{s}'].iloc[0], color=SUBDET_COLORS[s],
                    linestyle='--', label=f'{SUBDET_LABELS[s]}, in any TICLCandidate', **style)
            ax.set_yscale('log')
            ax.legend(fontsize=9)
            savefig(fig, outputdir, f'event_lc_{q}_vs_param')

    # fraction of LayerClusters ending up in any TICLCandidate
    fig, ax = make_axes(df, 'Fraction of LayerClusters in any TICLCandidate')
    for s in SUBDETS:
        ax.plot(x, d[f'nlc_tc_fraction_{s}'], color=SUBDET_COLORS[s], linestyle='-',
            label=f'{SUBDET_LABELS[s]}, by count', **style)
        ax.plot(x, d[f'e_tc_fraction_{s}'], color=SUBDET_COLORS[s], linestyle='--',
            label=f'{SUBDET_LABELS[s]}, by energy', **style)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9)
    savefig(fig, outputdir, 'event_lc_tc_fraction_vs_param')

    for selname in ['primary', 'all']:
        sellabel = 'primary TICLCandidate' if selname == 'primary' else 'all matched TICLCandidates'

        # TICLCandidate composition
        fig, ax = make_axes(df, f'Fraction of energy of {sellabel}\n(w.r.t. {tlabel})')
        for s in SUBDETS:
            ax.plot(x, d[f'{selname}_fe_{s}'], color=SUBDET_COLORS[s], label=SUBDET_LABELS[s], **style)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=10)
        savefig(fig, outputdir, f'tc_{truth_type}_composition_energy_vs_param_{selname}')

        # TICLCandidate energy / truth energy per subdetector
        fig, ax = make_axes(df, f'Median energy of {sellabel}\n/ {tlabel} energy,\nper subdetector')
        for s in SUBDETS:
            ax.plot(x, d[f'{selname}_capture_{s}'], color=SUBDET_COLORS[s], label=SUBDET_LABELS[s], **style)
        ax.set_ylim(0, 1.5)
        ax.legend(fontsize=10)
        savefig(fig, outputdir, f'tc_{truth_type}_energy_ratio_per_subdet_vs_param_{selname}')

    # metrics per truth category
    metrics = {
        'eff_primary': (f'Mean {tlabel} efficiency\nw.r.t. primary TICLCandidate', f'{truth_type}_tc_eff_primary'),
        'eff_all': (f'Mean {tlabel} efficiency\nw.r.t. all matched TICLCandidates', f'{truth_type}_tc_eff_all'),
        'pur_primary': (f'Mean primary TICLCandidate purity\nw.r.t. {tlabel}', f'{truth_type}_tc_pur_primary'),
        'pur_all': (f'Mean TICLCandidate purity\nw.r.t. matched {tlabel}', f'tc_{truth_type}_pur_all'),
    }
    for metric, (ylabel, figname) in metrics.items():
        fig, ax = make_axes(df, ylabel)
        ax.plot(x, d[metric], color='#1a1a1a', label='All', **style)
        for key, info in TRUTH_CATEGORIES.items():
            label = info['label'] if metric == 'pur_all' else f'{info["label"]} (n={int(df[f"ntruth_{key}"].median())})'
            ax.errorbar(x, d[f'{metric}_{key}'], yerr=d[f'{metric}_{key}_err'], color=info['color'],
                label=label, **style)
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=9, loc='lower left')
        savefig(fig, outputdir, f'{figname}_by_category_vs_param')

if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Plot composition trends along 1D CLUE parameter scans')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Grid scan output directory')
    parser.add_argument('-g', '--grids', default=None, nargs='+', help='Grids to plot (default: all)')
    parser.add_argument('-t', '--truth_type', default='truthbranch-signal', choices=list(TRUTH_TYPES.keys()))
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output_scan'))
    args = parser.parse_args()

    grids = args.grids
    if grids is None:
        grids = sorted([d for d in os.listdir(args.inputdir) if os.path.isdir(os.path.join(args.inputdir, d))])
    for grid in grids:
        print(f'Processing grid {grid}...')
        df = get_grid_summary(os.path.join(args.inputdir, grid), args.truth_type)
        if df is None:
            print(f'WARNING: no finished grid points with composition output found for {grid}, skipping.')
            continue
        outputdir = os.path.join(args.outputdir, grid)
        os.makedirs(outputdir, exist_ok=True)
        df.to_csv(os.path.join(outputdir, f'summary_{args.truth_type}.csv'), index=False)
        plot_grid(df, args.truth_type, outputdir)
