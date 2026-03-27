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

# HGCAL reconstruction
# raw to digi
process.load("EventFilter.HGCalRawToDigi/HGCalRawToDigi_cfi")
# local reco (RecHits + LayerClusters)
process.load("RecoLocalCalo.Configuration.hgcalLocalReco_cff")
# TICL (Tracksters)
process.load("RecoHGCal.Configuration.recoHGCAL_cff")

process.HGCalUncalibRecHit.HGCEEConfig.digiSource  = cms.InputTag("hgcalDigis","EE","HLT")
process.HGCalUncalibRecHit.HGCHEFConfig.digiSource = cms.InputTag("hgcalDigis","HEfront","HLT")
process.HGCalUncalibRecHit.HGCHEBConfig.digiSource = cms.InputTag("hgcalDigis","HEback","HLT")

process.iterTICLSequence = cms.Sequence(process.iterTICLTask)
process.hgcal_step = cms.Path(
    process.hgcalDigis
    * process.hgcalLocalRecoSequence
    * process.iterTICLSequence)
process.mergeTICLTask.remove(process.ticlTracksterMergeTask) # requires non-HGCAL reco inputs

# parameter modifications
#process.ticlTrackstersCLUE3DHigh.pluginPatternRecognitionByCLUE3D.criticalDensity = cms.double(0.3)
#process.ticlTrackstersCLUE3DLow.pluginPatternRecognitionByCLUE3D.criticalDensity = cms.double(1.0)

# set output
process.out = cms.OutputModule("PoolOutputModule",
    fileName = cms.untracked.string("hgcalreco_out.root"),
    outputCommands = cms.untracked.vstring(
        # reco output
        "keep *_HGCalRecHit_*_*",
        "keep *_hgcalMergeLayerClusters_*_*",
        "keep *_ticlTracksters*_*_*",
        # gen output
        "keep *GenParticle*_*_*_*",
        "keep *TrackingParticle*_*_*_*",
        "keep *TrackingVertex*_*_*_*",
        "keep *SimTrack*_*_*_*",
        "keep *CaloParticle*_*_*_*",
        "keep *SimCluster*_*_*_*",
        "keep *CaloHit*_*_*_*"
    )
)

process.outpath = cms.EndPath(process.out)
