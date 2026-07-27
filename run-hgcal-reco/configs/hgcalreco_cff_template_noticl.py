# CMSSW config file for HGCAL reconstruction

# Note: this config file only runs the "minimal-effort" HGCAL-only reconstruction.
# It avoids the final TICLv5 linking/candidate/PF tasks, where some non-HGCAL inputs are needed.
# The output file will contain "ticlTrackstersCLUE3DHigh", but not the linked TICLv5 products.


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
process.iterTICLSequence = cms.Sequence(
    cms.Task(
        process.ticlLayerTileTask,
        process.ticlCLUE3DHighStepTask
    )
)
process.hgcal_step = cms.Path(
    process.hgcalLocalRecoSequence
    * process.iterTICLSequence)

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
        cms.InputTag("HGCalRecHit", "HGCEERecHits", processName),
        cms.InputTag("HGCalRecHit", "HGCHEFRecHits", processName),
        cms.InputTag("HGCalRecHit", "HGCHEBRecHits", processName),
)
process.layerClusterCaloParticleAssociation.label_lc = cms.InputTag("hgcalMergeLayerClusters", "", processName)
process.layerClusterCaloParticleAssociation.label_cp = cms.InputTag("mix", "MergedCaloTruth", "HLT")
process.layerClusterSimClusterAssociation.label_lcl = cms.InputTag("hgcalMergeLayerClusters", "", processName)
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

# add association scores to the path to execute
process.hgcalAssociatorTask = cms.Task(
    process.recHitMapProducer,
    process.lcAssocByEnergyScoreProducer,
    process.scAssocByEnergyScoreProducer,
    process.layerClusterCaloParticleAssociation,
    process.layerClusterSimClusterAssociation,
    process.flattenLCToCP,
    process.flattenLCToSC,
    process.flattenCPToLC,
    process.flattenSCToLC
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
        # reco-level output
        "keep *_HGCalRecHit_*_*",
        "keep *_hgcalMergeLayerClusters_*_*",
        "keep *_ticlTracksters*_*_*",
        # gen-level output
        "keep *CaloParticle*_mix_MergedCaloTruth_*",
        "keep *SimCluster*_mix_MergedCaloTruth_*",
        "keep *CaloHit*_*_*_*",
        # links and associations
        "keep *_*_layerClusterCaloParticleAssociationFlat*_*",
        "keep *_*_layerClusterSimClusterAssociationFlat*_*",
        "keep *_*_caloParticleLayerClusterAssociationFlat*_*",
        "keep *_*_simClusterLayerClusterAssociationFlat*_*",
    )
)

process.outpath = cms.EndPath(process.out)
