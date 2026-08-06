import FWCore.ParameterSet.Config as cms

# Note:
# AddAntiParticle is intentionally False here. FlatRandomPtGunProducer's
# AddAntiParticle=True pairs each particle with its antiparticle at the
# momentum-reversed direction (-px, -py, -pz), i.e. the opposite eta and phi.
# With a forward-only eta window (as used here), that would send all
# particles of one charge to the forward endcap and all of the opposite
# charge to the backward endcap, rather than mixing charges within the
# same region. Instead, both charges are listed explicitly in PartID so
# each of the 200 particles gets its own independently random pt/eta/phi
# within the same kinematic window.
generator = cms.EDProducer("FlatRandomPtGunProducer",
    PGunParameters = cms.PSet(
        PartID = cms.vint32(*([-211, 211] * 100)),
        MinPt = cms.double(2.0),
        MaxPt = cms.double(200.0),
        MinEta = cms.double(1.5),
        MaxEta = cms.double(3.0),
        MinPhi = cms.double(-3.1416),
        MaxPhi = cms.double(3.1416),
    ),
    Verbosity = cms.untracked.int32(0),
    psethack = cms.string('multi pion Pt2to200, 100x pi- + 100x pi+'),
    AddAntiParticle = cms.bool(False),
    firstRun = cms.untracked.uint32(1)
)
