# CMSSW config file for HGCAL reconstruction

# Note: this config file only runs the "minimal-effort" HGCAL-only reconstruction.
# It fails at the final stage (ticlTracksterMergeTask), where some non-HGCAL inputs are needed.
# This task is therefore removed from the sequence, and the output file will contain
# "ticlTrackstersCLUE3DHigh" but not "ticlTrackstersMerge".


import FWCore.ParameterSet.Config as cms

# initialize process
processName = "HGCALTICL"
process = cms.Process(processName)

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

# HGCAL reconstruction
# local reco (RecHits + LayerClusters)
process.load("RecoLocalCalo.Configuration.hgcalLocalReco_cff")
# TICL (Tracksters)
process.load("RecoHGCal.Configuration.recoHGCAL_cff")

# define digis to use
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

process.iterTICLSequence = cms.Sequence(process.iterTICLTask)
process.hgcal_step = cms.Path(
    process.hgcalLocalRecoSequence
    * process.iterTICLSequence)
process.mergeTICLTask.remove(process.ticlTracksterMergeTask) # requires non-HGCAL reco inputs

# parameter modification
TEMPLATE_MOD

# set output
# note: only store output products that might be of any use for calculating efficiency,
#       for maximal file size efficiency and faster downstream steps.
#       to be finetuned later.
# note: also only store the version resulting from this reconstruction,
#       and not the "HLT" or "RECO" versions resulting from the default reconstruction chain.
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        # reco output
        f"keep *_HGCalRecHit_*_{processName}",
        f"keep *_hgcalMergeLayerClusters_*_{processName}",
        f"keep *_ticlTracksters*_*_{processName}",
        # gen output
        f"keep *CaloParticle*_*_*_*",
        f"keep *SimCluster*_*_*_*",
        f"keep *CaloHit*_*_*_*"
    )
)

process.outpath = cms.EndPath(process.out)
