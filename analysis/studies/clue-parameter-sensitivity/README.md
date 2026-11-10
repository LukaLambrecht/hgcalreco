# Investigate the sensitivity of TICLCandidate purity and efficiency to the CLUE parameters

Use case: varying the CLUE parameters in HSi seems to have very little effect on the TICLCandidate
purity and efficiency. The TICLCandidate composition study (`../ticlcandidate-composition`) showed that this
is not because TICLCandidates are mostly built from CE-E LayerClusters (about half of the signal pion energy
is in CE-H silicon and ends up in its TICLCandidates). Open leads:
- some parameters (e.g. deltac and deltao in HSi) barely change the number of LayerClusters at all;
- the efficiency (and the truth energy per subdetector) is normalized to the energy in LayerClusters only,
  so removing LayerClusters is not penalized (to do: normalize to the full truth energy instead).

## Scripts

All scripts run on a grid scan output directory (default: the latest PU200 scan, see `scanutils.py`),
with `calculate_associations.py` run with `--do_composition`, and use `truthbranch-signal` as truth reference by default.
Common options: `-i <scan output dir>`, `-g <grids>`, `-t <truth type>`, `-o <output dir>`.

- `lc_sensitivity.py`: how much does each parameter change the LayerClusters themselves?
  Per subdetector and grid point: number of LayerClusters, their total and mean energy, their energy in
  TICLCandidates, and the signal particle energy in them, relative to the default point.
  Overview heatmaps/tables of the maximum relative change per grid (full range and within a factor `--window`
  of the default), and a printed list of grids that change none of the CE-H silicon quantities by more
  than `--threshold`.
- `metric_sensitivity.py`: why do efficiency and purity barely change for the parameters that do change the
  LayerClusters? Follows each truth object across the grid points, and tests (1) the normalization
  (efficiency rescaled to a fixed reference energy per truth object, approximate)
  and (2) cancellation (change of the mean vs mean absolute change per truth object).
- `plot_scan_trends.py`: general trends of the composition and metrics (incl. per truth category)
  vs the scanned parameter.
- `scanutils.py`: common tools (default parameter values, axis labels, grid point iteration, plotting helpers).

To do: the rescaled efficiency in `metric_sensitivity.py` is approximate, since only the efficiency
(not the absolute shared energy of the primary TICLCandidate) is stored;
storing the absolute shared energies in `calculate_associations.py` would make it exact.
