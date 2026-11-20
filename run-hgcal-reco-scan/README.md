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
(see `analysis/efficiency/calculate_associations.py`), and the main metric in `result.json` (`metric`, `loss` = -`metric`)
is the one for the first requested truth type: the average of the mean combined purity of the TICLCandidates
matched to each truth object and the mean efficiency w.r.t. all matched TICLCandidates
(see `tools/hgcalrecotools.py::extract_tc_metric`; the same as the "average" sorting in
`analysis/studies/clue-parameter-sensitivity`). For truth Branches, the efficiency normalized to the truth
particle's energy in all RecHits is used (RecHit energy x its energy fraction, summed over all its HGCAL cells;
`eff_sum_rechits`), so energy lost in the LayerClustering is counted as inefficiency
(the outputs also contain the efficiency normalized to its energy in all TICLCandidates, `eff_sum_tc`).
CaloParticles (`cp`) and SimClusters (`sc`) are opt-in: only if they are requested with `--gen_level`,
the CaloParticle/SimCluster-based associations are also run in the re-reco (`useCaloTruth` in the config templates,
set via `tools/hgcalrecotools.py::uses_calo_truth`), CaloParticles/SimClusters are stored in its output,
and the corresponding efficiency output files are written.
In November 2026, leaving them out made the re-reco about 2.7 times faster on PU200 samples (14.4 to 5.4 s per event),
with identical truth-graph-based results.
The output files keep mentioning the truth type explicitly (e.g. `metrics_tc_truthbranch-signal.parquet`).


### Hyperopt runs

`run_hgcalreco_hyperopt_submit.py` runs a hyperopt (TPE) optimization of the re-reco parameters instead of a grid scan,
with one condor job per independent run (`--nruns`, in subdirectories `run<i>` of the working directory).
The search space is defined by the same grid files as the grid scans (`-g`), with `--space`:
`discrete` (default; choice between the listed values), or `uniform`/`loguniform` between the minimum and maximum
listed value of each parameter (`loguniform` falls back to `uniform` for parameters with a minimum <= 0).
Each trial runs `tools/hgcalrecotools.py::run_local_evaluation` and is stored in `trial<i>` (with its `result.json`);
the loss is minus the main metric (see "Truth reference" above).
All trials are stored in `trials.pkl` after each trial, so a resubmitted job continues where it stopped:
`--max_trials` is the total number of trials per run, and `--max_hours` an optional time budget per job
(no new trial is started if it would likely end after it; keep it below the wall time of `--job_flavour`,
e.g. 60 hours with `testmatch` = 3 days).
Example (5D HSi search space, 4 independent runs on one input file):
```
python3 run_hgcalreco_hyperopt_submit.py -i file_0.root -g grids/clue2d/splitparams/all_hsi_5d.json \
    --space loguniform --nruns 4 --max_trials 1000 --max_hours 60 --job_flavour testmatch \
    --do_composition --proxy $PROXY -w <output directory> --submit
```
Requires the `hyperopt` package for the CMSSW python version; for `CMSSW_20_1_0_pre5` (python 3.12, setuptools 83),
hyperopt 0.3.0 works (0.2.7 fails, since it needs `pkg_resources`), e.g. `python3 -m pip install --user --no-deps hyperopt==0.3.0`
(its dependencies are part of CMSSW).
