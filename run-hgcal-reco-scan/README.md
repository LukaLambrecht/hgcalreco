# Run HGCAL reconstruction over many parameter variations


At first try simple grid scans (in one and multiple dimensions),
later try more directed searches using e.g. expected improvement criterion.


### Multiple input files

Each grid point (job) runs the re-reco and the efficiency calculation
(see `tools/hgcalrecotools.py::run_local_evaluation`).
With multiple input files (`-i file_0.root file_1.root ...`), by default both steps run separately per input file,
and the efficiency outputs are combined at the end, with the event numbers of the i-th file offset by i x 1000000
(the same convention as `analysis/efficiency/calculate_associations.py` uses for multiple input files);
`-n`/`--max_events` then applies per input file.
With `--no_per_file`, a single re-reco runs over all input files instead, followed by a single efficiency calculation
on its output. Note: in November 2026, this failed for about 20% of the grid points with three PU200 input files
(std::bad_alloc in FWLite when reading the first event of the second input file; cause not understood).


### Truth reference

The default truth reference is the MC-truth graph: `--gen_level` defaults to `truthbranch-signal`
(see `analysis/efficiency/calculate_associations.py`), and the main metric in `result.json` (`metric`, `loss`)
is the one for the first requested truth type.
CaloParticles (`cp`) and SimClusters (`sc`) are opt-in: only if they are requested with `--gen_level`,
the CaloParticle/SimCluster-based associations are also run in the re-reco (`useCaloTruth` in the config templates,
set via `tools/hgcalrecotools.py::uses_calo_truth`), CaloParticles/SimClusters are stored in its output,
and the corresponding efficiency output files are written.
In November 2026, leaving them out made the re-reco about 2.7 times faster on PU200 samples (14.4 to 5.4 s per event),
with identical truth-graph-based results.
The output files keep mentioning the truth type explicitly (e.g. `metrics_tc_truthbranch-signal.parquet`).
