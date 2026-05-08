import FWCore.ParameterSet.Config as cms

process = cms.Process("TEST")

process.load("FWCore.MessageService.MessageLogger_cfi")

process.source = cms.Source(
    "PoolSource",
    fileNames = cms.untracked.vstring("file:input.root")
)

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(10))

process.test = cms.EDAnalyzer("HGCalAssocTestAnalyzer")

process.p = cms.Path(process.test)
