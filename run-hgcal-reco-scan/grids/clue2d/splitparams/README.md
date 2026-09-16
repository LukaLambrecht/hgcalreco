# Grid definitions for CMSSW versions with finer parameter splitting

So far, only custom CMSSW branch (?) by Wahid.
(https://github.com/waredjeb/cmssw/tree/splitCLUEParameters\_CMSSW\_20\_0\_0\_pre1)

The parameters are:
- deltac (= cut-off distance for local density calculation = d\_c in the CLUE paper)
- deltas (= seed distance = delta\_c)
- deltao (= outlier distance = delta\_o)
- kappa (= seed or outlier density = rho\_c)
- ecut (= minimum energy threshold)

Syntax:
- kappa and ecut are scalars
- delta's are vectors of lenght four, with the following order:
    - CE-E low density
    - CE-E high density
    - CE-H low density
    - CE-H high density or scintillator (depending on which producer)

Modules and default values (as obtained from edmConfigDump):
- EE, HFNose, and HSi:
```
process.hgcalLayerClustersEE = cms.EDProducer("HGCalLayerClusterProducer",
    calculatePositionInAlgo = cms.bool(True),
    detector = cms.string('EE'),
    mightGet = cms.optional.untracked.vstring,
    nHitsTime = cms.uint32(3),
    plugin = cms.PSet(
        deltac = cms.vdouble(1.3, 1.3, 1.3, 1.3),
        deltao = cms.vdouble(2.6, 2.6, 2.6, 2.6),
        deltas = cms.vdouble(1.3, 1.3, 1.3, 1.3),
        ecut = cms.double(3),
        kappa = cms.double(9),
```
- HSci:
```
process.hgcalLayerClustersHSci = cms.EDProducer("HGCalLayerClusterProducer",
    calculatePositionInAlgo = cms.bool(True),
    detector = cms.string('BH'),
    mightGet = cms.optional.untracked.vstring,
    nHitsTime = cms.uint32(3),
    plugin = cms.PSet(
        deltac = cms.vdouble(0.0315, 0.0315, 0.0315, 0.0315),
        deltao = cms.vdouble(0.063, 0.063, 0.063, 0.063),
        deltas = cms.vdouble(0.0315, 0.0315, 0.0315, 0.0315),
        ecut = cms.double(3),
        kappa = cms.double(9),
```

Note: EE only ever reads the first two values of each of these vectors,
HSi only the last two, and HSci only the last one.
