# Results of the hyperopt runs of the CLUE parameters

Plotting scripts for the output of `run-hgcal-reco-scan/run_hgcalreco_hyperopt_submit.py`
(one subdirectory `run<i>` per independent run, each with `trials.pkl` and one subdirectory `trial<i>` per trial).
They reuse the tools of the grid scan studies in `../clue-parameter-sensitivity` (loading, metrics, flat plots),
and only use the hyperopt outputs themselves.
The default parameter point is shown if it is in the hyperopt output: runs submitted with default values in their
grid file evaluate it as their first trial (flagged with `is_default`).

Common options: `-i <hyperopt output dir>` (default: the latest 5D HSi run, see `hyperoptutils.py`),
`-o <output dir>` (default: `output_<name of the input dir>` next to the scripts).

- `plot_hyperopt_progress.py`: the metric (hyperopt objective: average of the combined purity and the efficiency
  normalized to the RecHit energy) of all trials of all runs, vs the trial number (`metric_vs_trial`, chronological,
  with the running best per run as lines) and sorted by increasing metric per run (`metric_vs_trial_sorted`),
  each with all trials (`_all`) and without the worst 10% (`_best90`), with the average best result
  and the default point as horizontal lines;
  also writes a table with all trials (`trials.csv`).
- `plot_hyperopt_runs.py`: per run (`-r <runs>`, default all), the flat plots of the grid scans with the trials
  as points, sorted by the average of purity and efficiency and in chronological order
  (`<run>/<plot>_flat_average[_<subdet>].png` and `<run>/<plot>_flat_chronological[_<subdet>].png`, see `--flat_sort`),
  for the metrics and, relative to the default point, the metric changes, LayerCluster quantities and combined plots
  (see `--plots`),
  and a summary table per run (`<run>/summary_<truth type>.csv`, usable with
  `../clue-parameter-sensitivity/plot_param_distributions.py`).
- `plot_hyperopt_param_distributions.py`: the distributions of the parameter values of the best trials of each run
  (`--best_percent`, default 10), overlaid for all runs (`param_distributions_best<x>.png`; histograms of the continuous
  values with logarithmic bins over the search range, one bin per value for a discrete search space),
  with the default value as a dashed line, to see whether the runs converge to consistent values.
- `hyperoptutils.py`: common tools (finding the runs, reading the trials in chronological order).
