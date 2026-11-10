# Question: for the CLUE parameters that do change the LayerClusters (see lc_sensitivity.py),
# why do the TICLCandidate efficiency and purity barely change?
#
# Input: a grid scan output directory (see scanutils.py), with calculate_associations.py run with --do_composition.
# All grid points of a grid run on the same events, so each truth object can be followed across grid points
# (matched by event and truth index).
#
# Metrics (per truth object, w.r.t. all TICLCandidates matched to it):
# - eff_all: efficiency w.r.t. all matched TICLCandidates (eff_sum in the stored output), i.e. the energy shared
#   with all matched TICLCandidates, divided by the truth object's energy shared with all TICLCandidates
#   (i.e. its energy in LayerClusters that are part of any TICLCandidate, not its total energy);
# - pur_all: purity of the matched TICLCandidates combined, approximated as the average of their purities
#   weighted by their (raw) energy (the purity of each TICLCandidate is the fraction of its energy
#   shared with truth objects that is shared with this truth object).
#
# Hypotheses tested here:
# 1. Normalization: the efficiency is normalized to the truth energy that ends up in TICLCandidates,
#    so losing (signal) energy before that does not lower it. To test this, the efficiency is
#    normalized to the truth energy instead (truth-normalized efficiency, point 5):
#        eff_all x T_tc / T_ref,
#    with T the truth energy in LayerClusters (sum over cells in LayerClusters of RecHit energy x truth energy
#    fraction), T_tc the same for LayerClusters in any TICLCandidate (approximately the denominator of
#    the efficiency), both at this grid point, and T_ref the maximum of T over all grid points of all grids
#    (all grids run on the same events; the most inclusive settings cluster essentially all RecHits,
#    so T_ref approximates the truth energy in all RecHits).
#    This is approximately the energy shared with all matched TICLCandidates divided by the truth energy.
#    Note: energy deposits in cells without a RecHit (below the zero suppression) are not included.
# 2. Cancellation: the mean of a metric can stay flat while individual truth objects change in both directions.
#    To test this, the change of the mean w.r.t. the default point is compared to the mean absolute change
#    per truth object.
#
# Outputs (in <outputdir>):
# - <grid>/metric_decomposition_vs_param.png: eff_all, truth-normalized eff_all, T / T_ref, T_tc / T_ref and pur_all;
# - <grid>/metric_changes_vs_param.png: change of the mean w.r.t. the default point,
#   for eff_all, truth-normalized eff_all and pur_all
#   (and the mean absolute change per truth object with --show_abs_change);
# - overview_{full,window}.png/.csv: maximum changes per grid, over the full scanned range
#   and within a factor (--window) of the default value.


import os
import sys
import argparse
import numpy as np
import pandas as pd

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)
sys.path.append(thisdir)

from tools.compositiontools import SUBDETS, TRUTH_TYPES
from tools.compositiontools import load_composition
from scanutils import DEFAULT_INPUT, DEFAULT_PARAMS, DEFAULT_REFERENCE_JOB, get_grids, get_grid_jobs, get_window_mask
from scanutils import make_axes, savefig, plot_heatmap


def get_grid_truth_table(griddir, truth_type, reference_effdir=None):
    '''
    One row per (grid point, truth object), with the metrics and the truth energy in LayerClusters (T),
    and T_ref (maximum of T over the grid points) per truth object.
    If the grid does not contain the default parameter value, the grid point at reference_effdir
    (with all parameters at their default values) is added as the default point.
    '''
    dfs = []
    jobs = get_grid_jobs(griddir)
    if len(jobs) == 0: return None
    param_name = jobs[0][1]
    if (reference_effdir is not None and param_name in DEFAULT_PARAMS
        and not any(np.isclose(j[2], DEFAULT_PARAMS[param_name]) for j in jobs)):
        print(f'No default point in grid {os.path.basename(griddir)}, adding {DEFAULT_REFERENCE_JOB} as default point.')
        jobs.append(('reference', param_name, DEFAULT_PARAMS[param_name], reference_effdir))
    for jobdir, param_name, param_value, effdir in jobs:
        df_tc, df_truth = load_composition(effdir, truth_type=truth_type)
        df = df_truth[['event', 'truth_index', 'eff_sum']].rename(columns={'eff_sum': 'eff_all'})
        # combined purity of all matched TICLCandidates (energy-weighted average, see above)
        weights = df_tc['raw_energy'].clip(lower=0)
        pur_all = ((df_tc['pur'] * weights).groupby([df_tc['event'], df_tc['truth_index']]).sum()
            / weights.groupby([df_tc['event'], df_tc['truth_index']]).sum()).rename('pur_all').reset_index()
        df = df.merge(pur_all, on=['event', 'truth_index'], how='left')
        df['T'] = sum(df_truth[f'truthe_{s}'] for s in SUBDETS)
        # truth energy in LayerClusters that are part of any TICLCandidate
        # (approximately the denominator of the efficiency; only available in newer versions of the output)
        df['T_tc'] = (sum(df_truth[f'truthe_tc_{s}'] for s in SUBDETS)
            if 'truthe_tc_ee' in df_truth.columns else np.nan)
        df['job'] = jobdir
        df['param_name'] = param_name
        df['param_value'] = param_value
        dfs.append(df)
    if len(dfs) == 0: return None
    return pd.concat(dfs, ignore_index=True)


def add_normalized_quantities(df, t_ref):
    '''
    Add the truth energies relative to a reference energy per truth object,
    and the truth-normalized efficiency.
    t_ref: DataFrame with columns event, truth_index and T_ref (reference truth energy).
    '''
    df = df.merge(t_ref, on=['event', 'truth_index'], how='left')
    df['T_frac'] = np.where(df['T_ref'] > 0, df['T'] / df['T_ref'].where(df['T_ref'] > 0, 1), np.nan)
    df['T_tc_frac'] = np.where(df['T_ref'] > 0, df['T_tc'] / df['T_ref'].where(df['T_ref'] > 0, 1), np.nan)
    # truth-normalized efficiency: energy shared with all matched TICLCandidates divided by T_ref
    # (eff_all is approximately this shared energy divided by T_tc, so multiply by T_tc / T_ref;
    #  fallback for older outputs without T_tc: T / T_ref, which only captures losses from LayerClusters)
    rescaling = df['T_tc_frac'] if df['T_tc'].notna().all() else df['T_frac']
    df['eff_all_truthnorm'] = df['eff_all'] * rescaling
    return df


def get_point_table(df):
    '''Per grid point: means, and changes w.r.t. the default point (per truth object and of the mean).'''
    param_name = df['param_name'].iloc[0]
    if param_name not in DEFAULT_PARAMS: return None
    is_default = np.isclose(df['param_value'], DEFAULT_PARAMS[param_name])
    if not is_default.any(): return None
    default = df[is_default].drop_duplicates(['event', 'truth_index'])
    metrics = ['eff_all', 'pur_all', 'eff_all_truthnorm', 'T_frac', 'T_tc_frac']
    merged = df.merge(default[['event', 'truth_index'] + metrics], on=['event', 'truth_index'],
        how='inner', suffixes=('', '_default'))
    rows = []
    for (param_value, job), group in merged.groupby(['param_value', 'job']):
        row = {'param_name': param_name, 'param_value': param_value, 'job': job, 'ntruth': len(group)}
        for m in metrics:
            # (truth objects without matched TICLCandidates at either point have no purity and are skipped)
            delta = (group[m] - group[f'{m}_default']).dropna()
            row[m] = group[m].mean()
            row[f'{m}_err'] = group[m].std() / np.sqrt(group[m].count()) if group[m].count() > 1 else np.nan
            row[f'{m}_delta_mean'] = delta.mean()
            row[f'{m}_delta_abs'] = delta.abs().mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values(by='param_value').reset_index(drop=True)


def plot_grid(points, truth_type, outputdir, show_abs_change=False):
    tlabel = TRUTH_TYPES[truth_type]
    x = points['param_value'].values
    style = dict(linewidth=2, marker='o', markersize=4)
    # labels and colours (efficiency in red, truth-normalized efficiency in green, purity in blue;
    # lighter shades for the mean absolute change per truth object)
    eff_label = (f'{tlabel} efficiency w.r.t. all matched TICLCandidates,\n'
        + f'normalized to the {tlabel} energy in all TICLCandidates')
    effnorm_label = (f'{tlabel} efficiency w.r.t. all matched TICLCandidates,\n'
        + f'normalized to the {tlabel} energy (approx.)')
    pur_label = f'Purity of all matched TICLCandidates w.r.t. {tlabel}'
    colors = {
        'eff_all': ('#c0392b', '#f1948a'),
        'eff_all_truthnorm': ('#1e8449', '#82e0aa'),
        'pur_all': ('#2a78d6', '#7fb3ef'),
    }

    # decomposition
    curves = [
        ('eff_all', eff_label, colors['eff_all'][0], '-'),
        ('eff_all_truthnorm', effnorm_label, colors['eff_all_truthnorm'][0], '-'),
        ('pur_all', pur_label, colors['pur_all'][0], '-'),
        ('T_frac', f'{tlabel} energy in LayerClusters,\nnormalized to the {tlabel} energy (approx.)', '#a6a6a6', ':'),
        ('T_tc_frac', f'{tlabel} energy in LayerClusters in TICLCandidates,\n'
            + f'normalized to the {tlabel} energy (approx.)', '#6b6b6b', '--'),
    ]
    fig, ax = make_axes(points, 'Mean value')
    for m, label, color, linestyle in curves:
        ax.errorbar(x, points[m].values, yerr=points[f'{m}_err'].values, color=color, linestyle=linestyle,
            label=label, **style)
    ax.set_ylim(0, 1.6)
    ax.legend(fontsize=7, loc='upper left', handlelength=4)
    ax.grid(axis='y', color='#e6e6e6', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    savefig(fig, outputdir, 'metric_decomposition_vs_param')

    # change of the mean (and optionally the mean absolute change per truth object)
    fig, ax = make_axes(points, 'Change of the mean w.r.t. default parameters')
    curves = [('eff_all', eff_label), ('eff_all_truthnorm', effnorm_label), ('pur_all', pur_label)]
    for m, label in curves:
        ax.plot(x, points[f'{m}_delta_mean'].values, color=colors[m][0], linestyle='-', label=label, **style)
        if show_abs_change:
            ax.plot(x, points[f'{m}_delta_abs'].values, color=colors[m][1], linestyle='--',
                label=f'Same, mean absolute change per {tlabel}', **style)
    ax.axhline(0, color='#c8c8c8', linewidth=1, zorder=0)
    ax.legend(fontsize=7, loc='upper left', handlelength=4)
    deltas = ['mean', 'abs'] if show_abs_change else ['mean']
    lim = np.nanmax(np.abs(points[[f'{m}_delta_{d}' for m, _ in curves for d in deltas]].values))
    if np.isfinite(lim) and lim > 0: ax.set_ylim(-1.1 * lim, (1.8 if show_abs_change else 1.0) * lim)
    ax.grid(axis='y', color='#e6e6e6', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    savefig(fig, outputdir, 'metric_changes_vs_param')


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Why do the TICLCandidate metrics barely change along the scans?')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Grid scan output directory')
    parser.add_argument('-g', '--grids', default=None, nargs='+', help='Grids to use (default: all)')
    parser.add_argument('-t', '--truth_type', default='truthbranch-signal', choices=list(TRUTH_TYPES.keys()))
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output_metric_sensitivity'))
    parser.add_argument('--window', default=2., type=float,
        help='Factor around the default value defining the "window" range (default: 2)')
    parser.add_argument('--show_abs_change', default=False, action='store_true',
        help='Also show the mean absolute change per truth object in the plots of the changes')
    args = parser.parse_args()

    grids = args.grids if args.grids is not None else get_grids(args.inputdir)
    overview = {'full': {}, 'window': {}}
    columns = {
        'eff_all_delta_mean': 'Efficiency\n(change of mean)',
        'eff_all_delta_abs': 'Efficiency\n(mean abs. change\nper truth object)',
        'eff_all_truthnorm_delta_mean': 'Truth-normalized\nefficiency\n(change of mean)',
        'T_frac_delta_mean': 'Truth energy in\nLayerClusters / truth energy\n(change of mean)',
        'T_tc_frac_delta_mean': 'Truth energy in LCs\nin TICLCandidates / truth en.\n(change of mean)',
        'pur_all_delta_mean': 'Purity\n(change of mean)',
        'pur_all_delta_abs': 'Purity\n(mean abs. change\nper truth object)',
    }
    # load all grids first, to define the reference truth energy per truth object:
    # the maximum truth energy in LayerClusters over all grid points of all grids
    # (all grids run on the same events; the most inclusive settings, e.g. very low E_cut or rho_seed,
    #  cluster essentially all RecHits, so this approximates the truth energy in all RecHits)
    tables = {}
    for grid in grids:
        print(f'Loading grid {grid}...')
        tables[grid] = get_grid_truth_table(os.path.join(args.inputdir, grid), args.truth_type,
            reference_effdir=os.path.join(args.inputdir, DEFAULT_REFERENCE_JOB, 'efficiency'))
    alltables = pd.concat([t for t in tables.values() if t is not None], ignore_index=True)
    t_ref = alltables.groupby(['event', 'truth_index'])['T'].max().rename('T_ref').reset_index()
    default_t = alltables[alltables['job'].eq('reference') | (
        alltables.apply(lambda r: np.isclose(r['param_value'], DEFAULT_PARAMS.get(r['param_name'], np.nan)), axis=1))]
    default_t = default_t.drop_duplicates(['event', 'truth_index']).merge(t_ref, on=['event', 'truth_index'])
    print('Reference truth energy: mean ratio of the truth energy in LayerClusters at the default point'
        + f' to the reference: {np.mean(default_t["T"] / default_t["T_ref"]):.3f}')

    for grid in grids:
        print(f'Processing grid {grid}...')
        df = tables[grid]
        if df is not None: df = add_normalized_quantities(df, t_ref)
        points = get_point_table(df) if df is not None else None
        if points is None:
            print(f'WARNING: no finished grid points or no default point found for {grid}, skipping.')
            continue
        outputdir = os.path.join(args.outputdir, grid)
        os.makedirs(outputdir, exist_ok=True)
        points.to_csv(os.path.join(outputdir, f'summary_{args.truth_type}.csv'), index=False)
        plot_grid(points, args.truth_type, outputdir, show_abs_change=args.show_abs_change)
        for wname, factor in [('full', None), ('window', args.window)]:
            mask = get_window_mask(points['param_value'], points['param_name'].iloc[0], factor)
            overview[wname][grid] = {label: np.nanmax(np.abs(points[c].values[mask])) for c, label in columns.items()}

    os.makedirs(args.outputdir, exist_ok=True)
    for wname, data in overview.items():
        if len(data) == 0: continue
        table = pd.DataFrame(data).T
        table.rename(columns=lambda c: c.replace('\n', ' ')).to_csv(os.path.join(args.outputdir, f'overview_{wname}.csv'))
        wtext = 'over the full scanned range' if wname == 'full' else f'within a factor {args.window:g} of the default value'
        plot_heatmap(table, args.outputdir, f'overview_{wname}', cmax=0.2, fmt='{:.3f}',
            title_text=f'Maximum absolute change w.r.t. default parameters, {wtext}')
        print(f'Maximum absolute change w.r.t. default parameters, {wtext}:')
        print(table.rename(columns=lambda c: c.replace('\n', ' ')).T.to_string(float_format=lambda v: f'{v:.3f}'))
