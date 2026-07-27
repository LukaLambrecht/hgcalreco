# CMSSW config file for HGCAL reconstruction
# Variant restricted to TICLCandidate-vs-CaloParticle metrics only.

# Note:
# This is a trimmed-down variant of hgcalreco_cff_template.py, meant for grid scans that
# only need "tc"-level metrics (TICLCandidate <-> CaloParticle association, as computed
# by analysis/efficiency/calculate_associations.py with --do_tc_level and the default
# recalculate=False). Do NOT use this template if you also need LayerCluster-level
# ("lc"-level) metrics, SimClusters, or the pre-merge Trackster collections
# (CLUE3DHigh/Recovery/TracksterLinks) for anything else - those are dropped here,
# both from the output and (where possible) from being computed at all.
#
# Compared to hgcalreco_cff_template.py, this drops:
# - Output content: SimClusters/SimClustersRefs, LayerClusters, the inclusive and PU
#   variants of ticlSimTracksters (only ":fromCPs" is kept), the pre-merge Trackster
#   collections (CLUE3DHigh/Recovery/TracksterLinks(SuperclusteringDNN)), pfTICL, and
#   all "flatten*" association products except the TICLCandidate<->CP-SimTrackster one.
#   Measured on a ~2.47 GB (100-event) reference file restricted to this template's
#   output collections: this cuts it down to ~577 MB (about 23% of the original),
#   see the conversation this template was introduced in for the full breakdown.
# - Processing (not just output, so this also runs faster):
#   - allLayerClusterToTracksterAssociations cannot be dropped entirely: the "byLCs"
#     method used by allTrackstersToSimTrackstersAssociationsByLCs (below) takes its
#     output as an input for both the Trackster side and the SimTrackster side,
#     regardless of what is kept in the output. But its own tracksterCollections is
#     narrowed from the default 6 collections (CLUE3DHigh, TracksterLinks,
#     ticlCandidate, TracksterLinksSuperclusteringDNN, and both ticlSimTracksters
#     variants) down to just "ticlCandidate" and "ticlSimTracksters:fromCPs" (the only
#     two actually needed), cutting its own per-LayerCluster lookup work by 3x. Its
#     two flatteners (flattenLCToCLUE3DTrackster/flattenLCToMergeTrackster) are still
#     dropped, since nothing in the tc-level analysis path reads them.
#   - flattenLCToCP/flattenLCToSC/flattenCPToLC/flattenSCToLC and
#     flattenCLUE3DTracksterToCPSimTrackster are dropped (cheap flattening steps, but
#     still an easy skip since nothing in the tc-level analysis path reads them).
#   - allTrackstersToSimTrackstersAssociationsByLCs.tracksterCollections is narrowed
#     from the default 4 collections (CLUE3DHigh, TracksterLinks, ticlCandidate,
#     TracksterLinksSuperclusteringDNN) down to just "ticlCandidate", cutting this
#     producer's by-LayerCluster overlap computation roughly 4x (it was already
#     narrowed to a single SimTrackster collection, "fromCPs", in the base template).
#   Note: LayerCluster reconstruction, the full iterative TICL chain up to and
#   including ticlCandidate, and ticlSimTracksters itself (which produces the
#   inclusive/fromCPs/PU instances together in one go, so they can't be separated
#   at the producer level) cannot be skipped: ticlCandidate is built from the
#   upstream Trackster stages, and the association producers needed for
#   ticlSimTracksters:fromCPs (layerClusterCaloParticleAssociation,
#   layerClusterSimClusterAssociation, and their own rechit/association inputs)
#   are still required even though their outputs aren't kept.


import FWCore.ParameterSet.Config as cms
from Configuration.Eras.Era_Phase2C26I13M9_cff import Phase2C26I13M9

# initialize process
# note: currently the era is hard-coded; make sure it matches the one used for sample production!
#       otherwise the re-reco might not match the central reco even with the same CLUE parameters.
# todo: find out how to pass the era as an argument, similar to sample production code.
processName = "HGCALTICL"
process = cms.Process(processName, Phase2C26I13M9)

# load basic configs
process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRY_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRYReco_cff")
process.load("RecoTracker.Configuration.RecoTracker_cff")
process.load("RecoLocalCalo.Configuration.hgcalLocalReco_cff")
process.load("RecoHGCal.Configuration.recoHGCAL_cff")

# set global tag
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, "TEMPLATE_GLOBAL_TAG", "")

# set input file(s)
# note: duplicate checking is disabled because independently-produced sample-production
# files are not guaranteed to have globally unique (run, lumiblock, event) numbers
# (e.g. several files can all start at run 1, event 1); without this, PoolSource would
# silently drop all "duplicate"-numbered events beyond the first file.
process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(
        TEMPLATE_INPUT_FILES
    ),
    duplicateCheckMode = cms.untracked.string('noDuplicateCheck')
)
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(int('TEMPLATE_MAX_EVENTS')))

########################
# Run basic HGCAL reco #
########################

# load modules for HGCAL reconstruction
# local reco (RecHits + LayerClusters)
process.load("RecoLocalCalo.Configuration.hgcalLocalReco_cff")
# TICL (Tracksters)
process.load("RecoHGCal.Configuration.recoHGCAL_cff")
# SimTracksters, used as truth targets for Trackster-level associations
process.load("RecoHGCal.TICL.SimTracksters_cff")

# Reuse the HGCAL RecHits stored in the sample-production output. This keeps
# the configurable part of this re-reco step at the LayerCluster/TICL level,
# avoiding the expensive and fixed digi -> uncalibrated rechit -> rechit part.
inputRecHitProcess = "RECO"
process.hgcalLayerClustersEE.recHits = cms.InputTag("HGCalRecHit", "HGCEERecHits", inputRecHitProcess)
process.hgcalLayerClustersHSi.recHits = cms.InputTag("HGCalRecHit", "HGCHEFRecHits", inputRecHitProcess)
process.hgcalLayerClustersHSci.recHits = cms.InputTag("HGCalRecHit", "HGCHEBRecHits", inputRecHitProcess)
if hasattr(process, "hgcalLayerClustersHFNose"):
    process.hgcalLayerClustersHFNose.recHits = cms.InputTag("HGCalRecHit", "HGCHFNoseRecHits", inputRecHitProcess)

# add HGCAL reconstruction to the path to execute
# note: LayerCluster production cannot be skipped even though LayerClusters are not
# kept in the output of this template: the whole TICL chain (up to ticlCandidate) is
# built from them.
process.hgcalLayerClusterTask = cms.Task(
    process.hgcalLayerClustersEE,
    process.hgcalLayerClustersHSi,
    process.hgcalLayerClustersHSci,
    process.hgcalMergeLayerClusters
)
if hasattr(process, "hgcalLayerClustersHFNose"):
    process.hgcalLayerClusterTask.add(process.hgcalLayerClustersHFNose)
process.hgcalLayerClusterSequence = cms.Sequence(process.hgcalLayerClusterTask)
process.iterTICLSequence = cms.Sequence(process.iterTICLTask)
process.hgcal_step = cms.Path(
    process.hgcalLayerClusterSequence
    * process.iterTICLSequence)

################################################
# Calculate and parse sim to reco associatiors #
################################################

# load modules for calculating association scores between objects
# note: LCToTSAssociator_cfi (allLayerClusterToTracksterAssociations) is still needed
# here even though this template doesn't keep or flatten its output directly: the
# "byLCs" method used by allTrackstersToSimTrackstersAssociationsByLCs (below) takes
# it as an input, to look up which LayerClusters belong to which Trackster.
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi');
process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToTSAssociator_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociation_cfi');

# Narrow allLayerClusterToTracksterAssociations down to only the "ticlCandidate" and
# "ticlSimTracksters:fromCPs" collections: by default it computes LC-to-Trackster maps
# for 6 collections (CLUE3DHigh, TracksterLinks, ticlCandidate,
# TracksterLinksSuperclusteringDNN, and both ticlSimTracksters variants); the "byLCs"
# association below needs this producer's output for both the Trackster side
# ("ticlCandidate") and the SimTrackster side ("ticlSimTracksters:fromCPs"), so both
# must be kept, but the other 4 are not needed.
process.allLayerClusterToTracksterAssociations.tracksterCollections = cms.VInputTag(
    cms.InputTag("ticlCandidate"),
    cms.InputTag("ticlSimTracksters", "fromCPs"),
)

# The HGCal LC association score producers default to hardScatterOnly=True.
# That is fine for no-PU validation, but in PU samples it intentionally drops
# all CaloParticles/SimClusters with eventId != 0. Downstream TC association then
# sees many pileup-created TICLCandidates as having zero overlap with any
# CaloParticle. Keep PU truth in the association products; the analysis can
# still select primary-interaction CaloParticles after the full mapping is made.
process.lcAssocByEnergyScoreProducer.hardScatterOnly = cms.bool(False)
process.scAssocByEnergyScoreProducer.hardScatterOnly = cms.bool(False)

# set layer clusters, rechits, and calo particles to use as input for association scores
# note: layerClusterCaloParticleAssociation and layerClusterSimClusterAssociation are
# still required here even though their own outputs are not kept: ticlSimTracksters
# (below) takes them as input to build the CP-derived SimTracksters ("fromCPs").
process.recHitMapProducer.hits = cms.VInputTag(
        cms.InputTag("HGCalRecHit", "HGCEERecHits", inputRecHitProcess),
        cms.InputTag("HGCalRecHit", "HGCHEFRecHits", inputRecHitProcess),
        cms.InputTag("HGCalRecHit", "HGCHEBRecHits", inputRecHitProcess),
)
process.layerClusterCaloParticleAssociation.label_lc = cms.InputTag("hgcalMergeLayerClusters", "", processName)
process.layerClusterCaloParticleAssociation.label_cp = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.layerClusterSimClusterAssociation.label_lcl = cms.InputTag("hgcalMergeLayerClusters", "", processName)
process.layerClusterSimClusterAssociation.label_scl = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.ticlSimTracksters.simclusters = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.ticlSimTracksters.caloparticles = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.ticlSimTracksters.MtdSimTracksters = cms.InputTag("mix", "MergedMtdTruthST", "HLT")
process.ticlSimTracksters.trackingParticles = cms.InputTag("mix", "MergedTrackTruth", "HLT")
process.ticlSimTracksters.layerClusterSimClusterAssociator = cms.InputTag("layerClusterSimClusterAssociation")
process.ticlSimTracksters.layerClusterCaloParticleAssociator = cms.InputTag("layerClusterCaloParticleAssociation")
process.ticlSimTracksters.recoTracks = cms.InputTag("generalTracks", "", "RECO")
process.ticlSimTracksters.tpToTrack = cms.InputTag("trackingParticleRecoTrackAsssociation", "", "RECO")
process.ticlSimTracksters.simTrackToTPMap = cms.InputTag("simHitTPAssocProducer", "simTrackToTP", "RECO")

# Only associate the merged TICLCandidate tracksters to the CP-derived SimTrackster
# collection: neither the pre-merge Trackster stages (CLUE3DHigh/TracksterLinks/...)
# nor the inclusive/PU SimTrackster variants are needed for TICLCandidate<->CaloParticle
# metrics. Narrowing tracksterCollections (in addition to simTracksterCollections,
# already narrowed below) cuts this producer's by-LayerCluster overlap computation
# from 4 Trackster collections down to 1.
# note: the inclusive ticlSimTracksters collection is also not used by the efficiency
# code in this repository, and in CMSSW_17_0_0_pre2 it can contain zero-denominator
# SimTracksters for PU samples with very large EE CLUE2D delta_c values, which trips
# an assertion in the central associator.
process.allTrackstersToSimTrackstersAssociationsByLCs.tracksterCollections = cms.VInputTag(
    cms.InputTag("ticlCandidate")
)
process.allTrackstersToSimTrackstersAssociationsByLCs.simTracksterCollections = cms.VInputTag(
    cms.InputTag("ticlSimTracksters", "fromCPs")
)

# initialize association map flatteners
# note: only the TICLCandidate <-> CP-SimTrackster flattener is defined here; the
# LayerCluster-level ones (flattenLCToCP/flattenLCToSC/flattenCPToLC/flattenSCToLC),
# the LC-to-Trackster ones, and flattenCLUE3DTracksterToCPSimTrackster are not needed
# for TICLCandidate-vs-CaloParticle metrics and are intentionally omitted.
process.flattenMergeTracksterToCPSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlCandidateToticlSimTrackstersfromCPs"),
    dest = cms.string("mergeTracksterCPSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)

# add association scores to the path to execute
process.hgcalAssociatorTask = cms.Task(
    process.ticlSimTrackstersTask,
    process.recHitMapProducer,
    process.lcAssocByEnergyScoreProducer,
    process.scAssocByEnergyScoreProducer,
    process.layerClusterCaloParticleAssociation,
    process.layerClusterSimClusterAssociation,
    process.allLayerClusterToTracksterAssociations,
    process.allTrackstersToSimTrackstersAssociationsByLCs,
    process.flattenMergeTracksterToCPSimTrackster
)
process.hgcal_step.associate(process.hgcalAssociatorTask)

##########################
# Parameter modification #
##########################
TEMPLATE_MOD

#########################
# Define output content #
#########################

# set output
# note: restricted to only what is needed for TICLCandidate-vs-CaloParticle metrics
# (see analysis/efficiency/calculate_associations.py::calculate_tc_event_metrics with
# recalculate=False): CaloParticles, the TICLCandidate/Trackster pair produced by the
# "ticlCandidate" module (Trackster is kept because TICLCandidate::tracksters() holds
# edm::Ptrs into it, even though it is not read directly by name), the CP-derived
# SimTrackster collection, and the flattened TICLCandidate<->CP-SimTrackster
# association. SimClusters, LayerClusters, the pre-merge Trackster stages, pfTICL, and
# the other association products are intentionally dropped; see the module-level
# comments above for why they are safe to drop for this specific use case.
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        "drop *",
        # reco-level output
        f"keep *_ticlCandidate_*_{processName}", # TICLCandidates and their constituent Tracksters.
        f"keep *_ticlSimTracksters_fromCPs_{processName}", # CP-derived truth SimTracksters only.
        # gen-level output
        "keep CaloParticles_mix_MergedCaloTruth_*", # CaloParticles only, not SimClusters/SimClustersRefs.
        # links and associations
        f"keep *_flattenMergeTracksterToCPSimTrackster_*_{processName}",
    )
)

process.outpath = cms.EndPath(process.out)
