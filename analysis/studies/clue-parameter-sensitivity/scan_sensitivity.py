# Sensitivity of the LayerClusters and of the TICLCandidate purity and efficiency to the CLUE parameters,
# along grid scans.
#
# Input: a grid scan output directory (see scanutils.py), with calculate_associations.py run with --do_composition.
# All grid points of all grids run on the same events, so each truth object can be followed across grid points
# (matched by event and truth index).
#
# All output for a grid (plots and summary table) goes into <outputdir>/<grid>/.
# For each grid, a table with one row per grid point is built (written to <outputdir>/<grid>/summary_<truth type>.csv),
# with the following quantities.
#
# LayerCluster quantities per subdetector <s> (ee, hsi, hsci, and hgcal for the sum of the three;
# all per event, averaged over events), and the same relative to the default parameter point (prefix rel_):
# - nlc_<s>: number of LayerClusters;
# - e_<s>: total LayerCluster energy;
# - emean_<s>: mean energy per LayerCluster;
# - e_tc_<s>: LayerCluster energy in any TICLCandidate;
# - sig_e_<s>: energy of the signal truth particles in LayerClusters
#   (sum over cells in LayerClusters of RecHit energy x signal particle energy fraction);
# - sig_e_tc_<s>: the same, but only for LayerClusters that are part of any TICLCandidate.
#
# Metrics (per truth object, w.r.t. all TICLCandidates matched to it, averaged over truth objects):
# - eff_all: efficiency w.r.t. all matched TICLCandidates (eff_sum in the stored output), i.e. the energy shared
#   with all matched TICLCandidates, divided by the truth object's energy shared with all TICLCandidates
#   (i.e. its energy in LayerClusters that are part of any TICLCandidate, not its total energy);
# - pur_all: purity of the matched TICLCandidates combined, approximated as the average of their purities
#   weighted by their (raw) energy (the purity of each TICLCandidate is the fraction of its energy
#   shared with truth objects that is shared with this truth object);
# - eff_all_truthnorm: truth-normalized efficiency, eff_all x T_tc / T_ref,
#   with T the truth energy in LayerClusters, T_tc the same for LayerClusters in any TICLCandidate
#   (approximately the denominator of eff_all), both at this grid point, and T_ref the maximum of T over all
#   grid points of all grids (the most inclusive settings cluster essentially all RecHits, so T_ref approximates
#   the truth energy in all RecHits; energy in cells without a RecHit is not included);
#   this is approximately the energy shared with all matched TICLCandidates divided by the truth energy;
# - T_frac, T_tc_frac: T / T_ref and T_tc / T_ref;
# - for each of these: the uncertainty on the mean (_err), the change of the mean w.r.t. the default point
#   (_delta_mean), the mean absolute change per truth object (_delta_abs), and the mean relative to the
#   default point (rel_ prefix).
#
# Plots per grid, vs the scanned parameter (for 1D grids; file names <plot>_vs_param.png,
# or <plot>_vs_param_<s> for the plots per subdetector <s>, including hgcal), with <plot>:
# - lc (per subdetector): the LayerCluster quantities relative to the default point;
# - metrics: eff_all, eff_all_truthnorm, pur_all, T_frac and T_tc_frac;
# - metric_changes: change of the mean w.r.t. the default point, for eff_all, eff_all_truthnorm
#   and pur_all (and the mean absolute change per truth object with --show_abs_change);
# - combined (per subdetector): pur_all, eff_all_truthnorm and the number of LayerClusters,
#   all relative to the default point.
# With --flat (for any grid, including multi-parameter grids), all grid points are shown on a single axis instead,
# sorted by one or more of (see --flat_sort, default all; file names <plot>_flat_<sorting>[_<s>].png):
# - purity: the mean purity;
# - efficiency: the mean truth-normalized efficiency;
# - average: the average of both;
# - nlc: the number of LayerClusters in the plotted subdetector, or the total number of LayerClusters in HGCAL
#   (for plots without a subdetector, or if the former does not change over the grid).


import os
import sys
import argparse
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator, FixedLocator, FuncFormatter, NullFormatter

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)
sys.path.append(thisdir)

from tools.compositiontools import SUBDETS, SUBDET_LABELS, TRUTH_TYPES
from tools.compositiontools import load_composition, load_event_lc
from scanutils import DEFAULT_INPUT, DEFAULT_PARAMS, DEFAULT_REFERENCE_JOB
from scanutils import get_grids, get_grid_jobs, get_grid_jobs_flat, get_job_number, is_default_params
from scanutils import get_default_row
from scanutils import make_axes, make_flat_axes, flat_style, savefig


# LayerCluster quantities: label, colour, linestyle, marker
# (grouped by colour: count in blue, LayerCluster energies in red/orange, energies in TICLCandidates
#  and signal energies in green)
LC_QUANTITIES = {
    'nlc': ('Number of LayerClusters', '#2a78d6', '-', 'o'),
    'e': ('Total LayerCluster energy', '#c0392b', '-', 's'),
    'emean': ('Mean energy per LayerCluster', '#f39c4a', '--', 'D'),
    'e_tc': ('LayerCluster energy in TICLCandidates', 'mediumaquamarine', '-', '^'),
    'sig_e': ('Signal particle energy in LayerClusters', '#145a32', '--', 'v'),
    'sig_e_tc': ('Signal particle energy in LayerClusters\nin TICLCandidates', '#27ae60', ':', 'P'),
}

# subdetectors for the LayerCluster quantities and plots: the HGCAL subdetectors and their sum
PLOT_SUBDETS = SUBDETS + ['hgcal']
PLOT_SUBDET_LABELS = {**SUBDET_LABELS, 'hgcal': 'HGCAL'}

# metrics (columns of the per-truth-object table that are averaged per grid point)
METRICS = ['eff_all', 'pur_all', 'eff_all_truthnorm', 'T_frac', 'T_tc_frac']

# sortings for the flat plots: (function of the points table and the subdetector of the plot (or None),
# returning the sorting key and the axis label)
def _sort_nlc(points, subdet):
    if subdet is not None:
        key = points[f'nlc_{subdet}']
        if np.nanmax(key) - np.nanmin(key) > 1e-6 * np.nanmax(np.abs(key)):
            return key, f'number of LayerClusters in {PLOT_SUBDET_LABELS[subdet]}'
    return points['nlc_hgcal'], 'total number of LayerClusters in HGCAL'

FLAT_SORTS = {
    'purity': lambda p, s: (p['pur_all'], 'mean purity of all matched TICLCandidates'),
    'efficiency': lambda p, s: (p['eff_all_truthnorm'], 'mean truth-normalized efficiency'),
    'average': lambda p, s: ((p['pur_all'] + p['eff_all_truthnorm']) / 2, 'average of purity and truth-norm. efficiency'),
    'nlc': _sort_nlc,
}


# loading

def get_grid_job_list(griddir, reference_effdir=None, flat=False):
    '''
    Get the grid points of a grid as a list of (job name, metadata dict, efficiency output directory).
    Metadata for 1D grids: param_name and param_value.
    Metadata with flat=True (any number of parameters): param_name "flat", param_value the job number,
    is_default (whether all parameters are at their default values), and param_<name> for each parameter.
    If the grid does not contain the default parameter value(s), the grid point at reference_effdir
    (with all parameters at their default values) is added as the default point (if it exists).
    '''
    if not flat:
        jobs = get_grid_jobs(griddir)
        if len(jobs) == 0: return []
        param_name = jobs[0][1]
        has_default = (param_name not in DEFAULT_PARAMS
            or any(np.isclose(j[2], DEFAULT_PARAMS[param_name]) for j in jobs))
        jobs = [(jobdir, {'param_name': name, 'param_value': value}, effdir) for jobdir, name, value, effdir in jobs]
        reference_meta = {'param_name': param_name, 'param_value': DEFAULT_PARAMS.get(param_name)}
    else:
        jobs = get_grid_jobs_flat(griddir)
        if len(jobs) == 0: return []
        has_default = any(is_default_params(params) for _, params, _ in jobs)
        jobs = [(jobdir, {'param_name': 'flat', 'param_value': get_job_number(jobdir),
            'is_default': is_default_params(params), **{f'param_{n}': v for n, v in params.items()}}, effdir)
            for jobdir, params, effdir in jobs]
        reference_meta = {'param_name': 'flat', 'param_value': -1, 'is_default': True}
    if not has_default and reference_effdir is not None and os.path.exists(reference_effdir):
        print(f'No default point in grid {os.path.basename(griddir)}, adding {DEFAULT_REFERENCE_JOB} as default point.')
        jobs.append(('reference', reference_meta, reference_effdir))
    return jobs


def load_job(effdir, truth_type):
    '''
    Load one grid point: a dict with the LayerCluster quantities per subdetector,
    and a DataFrame with one row per truth object (metrics and truth energies).
    '''
    df_event = load_event_lc(effdir)
    df_tc, df_truth = load_composition(effdir, truth_type=truth_type)

    # LayerCluster quantities
    nevents = len(df_event)
    lc = {}
    for s in SUBDETS:
        lc[f'nlc_{s}'] = df_event[f'nlc_{s}'].mean()
        lc[f'e_{s}'] = df_event[f'e_{s}'].mean()
        lc[f'emean_{s}'] = df_event[f'e_{s}'].sum() / max(df_event[f'nlc_{s}'].sum(), 1)
        lc[f'e_tc_{s}'] = df_event[f'e_tc_{s}'].mean()
        lc[f'sig_e_{s}'] = df_truth[f'truthe_{s}'].sum() / nevents
        # (only available in newer versions of the output)
        lc[f'sig_e_tc_{s}'] = (df_truth[f'truthe_tc_{s}'].sum() / nevents
            if f'truthe_tc_{s}' in df_truth.columns else np.nan)
    # sum of the subdetectors
    for q in ['nlc', 'e', 'e_tc', 'sig_e', 'sig_e_tc']:
        lc[f'{q}_hgcal'] = sum(lc[f'{q}_{s}'] for s in SUBDETS)
    lc['emean_hgcal'] = lc['e_hgcal'] / max(lc['nlc_hgcal'], 1)

    # metrics per truth object
    truth = df_truth[['event', 'truth_index', 'eff_sum']].rename(columns={'eff_sum': 'eff_all'})
    # combined purity of all matched TICLCandidates (energy-weighted average, see above)
    weights = df_tc['raw_energy'].clip(lower=0)
    pur_all = ((df_tc['pur'] * weights).groupby([df_tc['event'], df_tc['truth_index']]).sum()
        / weights.groupby([df_tc['event'], df_tc['truth_index']]).sum()).rename('pur_all').reset_index()
    truth = truth.merge(pur_all, on=['event', 'truth_index'], how='left')
    truth['T'] = sum(df_truth[f'truthe_{s}'] for s in SUBDETS)
    # truth energy in LayerClusters that are part of any TICLCandidate
    # (approximately the denominator of the efficiency; only available in newer versions of the output)
    truth['T_tc'] = (sum(df_truth[f'truthe_tc_{s}'] for s in SUBDETS)
        if 'truthe_tc_ee' in df_truth.columns else np.nan)
    return lc, truth


def load_grid(griddir, truth_type, reference_effdir=None, flat=False, workers=8):
    '''
    Load all grid points of a grid. Returns (or None if no grid points):
    - a DataFrame with one row per grid point (metadata and LayerCluster quantities);
    - a DataFrame with one row per (grid point, truth object) (job name, metrics and truth energies).
    The grid points are loaded in parallel processes (workers).
    '''
    jobs = get_grid_job_list(griddir, reference_effdir=reference_effdir, flat=flat)
    effdirs = [job[2] for job in jobs]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(load_job, effdirs, [truth_type] * len(effdirs), chunksize=8))
    else:
        results = [load_job(effdir, truth_type) for effdir in effdirs]
    lc_rows, truth_dfs = [], []
    for (jobdir, meta, effdir), (lc, truth) in zip(jobs, results):
        lc_rows.append({'job': jobdir, **meta, **lc})
        truth['job'] = jobdir
        truth_dfs.append(truth)
    if len(lc_rows) == 0: return None
    return pd.DataFrame(lc_rows), pd.concat(truth_dfs, ignore_index=True)


# processing

def add_normalized_quantities(truth, t_ref):
    '''
    Add the truth energies relative to a reference energy per truth object,
    and the truth-normalized efficiency.
    t_ref: DataFrame with columns event, truth_index and T_ref (reference truth energy).
    '''
    truth = truth.merge(t_ref, on=['event', 'truth_index'], how='left')
    truth['T_frac'] = np.where(truth['T_ref'] > 0, truth['T'] / truth['T_ref'].where(truth['T_ref'] > 0, 1), np.nan)
    truth['T_tc_frac'] = np.where(truth['T_ref'] > 0, truth['T_tc'] / truth['T_ref'].where(truth['T_ref'] > 0, 1), np.nan)
    # truth-normalized efficiency: energy shared with all matched TICLCandidates divided by T_ref
    # (eff_all is approximately this shared energy divided by T_tc, so multiply by T_tc / T_ref;
    #  fallback for older outputs without T_tc: T / T_ref, which only captures losses from LayerClusters)
    rescaling = truth['T_tc_frac'] if truth['T_tc'].notna().all() else truth['T_frac']
    truth['eff_all_truthnorm'] = truth['eff_all'] * rescaling
    return truth


def get_points(lc, truth):
    '''
    Combine the per-grid-point LayerCluster quantities and the per-truth-object metrics
    into one table with one row per grid point (sorted by param_value), with the quantities relative
    to the default point and the changes of the metrics w.r.t. the default point (see above).
    Returns None if there is no default point.
    '''
    default = get_default_row(lc)
    if default is None: return None
    points = lc.copy()

    # LayerCluster quantities relative to the default point
    for q in list(LC_QUANTITIES.keys()):
        for s in PLOT_SUBDETS:
            ref = default[f'{q}_{s}']
            points[f'rel_{q}_{s}'] = points[f'{q}_{s}'] / ref if ref > 0 else np.nan

    # metrics: means and changes w.r.t. the default point
    truth_default = truth[truth['job'] == default['job']]
    merged = truth.merge(truth_default[['event', 'truth_index'] + METRICS], on=['event', 'truth_index'],
        how='inner', suffixes=('', '_default'))
    rows = []
    for job, group in merged.groupby('job'):
        row = {'job': job, 'ntruth': len(group)}
        for m in METRICS:
            # (truth objects without matched TICLCandidates at either point have no purity and are skipped)
            delta = (group[m] - group[f'{m}_default']).dropna()
            row[m] = group[m].mean()
            row[f'{m}_err'] = group[m].std() / np.sqrt(group[m].count()) if group[m].count() > 1 else np.nan
            row[f'{m}_delta_mean'] = delta.mean()
            row[f'{m}_delta_abs'] = delta.abs().mean()
        rows.append(row)
    points = points.merge(pd.DataFrame(rows), on='job', how='left')
    default_metrics = points[points['job'] == default['job']].iloc[0]
    for m in METRICS:
        points[f'rel_{m}'] = points[m] / default_metrics[m]
    return points.sort_values(by='param_value', kind='stable').reset_index(drop=True)


# plotting

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


def plot_curves(points, curves, ylabel, outputdir, name, axis='ratio', subdet=None,
        flat=False, flat_sort=None, linewidth=2, markersize=5, legend=None):
    '''
    Plot a set of curves (columns of the points table) vs the scanned parameter,
    or (flat=True) vs the grid point index after sorting with flat_sort (see FLAT_SORTS).
    curves: list of dicts with keys column, label, color, linestyle, marker and optionally err (uncertainty column).
    axis: 'ratio' (values relative to the default point), 'fraction' (values between 0 and 1,
          with space for the legend above) or 'delta' (changes w.r.t. the default point).
    subdet: subdetector of the plot (used for the sorting by number of LayerClusters).
    legend: keyword arguments for the legend.
    '''
    if not flat:
        data = points
        x = data['param_value'].values
        fig, ax = make_axes(data, ylabel)
    else:
        key, sortlabel = FLAT_SORTS[flat_sort](points, subdet)
        order = np.argsort(key.values, kind='stable')
        data = points.iloc[order].reset_index(drop=True)
        x = np.arange(len(data))
        default_x = data.index[data['is_default'].astype(bool)][0] if data['is_default'].astype(bool).any() else None
        fig, ax = make_flat_axes(ylabel, sortlabel, default_x=default_x)
        linewidth, markersize = flat_style(len(data), linewidth=linewidth, markersize=markersize)
    plotted = []
    for curve in curves:
        y = data[curve['column']].values
        if not np.any(np.isfinite(y)): continue
        style = dict(color=curve['color'], linestyle=curve['linestyle'], linewidth=linewidth,
            marker=curve['marker'], markersize=markersize, label=curve['label'])
        if curve.get('err') is not None:
            ax.errorbar(x, y, yerr=data[curve['err']].values, **style)
        else:
            ax.plot(x, y, **style)
        plotted.append(y)
    if axis == 'ratio':
        ax.axhline(1, color='#c8c8c8', linewidth=1, zorder=0)
        if len(plotted) > 0: set_ratio_axis(ax, np.concatenate(plotted))
    elif axis == 'fraction':
        ax.set_ylim(0, 1.6)
    elif axis == 'delta':
        ax.axhline(0, color='#c8c8c8', linewidth=1, zorder=0)
        lim = np.nanmax(np.abs(np.concatenate(plotted))) if len(plotted) > 0 else np.nan
        if np.isfinite(lim) and lim > 0:
            ax.set_ylim(-1.1 * lim, (1.8 if len(curves) > 3 else 1.0) * lim)
    ax.grid(axis='y', color='#e6e6e6', linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(**(legend if legend is not None else {}))
    suffix = f'flat_{flat_sort}' if flat else 'vs_param'
    savefig(fig, outputdir, f'{name}_{suffix}' + (f'_{subdet}' if subdet is not None else ''))


def plot_grid(points, truth_type, outputdir, show_abs_change=False, flat=False, flat_sorts=None):
    '''Make all plots for one grid.'''
    tlabel = TRUTH_TYPES[truth_type]
    eff_label = (f'{tlabel} efficiency w.r.t. all matched TICLCandidates,\n'
        + f'normalized to the {tlabel} energy in all TICLCandidates')
    effnorm_label = (f'{tlabel} efficiency w.r.t. all matched TICLCandidates,\n'
        + f'normalized to the {tlabel} energy (approx.)')
    pur_label = f'Purity of all matched TICLCandidates w.r.t. {tlabel}'
    # colours: efficiency in red, truth-normalized efficiency in green, purity in blue
    # (lighter shades for the mean absolute change per truth object)
    colors = {
        'eff_all': ('#c0392b', '#f1948a'),
        'eff_all_truthnorm': ('#1e8449', '#82e0aa'),
        'pur_all': ('#2a78d6', '#7fb3ef'),
    }
    lc_legend = dict(fontsize=8, handlelength=4)
    metric_legend = dict(fontsize=7, loc='upper left', handlelength=4)

    plots = []
    # LayerCluster quantities per subdetector, relative to the default point
    for s in PLOT_SUBDETS:
        curves = [dict(column=f'rel_{q}_{s}', label=label, color=color, linestyle=linestyle, marker=marker)
            for q, (label, color, linestyle, marker) in LC_QUANTITIES.items()]
        plots.append(dict(curves=curves, ylabel=f'{PLOT_SUBDET_LABELS[s]}: value relative to default parameters',
            name='lc', axis='ratio', subdet=s, legend=lc_legend))
    # metric decomposition
    curves = [
        dict(column='eff_all', err='eff_all_err', label=eff_label, color=colors['eff_all'][0], linestyle='-', marker='o'),
        dict(column='eff_all_truthnorm', err='eff_all_truthnorm_err', label=effnorm_label,
            color=colors['eff_all_truthnorm'][0], linestyle='-', marker='o'),
        dict(column='pur_all', err='pur_all_err', label=pur_label, color=colors['pur_all'][0], linestyle='-', marker='o'),
        dict(column='T_frac', err='T_frac_err', label=f'{tlabel} energy in LayerClusters,\n'
            + f'normalized to the {tlabel} energy (approx.)', color='#a6a6a6', linestyle=':', marker='o'),
        dict(column='T_tc_frac', err='T_tc_frac_err', label=f'{tlabel} energy in LayerClusters in TICLCandidates,\n'
            + f'normalized to the {tlabel} energy (approx.)', color='#6b6b6b', linestyle='--', marker='o'),
    ]
    plots.append(dict(curves=curves, ylabel='Mean value', name='metrics', axis='fraction',
        legend=metric_legend, markersize=4))
    # metric changes
    curves = []
    for m, label in [('eff_all', eff_label), ('eff_all_truthnorm', effnorm_label), ('pur_all', pur_label)]:
        curves.append(dict(column=f'{m}_delta_mean', label=label, color=colors[m][0], linestyle='-', marker='o'))
        if show_abs_change:
            curves.append(dict(column=f'{m}_delta_abs', label=f'Same, mean absolute change per {tlabel}',
                color=colors[m][1], linestyle='--', marker='o'))
    plots.append(dict(curves=curves, ylabel='Change of the mean w.r.t. default parameters', name='metric_changes',
        axis='delta', legend=metric_legend, markersize=4))
    # combined: purity, truth-normalized efficiency and number of LayerClusters, relative to the default point
    for s in PLOT_SUBDETS:
        curves = [
            dict(column='rel_pur_all', label=pur_label, color=colors['pur_all'][0], linestyle='-', marker='o'),
            dict(column='rel_eff_all_truthnorm', label=effnorm_label, color=colors['eff_all_truthnorm'][0],
                linestyle='-', marker='s'),
            dict(column=f'rel_nlc_{s}', label=f'Number of LayerClusters in {PLOT_SUBDET_LABELS[s]}',
                color='#8e44ad', linestyle='--', marker='D'),
        ]
        plots.append(dict(curves=curves, ylabel='Value relative to default parameters', name='combined',
            axis='ratio', subdet=s, legend=dict(fontsize=7, handlelength=4)))

    for plot in plots:
        kwargs = dict(axis=plot['axis'], subdet=plot.get('subdet'), legend=plot['legend'],
            markersize=plot.get('markersize', 5))
        name = plot['name']
        if not flat:
            plot_curves(points, plot['curves'], plot['ylabel'], outputdir, name, **kwargs)
        else:
            for flat_sort in flat_sorts:
                plot_curves(points, plot['curves'], plot['ylabel'], outputdir, name,
                    flat=True, flat_sort=flat_sort, **kwargs)


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Sensitivity of LayerClusters and TICLCandidate metrics to CLUE parameters')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Grid scan output directory')
    parser.add_argument('-g', '--grids', default=None, nargs='+', help='Grids to use (default: all)')
    parser.add_argument('-t', '--truth_type', default='truthbranch-signal', choices=list(TRUTH_TYPES.keys()))
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output_scan_sensitivity'))
    parser.add_argument('--show_abs_change', default=False, action='store_true',
        help='Also show the mean absolute change per truth object in the plots of the changes')
    parser.add_argument('--flat', default=False, action='store_true',
        help='Show all grid points on a single axis, sorted (see --flat_sort)'
            + ' (works for any grid, including multi-parameter grids)')
    parser.add_argument('--flat_sort', default=list(FLAT_SORTS.keys()), nargs='+', choices=list(FLAT_SORTS.keys()),
        help='Sorting(s) of the grid points with --flat (one set of plots per sorting; default: all)')
    parser.add_argument('--workers', default=8, type=int,
        help='Number of parallel processes for reading the grid point outputs (default: 8)')
    args = parser.parse_args()

    # load all grids first, to define the reference truth energy per truth object:
    # the maximum truth energy in LayerClusters over all grid points of all grids
    grids = args.grids if args.grids is not None else get_grids(args.inputdir)
    reference_effdir = os.path.join(args.inputdir, DEFAULT_REFERENCE_JOB, 'efficiency')
    loaded = {}
    for grid in grids:
        print(f'Loading grid {grid}...')
        loaded[grid] = load_grid(os.path.join(args.inputdir, grid), args.truth_type,
            reference_effdir=reference_effdir, flat=args.flat, workers=args.workers)
    alltruth = pd.concat([t for _, t in [v for v in loaded.values() if v is not None]], ignore_index=True)
    t_ref = alltruth.groupby(['event', 'truth_index'])['T'].max().rename('T_ref').reset_index()

    for grid in grids:
        print(f'Processing grid {grid}...')
        if loaded[grid] is None:
            print(f'WARNING: no finished grid points found for {grid}, skipping.')
            continue
        lc, truth = loaded[grid]
        points = get_points(lc, add_normalized_quantities(truth, t_ref))
        if points is None:
            print(f'WARNING: no default point found for {grid}, skipping.')
            continue
        default = points[points['job'] == get_default_row(lc)['job']].iloc[0]
        print(f'  Truth energy in LayerClusters at the default point relative to the reference: {default["T_frac"]:.3f}')
        outputdir = os.path.join(args.outputdir, grid)
        os.makedirs(outputdir, exist_ok=True)
        points.to_csv(os.path.join(outputdir, f'summary_{args.truth_type}.csv'), index=False)
        plot_grid(points, args.truth_type, outputdir, show_abs_change=args.show_abs_change,
            flat=args.flat, flat_sorts=args.flat_sort)
