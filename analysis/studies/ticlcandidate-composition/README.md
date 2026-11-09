# Investigate TiclCandidate composition in terms of their LayerClusters

Use case: originally meant to investigate why varying CLUE parameters in HSi seems to have so little effect.
The working hypothesis is that even for pions, the TiclCandidates are mainly built from LayerClusters
in the EE part, such that the parametes in HSi barely impact the purity and efficiency.
The scripts in this folder are meant to verify that.
Maybe to be generalized later.

## Scripts

All scripts run on the output of `analysis/efficiency/calculate_associations.py` with `--do_composition`
(no re-reco ROOT files needed). Shared definitions (subdetector labels, truth categories,
loading and linking of the TICLCandidate and truth dataframes) are in `analysis/tools/compositiontools.py`.

- `plot_composition.py`: composition plots for a single re-reco, by default the default parameter point
  of the latest PU200 grid scan (`-i <efficiency output dir>`, `-t <truth types>`, `-o <output dir>`).
  Makes the TICLCandidate composition (count and energy), truth composition, TICLCandidate vs truth comparison,
  all LayerClusters vs LayerClusters in (matched) TICLCandidates per subdetector, and purity/efficiency
  per truth category; also writes `summary.json`.

The trends along the CLUE parameter scans are in `../clue-parameter-sensitivity`.
Definitions:
- Subdetector of a LayerCluster: from its seed DetId.
- TICLCandidate energy per subdetector: sum of LayerCluster energies, LayerClusters shared between Tracksters
  counted with their share (1 / vertex multiplicity).
- Truth energy per subdetector: shared energy with all LayerClusters, so only energy in clustered cells
  (the same reference as used in the efficiency definition).
- Truth categories: by fraction of truth energy in CE-E (CE-E dominated: at least 2/3; CE-H dominated: at most 1/3).
- Primary TICLCandidate: the matched TICLCandidate with the highest efficiency for a given truth object.
- All matched TICLCandidates: all TICLCandidates whose best-matching truth object (highest purity) is the given one,
  combined by summing their energies (and LayerCluster counts) per subdetector.
  The corresponding metrics are the efficiency summed over them (`eff_sum`) and the purity of each of them separately.
