# CMSSW config file for HGCAL reconstruction

# Note:
# This config file runs a compact HGCAL/TICL re-reconstruction, including
# LayerClusters, Tracksters, TICL candidates, and the association products
# needed by the analysis scripts in this repository.


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
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi');
process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToTSAssociator_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociation_cfi');

# The HGCal LC association score producers default to hardScatterOnly=True.
# That is fine for no-PU validation, but in PU samples it intentionally drops
# all CaloParticles/SimClusters with eventId != 0. Downstream TC association then
# sees many pileup-created TICLCandidates as having zero overlap with any
# CaloParticle. Keep PU truth in the association products; the analysis can
# still select primary-interaction CaloParticles after the full mapping is made.
process.lcAssocByEnergyScoreProducer.hardScatterOnly = cms.bool(False)
process.scAssocByEnergyScoreProducer.hardScatterOnly = cms.bool(False)

# set layer clusters, rechits, and calo particles to use as input for association scores
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

# Build Trackster-to-SimTrackster association maps for both the CP-derived
# ("fromCPs") and the SimCluster-derived (inclusive, unlabeled instance)
# SimTrackster collections, so TICLCandidate-level metrics can be computed
# against either truth object (see calculate_associations.py --gen_level).
# Caution: in CMSSW_17_0_0_pre2 the inclusive collection could contain
# zero-denominator SimTracksters for PU samples with very large EE CLUE2D
# delta_c values, which tripped an assertion in the central associator; this
# has not reappeared in CMSSW_20_0_0_pre1 testing so far, but has not been
# stress-tested against PU200 samples either - watch for this if it recurs.
process.allTrackstersToSimTrackstersAssociationsByLCs.simTracksterCollections = cms.VInputTag(
    cms.InputTag("ticlSimTracksters", "fromCPs"),
    cms.InputTag("ticlSimTracksters"),
)

# initialize association map flatteners
process.flattenLCToCP = cms.EDProducer(
    "FlattenLCToCPAssociator",
    src = cms.InputTag("layerClusterCaloParticleAssociation"),
    dest = cms.string("layerClusterCaloParticleAssociationFlat")
)
process.flattenLCToSC = cms.EDProducer(
    "FlattenLCToSCAssociator",
    src = cms.InputTag("layerClusterSimClusterAssociation"),
    dest = cms.string("layerClusterSimClusterAssociationFlat")
)
process.flattenCPToLC = cms.EDProducer(
    "FlattenCPToLCAssociator",
    src = cms.InputTag("layerClusterCaloParticleAssociation"),
    dest = cms.string("caloParticleLayerClusterAssociationFlat")
)
process.flattenSCToLC = cms.EDProducer(
    "FlattenSCToLCAssociator",
    src = cms.InputTag("layerClusterSimClusterAssociation"),
    dest = cms.string("simClusterLayerClusterAssociationFlat")
)
process.flattenLCToCLUE3DTrackster = cms.EDProducer(
    "FlattenLCToTSAssociator",
    src = cms.InputTag("allLayerClusterToTracksterAssociations", "ticlTrackstersCLUE3DHigh"),
    dest = cms.string("layerClusterCLUE3DTracksterAssociationFlat"),
    second = cms.string("TS")
)
process.flattenLCToMergeTrackster = cms.EDProducer(
    "FlattenLCToTSAssociator",
    src = cms.InputTag("allLayerClusterToTracksterAssociations", "ticlCandidate"),
    dest = cms.string("layerClusterMergeTracksterAssociationFlat"),
    second = cms.string("TS")
)
process.flattenCLUE3DTracksterToCPSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlTrackstersCLUE3DHighToticlSimTrackstersfromCPs"),
    dest = cms.string("clue3DTracksterCPSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)
process.flattenMergeTracksterToCPSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlCandidateToticlSimTrackstersfromCPs"),
    dest = cms.string("mergeTracksterCPSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)
# SimCluster-derived (inclusive ticlSimTracksters instance) equivalents of the two
# associations above. The instance name has no "fromCPs" suffix since the
# InputTag instance is empty for the inclusive SimTrackster collection.
process.flattenCLUE3DTracksterToSCSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlTrackstersCLUE3DHighToticlSimTracksters"),
    dest = cms.string("clue3DTracksterSCSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)
process.flattenMergeTracksterToSCSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlCandidateToticlSimTracksters"),
    dest = cms.string("mergeTracksterSCSimTracksterAssociationFlat"),
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
    process.flattenLCToCP,
    process.flattenLCToSC,
    process.flattenCPToLC,
    process.flattenSCToLC,
    process.flattenLCToCLUE3DTrackster,
    process.flattenLCToMergeTrackster,
    process.flattenCLUE3DTracksterToCPSimTrackster,
    process.flattenMergeTracksterToCPSimTrackster,
    process.flattenCLUE3DTracksterToSCSimTrackster,
    process.flattenMergeTracksterToSCSimTrackster
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
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        "drop *",
        # reco-level output
        #"keep *_HGCalRecHit_*_*", # drop individual hits (no need to recalculate scores)
        "keep *_hgcalMergeLayerClusters_*_*",
        "keep *_ticlTracksters*_*_*", # includes Tracksters and ticlCandidates in v4.
        "keep *_ticlTracksterLinks*_*_*", # linked Tracksters in TICLv5.
        "keep *_ticlCandidate_*_*", # in v5, ticlCandidates have been moved to a separate module.
        "keep *_pfTICL_*_*", # full PF candidate collection from TICL.
        "keep *_ticlSimTracksters*_*_*",
        # gen-level output
        "keep *_mix_MergedCaloTruth_*",
        #"keep *_g4SimHits_HGCHitsEE_*", # drop individual hits (no need to recalculate scores)
        #"keep *_g4SimHits_HGCHitsHEfront_*", # drop individual hits (no need to recalculate scores)
        #"keep *_g4SimHits_HGCHitsHEback_*", # drop individual hits (no need to recalculate scores)
        # MC-truth graph (PhysicsTools/TruthInfo, cms-sw/cmssw PR #51213), only
        # present if the input was produced with sample-production's
        # --output-mode truth; harmless no-op "keep" otherwise. Not produced
        # by this re-reco process, so process is wildcarded like MergedCaloTruth.
        "keep *_truthGraphProducer_*_*",
        "keep *_truthLogicalGraphProducer_*_*",
        "keep *_truthLogicalGraphHitIndexProducer_*_*",
        # links and associations
        "keep *_flatten*_*_*",
    )
)

process.outpath = cms.EndPath(process.out)
