# CMSSW config file for HGCAL reconstruction

# Note:
# This config file runs a compact HGCAL/TICL re-reconstruction, including
# LayerClusters, Tracksters, TICL candidates, and the association products
# needed by the analysis scripts in this repository.


import FWCore.ParameterSet.Config as cms
from Configuration.Eras.Era_Phase2C22I13M9_cff import Phase2C22I13M9

# initialize process
# note: currently the era is hard-coded; make sure it matches the one used for sample production!
#       otherwise the re-reco might not match the central reco even with the same CLUE parameters.
# todo: find out how to pass the era as an argument, similar to sample production code.
processName = "HGCALTICL"
process = cms.Process(processName, Phase2C22I13M9)

# load basic configs
process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRY_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRYReco_cff")
process.load("RecoTracker.Configuration.RecoTracker_cff")
process.load("RecoLocalCalo.Configuration.hgcalLocalReco_cff")
process.load("RecoHGCal.Configuration.recoHGCAL_cff")
process.load("RecoHGCal.TICL.tracksterSelectionTf_cfi")

# The v4 TrackstersMergeProducer runs a TensorFlow model for the merged
# Trackster energy regression / particle ID. The ESProducer loaded above
# provides the graph payload labelled "tracksterSelectionTf", but CMSSW also
# needs an ESSource to define a valid IOV for TfGraphRecord. This mirrors the
# official TICL-from-RECO customisation and avoids a NoRecord exception when
# ticlTrackstersMerge asks the EventSetup for the graph.
from RecoTracker.IterativeTracking.iterativeTk_cff import trackdnn_source
process.trackdnn_source = trackdnn_source
process.TFESSource = cms.Task(process.trackdnn_source)

# set global tag
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, "TEMPLATE_GLOBAL_TAG", "")

# set input file
process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(
        'file:TEMPLATE_INPUT_FILE'
    )
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

# define digis to use as input for clustering
# note: syntax is a little unclear; apparently the name RECO should not be declared explicitly;
#       instead CMSSW looks for the collections under all available processes (e.g. RECO, HLT, etc)
#       and exposes them to the current process.
process.hgcalDigis = cms.EDAlias(
    hgcalDigis = cms.VPSet(
        cms.PSet(
            type = cms.string("HGCalDigiCollection"),
            fromProductInstance = cms.string("EE"),
            toProductInstance = cms.string("EE")
        ),
        cms.PSet(
            type = cms.string("HGCalDigiCollection"),
            fromProductInstance = cms.string("HEfront"),
            toProductInstance = cms.string("HEfront")
        ),
        cms.PSet(
            type = cms.string("HGCalDigiCollection"),
            fromProductInstance = cms.string("HEback"),
            toProductInstance = cms.string("HEback")
        )
    )
)

# add HGCAL reconstruction to the path to execute
process.iterTICLSequence = cms.Sequence(process.iterTICLTask)
process.hgcal_step = cms.Path(
    process.hgcalLocalRecoSequence
    * process.iterTICLSequence)
process.hgcal_step.associate(process.TFESSource)

################################################
# Calculate and parse sim to reco associatiors #
################################################

# load modules for calculating association scores between objects
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi');
process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToTSAssociator_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociation_cfi');

# set layer clusters and calo particles to use as input for association scores
# note: needs to be set to those from the current process,
#       otherwise it seems by default the ones from the RECO process
#       (already present in the input files) might be used (?)
process.recHitMapProducer.hits = cms.VInputTag(
        cms.InputTag("HGCalRecHit", "HGCEERecHits", processName),
        cms.InputTag("HGCalRecHit", "HGCHEFRecHits", processName),
        cms.InputTag("HGCalRecHit", "HGCHEBRecHits", processName),
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
    src = cms.InputTag("allLayerClusterToTracksterAssociations", "ticlTrackstersMerge"),
    dest = cms.string("layerClusterMergeTracksterAssociationFlat"),
    second = cms.string("TS")
)
process.flattenCLUE3DTracksterToSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlTrackstersCLUE3DHighToticlSimTracksters"),
    dest = cms.string("clue3DTracksterSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)
process.flattenSimTracksterToCLUE3DTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlSimTrackstersToticlTrackstersCLUE3DHigh"),
    dest = cms.string("simTracksterCLUE3DTracksterAssociationFlat"),
    first = cms.string("SimTS"),
    second = cms.string("TS")
)
process.flattenMergeTracksterToSimTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlTrackstersMergeToticlSimTracksters"),
    dest = cms.string("mergeTracksterSimTracksterAssociationFlat"),
    first = cms.string("TS"),
    second = cms.string("SimTS")
)
process.flattenSimTracksterToMergeTrackster = cms.EDProducer(
    "FlattenTSToTSAssociator",
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlSimTrackstersToticlTrackstersMerge"),
    dest = cms.string("simTracksterMergeTracksterAssociationFlat"),
    first = cms.string("SimTS"),
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
    src = cms.InputTag("allTrackstersToSimTrackstersAssociationsByLCs", "ticlTrackstersMergeToticlSimTrackstersfromCPs"),
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
    process.flattenLCToCP,
    process.flattenLCToSC,
    process.flattenCPToLC,
    process.flattenSCToLC,
    process.flattenLCToCLUE3DTrackster,
    process.flattenLCToMergeTrackster,
    process.flattenCLUE3DTracksterToSimTrackster,
    process.flattenSimTracksterToCLUE3DTrackster,
    process.flattenMergeTracksterToSimTrackster,
    process.flattenSimTracksterToMergeTrackster,
    process.flattenCLUE3DTracksterToCPSimTrackster,
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
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        "drop *",
        # reco-level output
        "keep *_HGCalRecHit_*_*",
        "keep *_hgcalMergeLayerClusters_*_*",
        "keep *_ticlTracksters*_*_*", # includes Tracksters and ticlCandidates in v4.
        "keep *_ticlCandidate_*_*", # in v5, ticlCandidates have been moved to a separate module.
        "keep *_pfTICL_*_*", # full PF candidate collection from TICL.
        "keep *_ticlSimTracksters*_*_*",
        "keep *_trackingParticleRecoTrackAsssociation_*_*",
        "keep *_simHitTPAssocProducer_simTrackToTP_*",
        # gen-level output
        "keep *_mix_MergedCaloTruth_*",
        "keep *_mix_MergedTrackTruth_*",
        "keep *_g4SimHits_HGCHitsEE_*",
        "keep *_g4SimHits_HGCHitsHEfront_*",
        "keep *_g4SimHits_HGCHitsHEback_*",
        # links and associations
        "keep *_flatten*_*_*",
    )
)

process.outpath = cms.EndPath(process.out)
