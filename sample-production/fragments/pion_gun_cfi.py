import FWCore.ParameterSet.Config as cms

generator = cms.EDProducer("FlatRandomPtGunProducer",
    PGunParameters = cms.PSet(
        PartID = cms.vint32(-211),
        MinPt = cms.double(2.0),
        MaxPt = cms.double(200.0),
        MinEta = cms.double(1.5),
        MaxEta = cms.double(3.0),
        MinPhi = cms.double(-3.1416),
        MaxPhi = cms.double(3.1416),
    ),
    Verbosity = cms.untracked.int32(0),
    psethack = cms.string('single pion Pt2to200'),
    AddAntiParticle = cms.bool(True),
    firstRun = cms.untracked.uint32(1)
)
