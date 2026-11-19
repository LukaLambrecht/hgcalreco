# Investigate the sensitivity of TICLCandidate purity and efficiency to the CLUE parameters

Use case: varying the CLUE parameters in HSi seems to have very little effect on the TICLCandidate
purity and efficiency. The TICLCandidate composition study (`../ticlcandidate-composition`) showed that this
is not because TICLCandidates are mostly built from CE-E LayerClusters (about half of the signal pion energy
is in CE-H silicon and ends up in its TICLCandidates). Open leads:
- some parameters (e.g. deltac and deltao in HSi) barely change the number of LayerClusters at all;
- the efficiency (and the truth energy per subdetector) is normalized to the energy in LayerClusters only,
  so removing LayerClusters is not penalized (to do: normalize to the full truth energy instead).

## Scripts

All scripts run on a grid scan output directory (default: the latest 1D PU200 scan, see `scanutils.py`),
with `calculate_associations.py` run with `--do_composition`, and use `truthbranch-signal` as truth reference by default.
Common options: `-i <scan output dir>`, `-g <grids>`, `-t <truth type>`, `-o <output dir>`.

- `scan_sensitivity.py`: per grid, one table with
  one row per grid point (`<output dir>/<grid>/summary_<truth type>.csv`) with
  - the LayerCluster quantities per subdetector and for HGCAL as a whole (number of LayerClusters, their total
    and mean energy, their energy in TICLCandidates, the signal particle energy in them and in TICLCandidates),
    also relative to the default point;
  - the metrics w.r.t. all matched TICLCandidates: efficiency, purity and truth-normalized efficiency
    (the efficiency normalized to the truth energy, approximately), with their changes w.r.t. the default point;

  and plots of these vs the scanned parameter: `metrics_vs_param`, `metric_changes_vs_param`, and per subdetector
  (`ee`, `hsi`, `hsci`, and `hgcal` for their sum) `lc_vs_param_<subdet>` (LayerCluster quantities) and
  `combined_vs_param_<subdet>` (purity, truth-normalized efficiency and number of LayerClusters,
  relative to the default point).
  With `--flat` (for any grid, including multi-parameter grids), all grid points are shown on a single axis instead,
  sorted by the mean purity, the mean truth-normalized efficiency, their average, and the number of LayerClusters
  (per subdetector, or in HGCAL; one set of plots `<plot>_flat_<sorting>[_<subdet>].png` each, see `--flat_sort`).
  Grid points are read in parallel processes (`--workers`, default 8).
- `plot_param_distributions.py`: distributions of the parameter values for a range of grid points
  (e.g. in a flat plot) after sorting, from a summary CSV file of `scan_sensitivity.py --flat`.
- `plot_scan_trends.py`: general trends of the composition and metrics (incl. per truth category)
  vs the scanned parameter.
- `scanutils.py`: common tools (default parameter values, axis labels, grid point iteration, plotting helpers).

Outputs: `output_scan_sensitivity` (1D scans, 2026-11-09) and `output_scan_sensitivity_5d` (5D HSi scan, 2026-11-13, `--flat`).

To do: the truth-normalized efficiency is approximate, since only the efficiency (not the absolute shared energy
with the matched TICLCandidates) is stored; storing the absolute shared energies in `calculate_associations.py`
would make it exact.
