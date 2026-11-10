# Question: how much does varying a given CLUE parameter affect the LayerClusters themselves
# (in particular in CE-H silicon)? Parameters that barely change the LayerClusters
# can be set aside as essentially irrelevant for the current CLUE implementation.
#
# Input: a grid scan output directory (see scanutils.py), with calculate_associations.py run with --do_composition.
# Quantities per grid point and subdetector (all per event, averaged over events):
# - nlc: number of LayerClusters;
# - e: total LayerCluster energy;
# - emean: mean energy per LayerCluster;
# - e_tc: LayerCluster energy in any TICLCandidate;
# - sig_e: energy of the signal truth particles in LayerClusters
#   (sum over cells in LayerClusters of RecHit energy x signal particle energy fraction);
# - sig_e_tc: the same, but only for LayerClusters that are part of any TICLCandidate.
# Outputs (in <outputdir>):
# - <grid>/lc_<subdet>_vs_param.png: these quantities relative to the default parameter point;
# - overview_<subdet>_{full,window}.png/.csv: maximum relative change w.r.t. the default point per grid,
#   over the full scanned range and within a factor (--window) of the default value;
# - a printed list of parameters that change none of the CE-H silicon quantities by more than --threshold.


import os
import sys
import argparse
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator, FixedLocator, FuncFormatter, NullFormatter

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)
sys.path.append(thisdir)

from tools.compositiontools import SUBDETS, SUBDET_LABELS, TRUTH_TYPES
from tools.compositiontools import load_composition, load_event_lc
from scanutils import DEFAULT_INPUT, DEFAULT_REFERENCE_JOB, get_grids, get_grid_jobs, get_window_mask, get_default_row
from scanutils import make_axes, savefig, plot_heatmap


# quantities: label, colour, linestyle, marker
# (grouped by colour: count in blue, LayerCluster energies in red/orange, energies in TICLCandidates
#  and signal energies in green)
QUANTITIES = {
    'nlc': ('Number of LayerClusters', '#2a78d6', '-', 'o'),
    'e': ('Total LayerCluster energy', '#c0392b', '-', 's'),
    'emean': ('Mean energy per LayerCluster', '#f39c4a', '--', 'D'),
    'e_tc': ('LayerCluster energy in TICLCandidates', 'mediumaquamarine', '-', '^'),
    'sig_e': ('Signal particle energy in LayerClusters', '#145a32', '--', 'v'),
    'sig_e_tc': ('Signal particle energy in LayerClusters\nin TICLCandidates', '#27ae60', ':', 'P'),
}


def get_point_summary(effdir, truth_type):
    '''Quantities per subdetector for one grid point.'''
    df_event = load_event_lc(effdir)
    _, df_truth = load_composition(effdir, truth_type=truth_type)
    nevents = len(df_event)
    row = {}
    for s in SUBDETS:
        row[f'nlc_{s}'] = df_event[f'nlc_{s}'].mean()
        row[f'e_{s}'] = df_event[f'e_{s}'].mean()
        row[f'emean_{s}'] = df_event[f'e_{s}'].sum() / max(df_event[f'nlc_{s}'].sum(), 1)
        row[f'e_tc_{s}'] = df_event[f'e_tc_{s}'].mean()
        row[f'sig_e_{s}'] = df_truth[f'truthe_{s}'].sum() / nevents
        # (only available in newer versions of the output)
        row[f'sig_e_tc_{s}'] = (df_truth[f'truthe_tc_{s}'].sum() / nevents
            if f'truthe_tc_{s}' in df_truth.columns else np.nan)
    return row


def get_grid_table(griddir, truth_type):
    rows = []
    for jobdir, param_name, param_value, effdir in get_grid_jobs(griddir):
        row = {'job': jobdir, 'param_name': param_name, 'param_value': param_value}
        row.update(get_point_summary(effdir, truth_type))
        rows.append(row)
    return pd.DataFrame(rows) if len(rows) > 0 else None


def get_relative(df, default):
    '''Ratio of each quantity to its value at the default point.'''
    rel = df[['param_name', 'param_value']].copy()
    for q in QUANTITIES:
        for s in SUBDETS:
            ref = default[f'{q}_{s}']
            rel[f'{q}_{s}'] = df[f'{q}_{s}'] / ref if ref > 0 else np.nan
    return rel


def set_ratio_axis(ax, values):
    '''
    Set the y-axis for ratios w.r.t. the default point: linear with dense ticks for small variations,
    logarithmic (beyond a factor 3) with labelled ticks at 1, 1.5, 2, 3, 5, 7 (x powers of 10) for large variations.
    '''
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    if len(values) == 0: return
    vmin, vmax = min(np.min(values), 1.), max(np.max(values), 1.)
    if vmax / vmin < 3:
        margin = 0.05 * (vmax - vmin) + 0.01
        ax.set_ylim(vmin - margin, vmax + margin)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=10))
        return
    ax.set_yscale('log')
    ax.set_ylim(vmin / 1.2, vmax * 1.2)
    # fewer labelled ticks per decade when the range spans many decades
    ndecades = np.log10(vmax / vmin)
    mantissas = [1, 1.5, 2, 3, 5, 7] if ndecades < 2.5 else ([1, 2, 5] if ndecades < 4.5 else [1])
    ticks = [m * 10.**k for k in range(-6, 4) for m in mantissas]
    ticks = [t for t in ticks if vmin / 1.2 <= t <= vmax * 1.2]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
    ax.yaxis.set_minor_formatter(NullFormatter())


def plot_grid(rel, outputdir):
    x = rel['param_value'].values
    for s in SUBDETS:
        fig, ax = make_axes(rel, f'{SUBDET_LABELS[s]}: value relative to default parameters')
        plotted = []
        for q, (label, color, linestyle, marker) in QUANTITIES.items():
            y = rel[f'{q}_{s}'].values
            if not np.any(np.isfinite(y)): continue
            ax.plot(x, y, color=color, linestyle=linestyle, linewidth=2, marker=marker, markersize=5, label=label)
            plotted.append(y)
        ax.axhline(1, color='#c8c8c8', linewidth=1, zorder=0)
        set_ratio_axis(ax, np.concatenate(plotted))
        ax.grid(axis='y', color='#e6e6e6', linewidth=0.8, zorder=0)
        ax.legend(fontsize=8, handlelength=4)
        savefig(fig, outputdir, f'lc_{s}_vs_param')


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Sensitivity of LayerCluster properties to CLUE parameters')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Grid scan output directory')
    parser.add_argument('-g', '--grids', default=None, nargs='+', help='Grids to use (default: all)')
    parser.add_argument('-t', '--truth_type', default='truthbranch-signal', choices=list(TRUTH_TYPES.keys()))
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output_lc_sensitivity'))
    parser.add_argument('--window', default=2., type=float,
        help='Factor around the default value defining the "window" range (default: 2)')
    parser.add_argument('--threshold', default=0.05, type=float,
        help='Maximum relative change (over the full range) for a parameter to be considered irrelevant')
    args = parser.parse_args()

    grids = args.grids if args.grids is not None else get_grids(args.inputdir)
    overview = {'full': {}, 'window': {}}
    for grid in grids:
        print(f'Processing grid {grid}...')
        df = get_grid_table(os.path.join(args.inputdir, grid), args.truth_type)
        if df is None:
            print(f'WARNING: no finished grid points found for {grid}, skipping.')
            continue
        default = get_default_row(df)
        if default is None:
            print(f'No default point in grid {grid}, using {DEFAULT_REFERENCE_JOB} as reference.')
            default = pd.Series(get_point_summary(
                os.path.join(args.inputdir, DEFAULT_REFERENCE_JOB, 'efficiency'), args.truth_type))
        rel = get_relative(df, default)
        outputdir = os.path.join(args.outputdir, grid)
        os.makedirs(outputdir, exist_ok=True)
        df.to_csv(os.path.join(outputdir, 'summary.csv'), index=False)
        plot_grid(rel, outputdir)
        for wname, factor in [('full', None), ('window', args.window)]:
            mask = get_window_mask(rel['param_value'], rel['param_name'].iloc[0], factor)
            overview[wname][grid] = {f'{q}_{s}': (np.nanmax(np.abs(rel[f'{q}_{s}'].values[mask] - 1))
                if np.any(np.isfinite(rel[f'{q}_{s}'].values[mask])) else np.nan) for q in QUANTITIES for s in SUBDETS}

    # overview tables and heatmaps
    os.makedirs(args.outputdir, exist_ok=True)
    for wname, data in overview.items():
        if len(data) == 0: continue
        table = pd.DataFrame(data).T
        table.to_csv(os.path.join(args.outputdir, f'overview_{wname}.csv'))
        wtext = 'over the full scanned range' if wname == 'full' else f'within a factor {args.window:g} of the default value'
        for s in SUBDETS:
            sub = table[[f'{q}_{s}' for q in QUANTITIES]]
            sub.columns = [QUANTITIES[q][0].replace('\n', ' ') for q in QUANTITIES]
            plot_heatmap(sub, args.outputdir, f'overview_{s}_{wname}',
                title_text=f'{SUBDET_LABELS[s]}: maximum relative change w.r.t. default, {wtext}')

    # parameters that do not affect the CE-H silicon LayerClusters
    if len(overview['full']) > 0:
        table = pd.DataFrame(overview['full']).T
        columns = [f'{q}_hsi' for q in ['nlc', 'e', 'sig_e']]
        printcolumns = [f'{q}_hsi' for q in QUANTITIES]
        inert = table[(table[columns] < args.threshold).all(axis=1)].index.tolist()
        print(f'Grids changing the CE-H silicon number of LayerClusters, their energy and the signal energy in them')
        print(f'by less than {args.threshold:.0%} over the full scanned range: {inert}')
        print('Maximum relative change over the full scanned range (CE-H silicon):')
        print(table[printcolumns].to_string(float_format=lambda v: f'{v:.1%}'))
