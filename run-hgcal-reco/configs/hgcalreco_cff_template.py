# CMSSW config file for HGCAL reconstruction

# Note: this config file only runs the "minimal-effort" HGCAL-only reconstruction.
# It fails at the final stage (ticlTracksterMergeTask), where some non-HGCAL inputs are needed.
# This task is therefore removed from the sequence, and the output file will contain
# "ticlTrackstersCLUE3DHigh" but not "ticlTrackstersMerge".


import FWCore.ParameterSet.Config as cms

# initialize process
process = cms.Process("HGCALTICL")

# load basic configs
process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRY_cff")
process.load("Configuration.Geometry.TEMPLATE_GEOMETRYReco_cff")
process.load("RecoTracker.Configuration.RecoTracker_cff")

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
process.mergeTICLTask.remove(process.ticlTracksterMergeTask) # requires non-HGCAL reco inputs

################################################
# Calculate and parse sim to reco associatiors #
################################################

# load modules for calculating association scores between objects
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi');
process.load('SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi');
process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi');

# set layer clusters and calo particles to use as input for association scores
# note: needs to be set to those from the current process,
#       otherwise it seems by default the ones from the RECO process
#       (already present in the input files) might be used (?)
process.recHitMapProducer.hits = cms.VInputTag(
        cms.InputTag("HGCalRecHit", "HGCEERecHits", "HGCALTICL"),
        cms.InputTag("HGCalRecHit", "HGCHEFRecHits", "HGCALTICL"),
        cms.InputTag("HGCalRecHit", "HGCHEBRecHits", "HGCALTICL"),
)
process.layerClusterCaloParticleAssociation.label_lc = cms.InputTag("hgcalMergeLayerClusters", "", "HGCALTICL")
process.layerClusterCaloParticleAssociation.label_cp = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.layerClusterSimClusterAssociation.label_lcl = cms.InputTag("hgcalMergeLayerClusters", "", "HGCALTICL")
process.layerClusterSimClusterAssociation.label_scl = cms.InputTag("mix", "MergedCaloTruth", "HLT")
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

# add association scores to the path to execute
process.hgcalAssociatorTask = cms.Task(
    process.recHitMapProducer,
    process.lcAssocByEnergyScoreProducer,
    process.scAssocByEnergyScoreProducer,
    process.layerClusterCaloParticleAssociation,
    process.layerClusterSimClusterAssociation,
    process.flattenLCToCP,
    process.flattenLCToSC
)
process.hgcal_step.associate(process.hgcalAssociatorTask)

#########################
# Define output content #
#########################

# set output
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        # reco-level output
        "keep *_HGCalRecHit_*_*",
        "keep *_hgcalMergeLayerClusters_*_*",
        "keep *_ticlTracksters*_*_*",
        # gen-level output
        "keep *GenParticle*_*_*_*",
        "keep *TrackingParticle*_*_*_*",
        "keep *TrackingVertex*_*_*_*",
        "keep *SimTrack*_*_*_*",
        "keep *CaloParticle*_*_*_*",
        "keep *SimCluster*_*_*_*",
        "keep *CaloHit*_*_*_*",
        # links and associations
        "keep *_layerClusterCaloParticleAssociation_*_*",
        "keep *_layerClusterSimClusterAssociation_*_*",
        "keep *_*_layerClusterCaloParticleAssociationFlat*_*",
        "keep *_*_layerClusterSimClusterAssociationFlat*_*",
    )
)

process.outpath = cms.EndPath(process.out)
