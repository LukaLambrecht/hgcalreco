# Per hyperopt run: the same "flat" plots as for the grid scans (see ../clue-parameter-sensitivity/scan_sensitivity.py),
# with the trials of the run as points, sorted by the average of purity and efficiency and in chronological order
# (by default, see --flat_sort; metrics_flat_average.png and metrics_flat_chronological.png):
# the mean efficiencies (normalized to the energy in all TICLCandidates and in RecHits), the mean purity, and the
# fractions of the truth energy in LayerClusters (in TICLCandidates).
# The default point (the first trial of the run, see hyperoptutils.py::get_default_point) is marked "default",
# and the plots relative to it (metric changes, LayerCluster quantities, combined) are made as well (see --plots).
# Only the hyperopt outputs are used.
#
# Output: <outputdir>/<run>/ with the plots and a summary table (summary_<truth type>.csv, one row per trial,
# with param_<name> columns, so it can also be used with ../clue-parameter-sensitivity/plot_param_distributions.py).
#
# Example: python3 plot_hyperopt_runs.py -i <hyperopt output dir> [-r run0 run1]


import os
import sys
import argparse
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

from hyperoptutils import DEFAULT_INPUT, get_default_outputdir
from hyperoptutils import get_runs, load_trials, get_metric, get_default_point
from scan_sensitivity import load_job, get_points, plot_grid, FLAT_SORTS


def load_run(rundir, truth_type, workers=8):
    '''
    Load the successful trials of a run, in the same format as scan_sensitivity.py::load_grid (with flat=True):
    returns (per-trial DataFrame, per-truth-object DataFrame, per-event DataFrame), with the trials labelled by their
    chronological index (param_value), whether they are the default point (is_default, see
    hyperoptutils.py::get_default_point), and the hyperopt metric of each trial (metric).
    '''
    trials = load_trials(rundir)
    default = get_default_point(rundir, trials)
    jobs = []
    for trial in [trial for trial in trials if trial['status'] == 'ok']:
        effdir = os.path.join(trial['trial_dir'], 'efficiency')
        name = f'trial{trial["index"]}'
        meta = {'param_name': 'flat', 'param_value': trial['index'],
            'is_default': default is not None and trial['index'] == default['index'], 'metric': trial['metric'],
            **{f'param_{name}': value for name, value in trial['params'].items()}}
        jobs.append((name, meta, effdir))
    effdirs = [effdir for _, _, effdir in jobs]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(load_job, effdirs, [truth_type] * len(effdirs), chunksize=8))
    lc_rows, truth_dfs, event_dfs = [], [], []
    for (name, meta, _), (lc, truth, events) in zip(jobs, results):
        # consistency check: the metric recomputed from the efficiency output is the hyperopt metric
        if abs(get_metric(truth) - meta['metric']) > 1e-9:
            print(f'WARNING: {rundir}/{name}: recomputed metric {get_metric(truth)} differs from the hyperopt metric {meta["metric"]}.')
        lc_rows.append({'job': name, **meta, **lc})
        truth['job'] = name
        truth_dfs.append(truth)
        events['job'] = name
        event_dfs.append(events)
    return pd.DataFrame(lc_rows), pd.concat(truth_dfs, ignore_index=True), pd.concat(event_dfs, ignore_index=True)


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Per hyperopt run: flat plots of the trials (as for the grid scans)')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT, help='Hyperopt output directory')
    parser.add_argument('-r', '--runs', default=None, nargs='+', help='Runs to plot (default: all)')
    parser.add_argument('-t', '--truth_type', default='truthbranch-signal')
    parser.add_argument('-o', '--outputdir', default=None,
        help='Output directory (default: output_<name of the input directory, without "output_"> next to this script)')
    parser.add_argument('--flat_sort', default=['average', 'chronological'], nargs='+', choices=list(FLAT_SORTS.keys()),
        help='Sorting(s) of the trials (one plot per sorting; default: by the average of purity and efficiency,'
            + ' and chronological)')
    parser.add_argument('--plots', default=['metrics', 'metric_changes', 'lc', 'combined'], nargs='+',
        choices=['metrics', 'metric_changes', 'lc', 'combined'],
        help='Plots to make (default: all; all but metrics are relative to the default point,'
            + ' so they are only made if the run has one)')
    parser.add_argument('--fontscale', default=1.3, type=float,
        help='Scale factor for the font sizes, w.r.t. the grid scan plots (default: 1.3)')
    parser.add_argument('--workers', default=8, type=int,
        help='Number of parallel processes for reading the trial outputs (default: 8)')
    args = parser.parse_args()
    outputdir = args.outputdir or get_default_outputdir(args.inputdir)

    rundirs = get_runs(args.inputdir)
    if args.runs is not None: rundirs = [d for d in rundirs if os.path.basename(d) in args.runs]
    for rundir in rundirs:
        run = os.path.basename(rundir)
        print(f'Processing {run}...')
        lc, truth, events = load_run(rundir, args.truth_type, workers=args.workers)
        plots = args.plots
        if not lc['is_default'].any():
            print(f'WARNING: no default point found for {run}; only making the plots that do not need one.')
            plots = [p for p in plots if p == 'metrics']
        points = get_points(lc, truth, events=events, require_default=False)
        rundir_out = os.path.join(outputdir, run)
        os.makedirs(rundir_out, exist_ok=True)
        points.to_csv(os.path.join(rundir_out, f'summary_{args.truth_type}.csv'), index=False)
        plot_grid(points, args.truth_type, rundir_out, flat=True, flat_sorts=args.flat_sort,
            flat_xlabel={s: 'Hyperopt trial (chronological)' if s == 'chronological' else 'Hyperopt trial' for s in FLAT_SORTS},
            names=plots, fontscale=args.fontscale, legend_outside=True)
