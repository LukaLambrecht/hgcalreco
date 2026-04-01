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
This gives the following (for `CMSSW_14_0_9`, to update later):
```
process.ticlTrackstersHAD = cms.EDProducer("TrackstersProducer",
    [...]
    pluginPatternRecognitionByCLUE3D = cms.PSet(
        algo_verbosity = cms.int32(0),pluginPatternRecognitionByCLUE3D
        criticalDensity = cms.double(4),
        criticalEtaPhiDistance = cms.double(0.025),
        criticalSelfDensity = cms.double(0.15),
        criticalXYDistance = cms.double(1.8),
        criticalZDistanceLyr = cms.int32(5),
        densityEtaPhiDistanceSqr = cms.double(0.0008),
        densityOnSameLayer = cms.bool(False),
        densitySiblingLayers = cms.int32(3),
        densityXYDistanceSqr = cms.double(3.24),
        eid_input_name = cms.string('input'),
        eid_min_cluster_energy = cms.double(1),
        eid_n_clusters = cms.int32(10),
        eid_n_layers = cms.int32(50),
        eid_output_name_energy = cms.string('output/regressed_energy'),
        eid_output_name_id = cms.string('output/id_probabilities'),
        kernelDensityFactor = cms.double(0.2),
        minNumLayerCluster = cms.int32(2),
        nearestHigherOnSameLayer = cms.bool(False),
        outlierMultiplier = cms.double(2),
        rescaleDensityByZ = cms.bool(False),
        type = cms.string('CLUE3D'),
        useAbsoluteProjectiveScale = cms.bool(True),
        useClusterDimensionXY = cms.bool(False)
    ),
```

Note, many other modules also have a similar `pluginPatternRecognitionByCLUE3D`, e.g.:
```
process.ticlTrackstersCLUE3DHigh
process.ticlTrackstersCLUE3DLow
process.ticlTrackstersEM
process.ticlTrackstersFastJet
process.ticlTrackstersHFNoseEM
process.ticlTrackstersHFNoseHAD
process.ticlTrackstersHFNoseMIP
process.ticlTrackstersHFNoseTrk
process.ticlTrackstersHFNoseTrkEM
process.ticlTrackstersMIP
process.ticlTrackstersTrk
process.ticlTrackstersTrkEM
```
Presumably these correspond to different sequential iterations of the TICL algorithm (to be confirmed),
and also presumably `process.ticlTrackstersHAD` is the most relevant one for now (to be confirmed).

The meaning of the parameters: to check with experts.


### How to make event display

Just run `cmsShow -i <output file from reconstruction>`.

Notes:
- Takes a while to load...
- Requires a CMSSW version to have been sourced with `cmsenv`.
- Requires an lxplus connection with screen forwarding, using the `-X` option in `ssh`.

### Other tips and tricks

Run `edmDumpEventContent.py <input file>` to see file contents.
Use the same followed by `| grep <search term>` to filter.
