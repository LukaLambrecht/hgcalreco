# Truth graph: integration status and path to replacing SimClusters/CaloParticles

Reference notes on using the MC-truth graph (`PhysicsTools/TruthInfo`,
`SimGeneral/TruthGraphAssociatorProducers`) in this repository.
See `README.md` in this directory for day-to-day usage of the dump tool,
and the [documentation](https://cms-truth.docs.cern.ch) for the truth graph itself
(sources in [this repository](https://github.com/felicepantaleo/cms-truth-docs)).


## History

- Up to `CMSSW_20_0_X`: experimental prototype from
  [cms-sw/cmssw#51213](https://github.com/cms-sw/cmssw/pull/51213), merged in by hand.
  Only the graph itself and a Branch <-> CaloParticle/SimCluster cross-check were usable;
  there was no proper truth definition for showering particles
  and no persisted association to reco objects.
- From `CMSSW_20_1_0_pre5` onwards (used here), both are solved upstream:
  - [cms-sw/cmssw#51716](https://github.com/cms-sw/cmssw/pull/51716) adds truth *levels*
    (e.g. `signal`, `caloBoundary`, `reconstructableFinalState`), flags on the graph
    that each define a valid set of truth objects (no member is an ancestor of another).
  - [cms-sw/cmssw#51829](https://github.com/cms-sw/cmssw/pull/51829) adds the association layer:
    `TruthBranchTargetsProducer` (candidate truth Branches and one efficiency denominator per level)
    and per-domain reco-to-truth associators, among which `truthBranchTracksterAssociators`.


## What's done and working in this repository

- **Sample production**: the graph is built at DIGI by default for all Run4 eras
  (the `enableTruth` process modifier is part of the era), so `--output-mode truth`
  in `sample-production/produce.py` only needs to keep the products in the final output:
  `truth::Graph` (`truthLogicalGraphProducer`), `truth::LogicalGraphHitIndex`
  (`truthLogicalGraphHitIndexProducer`) and the raw `TruthGraph` (`mix`),
  all with process name `HLT` (the DIGI step).
  Measured on a 20-event single pion sample: about 43 kB/event compressed in total
  (compared to about 31 kB/event for CaloParticles + SimClusters).
- **Re-reco**: the templates in `run-hgcal-reco` and `run-hgcal-reco-scan` automatically
  run the truth associations if the input contains the truth graph:
  - `truthBranchTargets` (kept in the output).
  - `truthBranchTracksterAssociators` for `ticlTrackstersCLUE3DHigh` and `ticlCandidate`
    (only `ticlCandidate` in the `tc_only` template), with all working points
    (`Fixed`, `AdaptiveTight`, `AdaptiveNominal`).
  - The resulting maps are flattened for FWLite access by `FlattenTruthBranchAssociator`
    (see `cmssw_packages/HGCalCustomization/HGCalAssociations`), e.g. for `ticlCandidate`:
    `flattenTiclCandidateRecoToTruthFixed:ticlCandidateRecoToTruthFixedFlat{TSIdx,BranchIdx,SharedEnergy,Score}`
    and `flattenTiclCandidateTruthToReco:ticlCandidateTruthToRecoFlat{BranchIdx,TSIdx,SharedEnergy,Score}`.
    Truth Branches are identified by the particle id of their root in the `truth::Graph`.
    Note: this particle id is not the same as the index of the corresponding CaloParticle
    (e.g. for a pion gun, CaloParticle 0 can be the pi+ while particle 0 in the graph is the pi-).
    Note: in the TruthToReco maps, `SharedEnergy` is the shared energy fraction
    normalized to the truth Branch.
  - LayerCluster to truth Branch associations, with a custom producer
    (`LayerClusterToTruthBranchAssociatorProducer` in `cmssw_packages/HGCalCustomization/HGCalAssociations`;
    not available upstream) that follows exactly the same logic and output format as the upstream
    trackster associator, only with a LayerCluster as reco object.
    Optional via `truthGraphLayerClusters` in the templates (on by default, not in the `tc_only` template).
    Flattened as e.g. `flattenHgcalMergeLayerClustersRecoToTruthFixed:hgcalMergeLayerClustersRecoToTruthFixedFlat{LCIdx,BranchIdx,SharedEnergy,Score}`.
    Validated on 3 single pion events against the existing LayerCluster to CaloParticle association:
    the same LayerClusters are matched, every LayerCluster's best Branch descends from the same pion
    as its best CaloParticle, and the scores are identical where the best Branch is the pion itself.
    Cost: about 6 ms/event (out of about 5.5 s/event for the full re-reco, no pileup).
- **Visualization**: `dump_truth_graph.py` / `dump_truth_graph_cfg.py` in this
  directory render the graph to DOT/PNG/SVG/PDF directly from the persisted products.
- **Python access**: `PhysicsTools.TruthInfo.graphTools.eventGraphs` gives a per-event view
  of the graph (particles, kinematics, levels, navigation) directly from an EDM file.


## What's still to do

- Use the truth Branch associations in `analysis/efficiency/calculate_associations.py`
  as an alternative to CaloParticles/SimClusters, with a configurable truth level
  (e.g. `signal` for particle guns) and working point,
  and validate against the CaloParticle-based results on the same events.
- Measure the cost of the associations (in particular the LayerCluster one) with pileup.
