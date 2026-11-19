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
