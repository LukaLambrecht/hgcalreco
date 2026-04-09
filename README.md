# Run and tune HGCAL reconstruction for hadronic showers


### How to modify clustering parameters in HGCAL reconstruction?

The safest option seems to be to modify the cmsRun configuration fragment (`_cff.py`).
This overwrites any default values and other silent modifications (e.g. era modifiers) that might be present.
For example, one can add a line like the following to a default cmsRun configuration fragment:
```
process.ticlTrackstersCLUE3DHigh.pluginPatternRecognitionByCLUE3D.criticalDensity = cms.double(0.0)
```

How to figure out which parameter names are available and what their default value is?
For this, one can dump the full config using `edmConfigDump`.
This lists all the configurable parameters with their value.

Notes:
- Need to figure out if it matters where in the config fragment these lines are added.
Probably it doesn't matter exactly as long as they are low enough
(i.e. after any other modifications that might be happening),
but before the output definition.


### Which parameters to modify / scan?

Print all available parameters with `edmConfigDump` on a default cmsRun configuration fragment.
This gives the following (for `CMSSW_16_0_5`, to update when needed):
```
process.ticlTrackstersCLUE3DHigh = cms.EDProducer("TrackstersProducer",
    [...]
    pluginPatternRecognitionByCLUE3D = cms.PSet(
        algo_verbosity = cms.int32(0),
        computeLocalTime = cms.bool(False),
        criticalDensity = cms.vdouble(0.6, 0.6, 0.6),
        criticalEtaPhiDistance = cms.vdouble(0.025, 0.025, 0.025),
        criticalSelfDensity = cms.vdouble(0.15, 0.15, 0.15),
        criticalXYDistance = cms.vdouble(1.8, 1.8, 1.8),
        criticalZDistanceLyr = cms.vint32(5, 5, 5),
        cutHadProb = cms.double(999),
        densityEtaPhiDistanceSqr = cms.vdouble(0.0008, 0.0008, 0.0008),
        densityOnSameLayer = cms.bool(False),
        densitySiblingLayers = cms.vint32(3, 3, 3),
        densityXYDistanceSqr = cms.vdouble(3.24, 3.24, 3.24),
        doPidCut = cms.bool(True),
        kernelDensityFactor = cms.vdouble(0.2, 0.2, 0.2),
        minNumLayerCluster = cms.vint32(2, 2, 2),
        nearestHigherOnSameLayer = cms.bool(False),
        outlierMultiplier = cms.vdouble(2, 2, 2),
        rescaleDensityByZ = cms.bool(False),
        type = cms.string('CLUE3D'),
        useAbsoluteProjectiveScale = cms.bool(True),
        useClusterDimensionXY = cms.bool(False),
        usePCACleaning = cms.bool(False)
    ),
    [...]
)
```

Note, many other modules also have a similar `pluginPatternRecognitionByCLUE3D`, e.g.:
```
process.ticlTrackstersCLUE3DEM
process.ticlTrackstersCLUE3DHAD
process.ticlTrackstersCLUE3DHigh
process.ticlTrackstersEM
process.ticlTrackstersFastJet
process.ticlTrackstersHAD
process.ticlTrackstersHFNoseEM
process.ticlTrackstersHFNoseHAD
process.ticlTrackstersHFNoseMIP
process.ticlTrackstersHFNoseTrk
process.ticlTrackstersHFNoseTrkEM
process.ticlTrackstersMIP
process.ticlTrackstersRecovery
process.ticlTrackstersTrk
process.ticlTrackstersTrkEM
```
These are different implementations / configurations of the TICL algorithm that have been defined over time.
Note: this part of the config does not tell you which one of those are actually run!
It looks like only CLUE3DHigh is enabled in normal reconstruction, so we can probably ignore the rest.
Note: there is also a `process.ticlTrackstersMerge`, but it does not contain the same parameters.
Probably this is a later merging step.

The meaning of the parameters: to check with experts.

All of the above seems to be for the trackster reconstruction only, not the layer clusters.
For layer clusters, dump the config in the same way, but look for another section that looks like this:
```
process.hgcalLayerClustersHSi = cms.EDProducer("HGCalLayerClusterProducer",
    calculatePositionInAlgo = cms.bool(True),
    detector = cms.string('FH'),
    mightGet = cms.optional.untracked.vstring,
    nHitsTime = cms.uint32(3),
    plugin = cms.PSet(
        [...]
        deltac = cms.vdouble(1.3, 1.3, 1.3, 0.0315),
        deltasi_index_regemfac = cms.int32(3),
        dependSensor = cms.bool(True),
        ecut = cms.double(3),
        [...]
        kappa = cms.double(9),
        [...]
    ),
    recHits = cms.InputTag("HGCalRecHit","HGCHEFRecHits"),
    timeClname = cms.string('timeLayerCluster')
)
```
Or for HSci instead of HSi:
```
process.hgcalLayerClustersHSci = cms.EDProducer("HGCalLayerClusterProducer",
    calculatePositionInAlgo = cms.bool(True),
    detector = cms.string('BH'),
    mightGet = cms.optional.untracked.vstring,
    nHitsTime = cms.uint32(3),
    plugin = cms.PSet(
        [...]
        deltac = cms.vdouble(1.3, 1.3, 1.3, 0.0315),
        deltasi_index_regemfac = cms.int32(3),
        dependSensor = cms.bool(True),
        ecut = cms.double(3),
        [...]
        kappa = cms.double(9),
        [...]
    ),
    recHits = cms.InputTag("HGCalRecHit","HGCHEBRecHits"),
    timeClname = cms.string('timeLayerCluster')
)
```
Where the parameters mean (to be checked!):
- ecut: Minimum energy for a RecHit to be considered.
- kappa: Density threshold for identifying seed hits.
- deltac: Clustering radius. The different values are for thin, medium and thick silicon sensors (in cm) and for scintillator tiles (in eta-phi).


### How to make event display

Just run `cmsShow -i <output file from reconstruction>`.

Notes:
- Takes a while to load...
- Requires a CMSSW version to have been sourced with `cmsenv`.
- Requires an lxplus connection with screen forwarding, using the `-X` option in `ssh`.

### Other tips and tricks

Run `edmDumpEventContent.py <input file>` to see file contents.
Use the same followed by `| grep <search term>` to filter.
