# Parameter distributions of the best trials of each hyperopt run, overlaid for all runs
# (similar to ../clue-parameter-sensitivity/plot_param_distributions.py for the grid scans),
# to see whether the independent runs converge to consistent parameter values.
#
# For each run, the best x% of its trials (by the hyperopt metric, see --best_percent) are selected,
# and for each parameter, the fraction of the selected trials per bin is shown (one line per run).
# Bins: logarithmic between the minimum and maximum value in the grid file of the hyperopt output (grid.json)
# for positive parameters (linear otherwise), or one bin per value for a discrete search space.
# The default value (from grid.json, if available) is shown as a dashed line.
#
# Output: param_distributions_best<x>.png in the output directory.
#
# Example: python3 plot_hyperopt_param_distributions.py -i <hyperopt output dir> --best_percent 10


import os
import sys
import json
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

from hyperoptutils import DEFAULT_INPUT, get_default_outputdir
from hyperoptutils import get_runs, load_trials
from scanutils import PARAM_LABELS


def get_bins(el, values, nbins):
    '''
    Bin edges for a parameter (el: its entry in grid.json; values: all its trial values):
    one bin per grid value if all trial values are grid values (discrete search space),
    else nbins bins between the minimum and maximum grid value (logarithmic if positive).
    Returns (bin edges, whether the x-axis is logarithmic, grid values for discrete bins or None).
    '''
    grid_values = np.sort(np.array(el['values'], dtype=float))
    if all(np.any(np.isclose(v, grid_values)) for v in values):
        # discrete: bin edges halfway between the values (in log space if all positive)
        log = grid_values.min() > 0
        x = np.log(grid_values) if log else grid_values
        mid = (x[1:] + x[:-1]) / 2
        first = x[0] - (mid[0] - x[0] if len(mid) > 0 else 0.5)
        last = x[-1] + (x[-1] - mid[-1] if len(mid) > 0 else 0.5)
        edges = np.concatenate([[first], mid, [last]])
        return (np.exp(edges) if log else edges), log, grid_values
    vmin, vmax = grid_values.min(), grid_values.max()
    if vmin > 0: return np.geomspace(vmin, vmax, nbins + 1), True, None
    return np.linspace(vmin, vmax, nbins + 1), False, None


def plot_param_distributions(selected, grid, outputfile, title=None, nbins=15):
    '''
    One panel per parameter, with the fraction of the selected trials per bin for each run.
    selected: dict run -> list of selected trials (see hyperoptutils.py::load_trials); grid: content of grid.json.
    '''
    runs = list(selected.keys())
    cmap = plt.get_cmap('cool')
    def run_color(idx): return cmap(idx / max(len(runs) - 1, 1))
    fig, axs = plt.subplots(1, len(grid), figsize=(4.2 * len(grid), 4.6), squeeze=False)
    for ax, el in zip(axs[0], grid):
        name = el['name']
        allvalues = [trial['params'][name] for trials in selected.values() for trial in trials]
        edges, log, discrete_values = get_bins(el, allvalues, nbins)
        for idx, run in enumerate(runs):
            values = np.array([trial['params'][name] for trial in selected[run]])
            counts, _ = np.histogram(values, bins=edges)
            fractions = counts / max(len(values), 1)
            ax.stairs(fractions, edges, color=run_color(idx), linewidth=1.5, label=run)
        if log: ax.set_xscale('log')
        if discrete_values is not None:
            ax.set_xticks(discrete_values)
            ax.set_xticklabels([f'{v:g}' for v in discrete_values])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if log and discrete_values is None:
            # labelled ticks at the grid values (the range of the search space and the values of the grid scan)
            ticks = np.sort(np.array(el['values'], dtype=float))
            ax.set_xticks(ticks)
            ax.set_xticklabels([f'{v:g}' for v in ticks])
        ax.set_xlim(edges[0], edges[-1])
        if 'default' in el:
            ax.axvline(el['default'], color='#1a1a1a', linestyle='--', linewidth=1.5, label='Default value')
        ax.set_xlabel(PARAM_LABELS.get(name, name), fontsize=15)
        ax.tick_params(axis='both', labelsize=12)
        ax.set_ylim(0, None)
        ax.grid(axis='y', color='#e6e6e6', linewidth=0.8)
        ax.set_axisbelow(True)
    axs[0][0].set_ylabel('Fraction of selected trials', fontsize=15)
    # legend: only the first and last run (with "..." in between), and the default value
    handles, labels = axs[0][0].get_legend_handles_labels()
    lines = {label: handle for handle, label in zip(handles, labels)}
    entries = [(lines[runs[0]], runs[0])]
    if len(runs) > 2: entries.append((Line2D([], [], linestyle='none'), '...'))
    if len(runs) > 1: entries.append((lines[runs[-1]], runs[-1]))
    if 'Default value' in lines: entries.append((lines['Default value'], 'Default value'))
    fig.legend([h for h, _ in entries], [l for _, l in entries], fontsize=12, loc='center left', bbox_to_anchor=(1.0, 0.5))
    if title is not None: fig.suptitle(title, fontsize=15)
    fig.tight_layout()
    # (bbox_inches='tight' to include the legend outside the axes)
    fig.savefig(outputfile, bbox_inches='tight')
    plt.close(fig)
    print(f'Created figure {outputfile}')


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Parameter distributions of the best trials of each hyperopt run')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Hyperopt output directory')
    parser.add_argument('-o', '--outputdir', default=None,
        help='Output directory (default: output_<name of the input directory, without "output_"> next to this script)')
    parser.add_argument('--best_percent', default=10., type=float,
        help='Percentage of the best trials (by metric) of each run to select (default: 10)')
    parser.add_argument('--nbins', default=15, type=int, help='Number of bins for continuous parameters (default: 15)')
    args = parser.parse_args()
    outputdir = args.outputdir or get_default_outputdir(args.inputdir)

    with open(os.path.join(args.inputdir, 'grid.json')) as f: grid = json.load(f)
    selected = {}
    for rundir in get_runs(args.inputdir):
        trials = [trial for trial in load_trials(rundir) if trial['status'] == 'ok']
        trials = sorted(trials, key=lambda trial: -trial['metric'])
        nselected = max(int(round(len(trials) * args.best_percent / 100)), 1)
        selected[os.path.basename(rundir)] = trials[:nselected]
    nselected = [len(trials) for trials in selected.values()]
    print(f'Selected the best {args.best_percent:g}% of the trials of {len(selected)} runs'
          + f' ({min(nselected)} to {max(nselected)} trials per run).')

    os.makedirs(outputdir, exist_ok=True)
    plot_param_distributions(selected, grid, os.path.join(outputdir, f'param_distributions_best{args.best_percent:g}.png'),
        title=f'Best {args.best_percent:g}% of the trials of each run')
