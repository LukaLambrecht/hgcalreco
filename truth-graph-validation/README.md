# Truth graph validation

Tools to visualize the MC-truth graph (see `PhysicsTools/TruthInfo` in CMSSW) for
samples produced with `sample-production/produce.py --output-mode truth`.
See `status.md` for the integration status in this repository,
and the [documentation](https://cms-truth.docs.cern.ch) for the truth graph itself
(CERN SSO required; the sources are also available in
[this repository](https://github.com/felicepantaleo/cms-truth-docs)).

Status note: the truth graph is still under active development upstream.
Expect the data model/APIs (and the two files here that depend on them) to need updates
when moving to a newer CMSSW release.


## Prerequisites

- A CMSSW release from `CMSSW_20_1_X` onwards (tested with `CMSSW_20_1_0_pre5`),
  where the truth graph is part of the release (no merge-topic needed);
  see `cmssw_setup.sh` in the top directory.
- A sample produced with `--output-mode truth`, e.g.:
  ```
  cd ../sample-production
  python3 produce.py -f fragments/pion_gun_cfi.py -c cmsdriver/chain_200X_full_baseline.json \
    -w my_truth_sample -n 100 --output-mode truth
  ```
  This keeps the truth graph products (`TruthGraph`, `truth::Graph`,
  `truth::LogicalGraphHitIndex`) alongside the same lean reco-level content as
  `--output-mode hgcal`, in a single, compact output file.


## Usage

```
python3 dump_truth_graph.py -i /path/to/step2.root -o output_dir -n 5
```

This dumps `.dot` files (one raw-graph, one logical-graph per event) and, if
`graphviz` is available, renders them to `.png` alongside the `.dot` files.
Useful options:

- `-n / --maxevents`: number of events to process (default: all - can produce a
  lot of files for a large input).
- `--tag`: suffix for output file names, useful when dumping into a shared
  directory.
- `--process`: the process name the truth-graph producers *originally ran
  under*. Defaults to `"HLT"`, matching the standard sample-production chain,
  where the graph is built at DIGI (`step1_200X.sh`, which also runs the HLT and
  hence has process name `"HLT"`). Note this stays `"HLT"` even when dumping from a
  re-reco'd file (`run-hgcal-reco`/`run-hgcal-reco-scan` output): the truth
  graph products are pass-through there (re-reco doesn't recompute them, just
  keeps them - see those templates' output-content lists), so they keep their
  original process label, not the re-reco process's own name (e.g.
  `"HGCALTICL"`). If unsure, check with `edmDumpEventContent <file>.root |
  grep -i truth` - the process name is the last column.
- `--layout {dot,sfdp,fdp,neato}`: DOT graph layout for the *logical* graph
  dump. `dot` (default) draws a hierarchical left-to-right tree, good for
  normal decay chains. For very dense or highly-recombined graphs, a
  force-directed layout (`sfdp`/`fdp`/`neato`) can be easier to read.
- `--format {png,svg,pdf}`: image format. For large/busy events, `png` can hit
  graphviz's cairo bitmap size cap (it auto-scales down, with a "graph is too
  large" warning on stderr - harmless, but detail gets lost); `svg` or `pdf`
  render at full detail with no such cap.
- `--no-render`: only produce `.dot` files, skip the graphviz rendering step
  (e.g. if `graphviz` isn't installed - use `--no-render` and render the
  `.dot` files separately, or view them directly).

Each event produces two dumps:
- `truthgraph_<tag>_run<R>_lumi<L>_event<E>.dot` - the **raw** TruthGraph:
  every SimTrack/SimVertex/GenParticle node, largely unfiltered.
- `truthlogicalgraph_<tag>_run<R>_lumi<L>_event<E>.dot` - the **logical**
  graph: the merged, cleaned-up particle/vertex view with hit-count/energy
  annotations per node (direct and subgraph-aggregated, split by
  tracker/HGCal/MTD), generally the more useful one to look at first.


## Files

- `dump_truth_graph.py` - convenience wrapper: runs the dumper via `cmsRun`
  and renders the resulting `.dot` files to images.
- `dump_truth_graph_cfg.py` - the actual CMSSW config, run via `cmsRun`. Unlike
  the upstream `PhysicsTools/TruthInfo/test/dumpTruthGraphsFromGENSIMRECO_cfg.py`
  (which re-runs the truth-graph EDProducers from raw SimTracks/RecHits, so it
  needs an input file that carries those), this one reads the **already
  computed and persisted** `TruthGraph`/`truth::Graph`/
  `truth::LogicalGraphHitIndex` products directly from a `--output-mode truth`
  file and only runs the two dumper EDAnalyzers. This is what lets
  `--output-mode truth` keep its output small (no need to also carry raw
  `g4SimHits`/`generatorSmeared`) while still supporting this dump.
  It can also be run directly with `cmsRun` if you want the full argparse
  interface without the wrapper's rendering step:
  ```
  cmsRun dump_truth_graph_cfg.py /path/to/step2.root -n 5 -o output_dir
  ```
  (note: pass the input file path as a plain positional argument; if it's an
  absolute path, the script adds the `file:` prefix for you.)


## Rendering `.dot` files manually

If you skipped rendering (`--no-render`) or want a different format/engine:

```
dot -Tpng truthlogicalgraph_..._event1.dot -o event1.png
# or, for dense graphs:
sfdp -Tsvg truthlogicalgraph_..._event1.dot -o event1.svg
```
