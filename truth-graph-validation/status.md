# Truth graph: integration status and path to replacing SimClusters/CaloParticles

Reference notes from investigating [cms-sw/cmssw PR #51213](https://github.com/cms-sw/cmssw/pull/51213)
("MC-truth graph prototype", `PhysicsTools/TruthInfo`) for this repo. See
`README.md` in this directory for day-to-day usage of the dump tool; this file
is the longer-form summary of what works today, what doesn't, and why.

Status of the upstream code itself: **experimental prototype**, "under heavy
development, not open to external contributions" per its own README. Expect
the data model/APIs to change without notice.


## What's done and working in this repo

- **CMSSW**: `PhysicsTools/TruthInfo` merged into the local `CMSSW_20_0_0_pre1`
  checkout via `git cms-merge-topic 51213` (not part of the `pre1` release
  itself, but present on the `CMSSW_20_0_X` IB branch from ~2026-07-14
  onward). Compiles cleanly alongside the rest of this repo's patches.
- **Sample production**: `sample-production/produce.py --output-mode truth`
  enables the `enableTruth` process modifier and appends
  `VALIDATION:@baseValidation` to the RECO step's `--step` argument - the
  minimal addition that actually schedules the truth-graph producers
  (`baseCommonPreValidation`/`baseCommonValidation`/`postValidation_common`
  are empty sequences by default, only populated by `enableTruth`'s hooks).
  Deliberately narrower than the official relval recipe's full
  `@phase2Validation` preset, which would also pull in unrelated
  tracking/muon/jet/electron/photon/b-tag/tau/HCAL/HGCal/barrel/MTD/ECAL/HLT
  validation. No DQM/harvesting step is added, so validation histograms are
  computed (costing runtime) but never persisted - output stays small and
  single-file, keeping `TruthGraph`, `truth::Graph`, and
  `truth::LogicalGraphHitIndex` alongside the same lean reco-level content as
  `--output-mode hgcal`.
- **Re-reco**: `run-hgcal-reco`/`run-hgcal-reco-scan`'s templates
  (`hgcalreco_cff_template.py`, `hgcalreco_cff_template_noticl.py`) now keep
  the three truth-graph products as pass-through output, verified end-to-end.
  Note: they keep their *original* process label (`"RECO"` for the standard
  chain) even in re-reco'd files, since re-reco doesn't recompute them.
- **Visualization**: `dump_truth_graph.py` / `dump_truth_graph_cfg.py` in this
  directory render the graph to DOT/PNG/SVG/PDF directly from the persisted
  products (no need to keep raw SimTracks/RecHits around for this).


## Is there already a mapping to reco objects (LayerClusters/Tracksters/TICLCandidates)?

Short answer: **not usably, not yet.** Two different things exist upstream and
it's easy to conflate them:

### 1. `TruthBranchCaloAssociationProducer` - Branch <-> CaloParticle/SimCluster

Already running (part of `baseCommonPreValidation`, so already active in
`--output-mode truth` samples). Produces a real, persistable, TICL-style
`AssociationMap`, bidirectional, with shared-energy scores.

**But** this maps the *new* truth graph against the *old* truth objects
(CaloParticle, SimCluster) - it's a consistency check ("does the graph
correctly reproduce the legacy truth?"), not a mapping to reconstructed
objects. `BranchHGCalValidator` consumes it to produce "reproduction
efficiency" DQM plots for exactly this purpose.

### 2. `BranchTracksterRecoValidator` - Branch <-> ticl::Trackster (real reco objects)

This is the one that would actually matter for replacing CaloParticle/SimCluster
in our downstream analysis: it matches `ticl::Trackster` to `truth::Branch` via
shared hits, the direct analogue of what `analysis/efficiency/calculate_associations.py`
already does. It compiles and runs. However:

- **Deliberately excluded from the default validation sequence** (not part of
  `baseValidation`), so `--output-mode truth` does not run it. Confirmed from
  the upstream source comments, not inferred.
- **Why**: a meaningful efficiency needs the "interesting particles" reference
  set to be an *antichain* (no particle is an ancestor of another). A `Branch`
  subgraph aggregates all of a particle's descendants, so for anything that
  showers (photons, electrons, hadrons - i.e. everything relevant to HGCAL),
  a flat PDG-ID list is *not* a valid antichain: every ancestor's branch
  already contains its descendants' hits, so every match looks like a "merge"
  and the efficiency comes out near zero. The upstream authors' own comment:
  the proper fix (a detector-aware `BranchSelector` antichain, roughly "one
  Branch per CaloParticle") is explicitly **"not yet wired."** Only muons
  (non-showering) currently give meaningful numbers with this validator.
- **Output form**: fills DQM histograms in-memory only. No persisted per-event
  association product to read back the way `calculate_associations.py` does
  today (unlike `TruthBranchCaloAssociationProducer`, which does persist one).

It *can* be enabled by hand (real cfi: `branchTracksterRecoValidator` in
`PhysicsTools/TruthInfo/python/truthGraphValidation_cff.py`, runnable via
`test/validateBranchRecoDQM_cfg.py`) but the results would currently be
degenerate/meaningless for HGCAL objects specifically, per the code's own
caveats.


## What would be needed to actually replace SimClusters/CaloParticles downstream

1. **A proper antichain "interesting particles" selection for HGCAL/calo** -
   the specific piece the upstream authors flagged as unfinished. Without it,
   Trackster-level truth-graph validation is degenerate for anything but
   muons.
2. **A persistable Branch <-> Trackster/TICLCandidate association product** -
   e.g. a new producer analogous to `TruthBranchCaloAssociationProducer` but
   for `ticl::Trackster`, or a refactor of `BranchRecoValidator`'s existing
   matching logic into producer form. Does not exist upstream yet.
3. **TICLCandidate-level aggregation** on top of Trackster-level matching
   (summing over constituent Tracksters), mirroring
   `tools/tcassociationtools.py::get_ticl_candidate_matrices_from_trackster_associations`
   already built in this repo for the CaloParticle/SimCluster case.
4. **Flattening for FWLite/Python access**, mirroring this repo's own
   `FlattenTSToTSAssociator` custom EDProducer (see
   `cmssw_packages/HGCalCustomization/HGCalAssociations`).
5. All of the above sits on top of code that is explicitly "under heavy
   development, not open to external contributions" - expect to need rework
   as the upstream prototype evolves.

**Bottom line**: the raw truth graph and the CaloParticle/SimCluster
cross-check (`TruthBranchCaloAssociationProducer`) are usable today. The
reco-object-level piece - the part that would actually replace
`calculate_associations.py`'s CaloParticle/SimCluster-based validation - has a
known, upstream-acknowledged gap (the antichain selection) and a missing
persistence layer. Not a drop-in replacement yet.


## References

- PR: https://github.com/cms-sw/cmssw/pull/51213
- Docs (CERN SSO required): https://cms-truth.docs.cern.ch
- `PhysicsTools/TruthInfo/README.md` (in the CMSSW checkout, once merged)
- `PhysicsTools/TruthInfo/doc/branch_design.md` for the `Branch`/`BranchSelector` design
