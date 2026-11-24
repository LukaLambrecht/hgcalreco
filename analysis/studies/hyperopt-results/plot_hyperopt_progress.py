# Progress of the hyperopt runs: the metric (hyperopt objective) of each trial, for all runs on the same plot.
#
# Plots (in the output directory), each in two versions: with all trials (suffix _all), and without the worst
# 10% of all trials, zoomed on the range of the others (suffix _best90, see --discard_fraction):
# - metric_vs_trial: the metric vs the trial number (chronological), one colour per run,
#   with the running best per run as a line;
# - metric_vs_trial_sorted: the same, with the trials of each run sorted by increasing metric.
# The average over the runs of the metric of their best trial is shown as a horizontal line,
# as well as the metric at the default point (if available in the hyperopt output, see hyperoptutils.py::get_default_point).
# Only the hyperopt outputs are used.
# Also writes a summary table (trials.csv) with one row per trial (run, chronological index, status, metric, parameters).
#
# Example: python3 plot_hyperopt_progress.py -i <hyperopt output dir>


import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

from hyperoptutils import DEFAULT_INPUT, get_default_outputdir
from hyperoptutils import get_runs, load_trials, get_default_point
from scanutils import savefig


METRIC_LABEL = 'Average of purity and efficiency'


def plot_progress(df, outputdir, sort=False, discard_fraction=0., default_metric=None):
    '''
    Metric vs trial for all runs (df: one row per trial, see main), chronological or sorted per run.
    discard_fraction: fraction of all trials (the worst ones) not to show; the y-axis is zoomed on the others.
    default_metric: metric at the default point (shown as a horizontal line if not None).
    In the sorted version, each trial keeps its position (rank) within its run.
    '''
    runs = list(dict.fromkeys(df['run']))
    # one colour per run from the "cool" colour map (not meant to distinguish individual runs)
    cmap = plt.get_cmap('cool')
    def run_color(idx): return cmap(idx / max(len(runs) - 1, 1))
    threshold = df['metric'].quantile(discard_fraction) if discard_fraction > 0 else -np.inf
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for idx, run in enumerate(runs):
        d = df[(df['run'] == run) & df['metric'].notna()]
        color = run_color(idx)
        if not sort:
            x, y = d['index'].values, d['metric'].values
            best = d['metric'].cummax().values
            keep = (y >= threshold)
            ax.plot(x[keep], y[keep], linestyle='none', marker='o', markersize=3, color=color, alpha=0.6)
            ax.plot(x[best >= threshold], best[best >= threshold], linestyle='-', linewidth=1.5, color=color, label=run)
        else:
            y = np.sort(d['metric'].values)
            x = np.arange(len(y))
            keep = (y >= threshold)
            ax.plot(x[keep], y[keep], linestyle='-', linewidth=1.5, marker='o', markersize=2, color=color, label=run)
    # average over the runs of their best trial
    best_average = df.groupby('run')['metric'].max().mean()
    ax.axhline(best_average, color='red', linestyle='--', linewidth=2, label='Best result (average)', zorder=5)
    if default_metric is not None:
        ax.axhline(default_metric, color='black', linestyle=':', linewidth=2, label='Default parameters', zorder=5)
    ax.set_xlabel('Trial (sorted by increasing metric)' if sort else 'Trial (chronological)', fontsize=16)
    ax.set_ylabel(METRIC_LABEL, fontsize=16)
    ax.tick_params(axis='both', labelsize=14)
    shown = df['metric'][df['metric'] >= threshold]
    low, high = shown.min(), shown.max()
    if default_metric is not None: low = min(low, default_metric)
    ax.set_ylim(low - 0.05 * (high - low), high + 0.05 * (high - low))
    ax.grid(axis='y', color='#e6e6e6', linewidth=0.8)
    ax.set_axisbelow(True)
    # legend: only the first and last run (with "..." in between), and the horizontal lines
    handles, labels = ax.get_legend_handles_labels()
    lines = {label: handle for handle, label in zip(handles, labels)}
    entries = [(lines[runs[0]], runs[0])]
    if len(runs) > 2: entries.append((Line2D([], [], linestyle='none'), '...'))
    if len(runs) > 1: entries.append((lines[runs[-1]], runs[-1]))
    entries += [(lines[label], label) for label in ['Best result (average)', 'Default parameters'] if label in lines]
    title = 'Lines: running best per run\nMarkers: all trials' if not sort else None
    ax.legend([h for h, _ in entries], [l for _, l in entries], fontsize=11, loc='center left',
        bbox_to_anchor=(1.01, 0.5), title=title, title_fontsize=11)
    fig.tight_layout()
    name = 'metric_vs_trial_sorted' if sort else 'metric_vs_trial'
    suffix = f'_best{round(100 * (1 - discard_fraction))}' if discard_fraction > 0 else '_all'
    savefig(fig, outputdir, name + suffix)


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Plot the progress of hyperopt runs')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Hyperopt output directory')
    parser.add_argument('-o', '--outputdir', default=None,
        help='Output directory (default: output_<name of the input directory, without "output_"> next to this script)')
    parser.add_argument('--discard_fraction', default=0.1, type=float,
        help='Fraction of the worst trials (of all runs together) not to show in the zoomed version of the plots'
            + ' (default: 0.1)')
    args = parser.parse_args()
    outputdir = args.outputdir or get_default_outputdir(args.inputdir)

    rows = []
    rundirs = get_runs(args.inputdir)
    default_metrics = []
    for rundir in rundirs:
        trials = load_trials(rundir)
        for trial in trials:
            rows.append({'run': os.path.basename(rundir), 'index': trial['index'], 'status': trial['status'],
                'metric': trial['metric'], 'is_default': trial['is_default'], 'trial_dir': trial['trial_dir'],
                **{f'param_{name}': value for name, value in trial['params'].items()}})
        default = get_default_point(rundir, trials)
        if default is not None: default_metrics.append(default['metric'])
    df = pd.DataFrame(rows)
    print(f'Found {len(rundirs)} runs with {len(df)} trials ({(df["status"] != "ok").sum()} not ok).')
    # metric at the default point (the same for all runs on the same events; averaged over the runs otherwise)
    default_metric = np.mean(default_metrics) if len(default_metrics) > 0 else None
    print(f'Default point found for {len(default_metrics)} runs' + (f', metric: {default_metric:.4f}' if default_metric else ''))

    os.makedirs(outputdir, exist_ok=True)
    df.to_csv(os.path.join(outputdir, 'trials.csv'), index=False)
    for sort in [False, True]:
        plot_progress(df, outputdir, sort=sort, default_metric=default_metric)
        plot_progress(df, outputdir, sort=sort, discard_fraction=args.discard_fraction, default_metric=default_metric)
