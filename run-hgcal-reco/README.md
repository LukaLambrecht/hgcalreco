# Run minimal HGCAL reco

Note: still to figure out which combinations of CMSSW versions, arguments, and input files are working...

For current version (10 March 2026):
- Input files: produced with CMSSW `14_0_X` (e.g. this dataset: `SinglePion_PT2to200/Phase2Spring24DIGIRECOMiniAOD-noPU_Trk1GeV_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD`)
- CMSSW version: run everything in CMSSW `14_0_9` for consistency.
- Geometry: can get it from DAS, click `Configs` and scan the cmsRun config. For this dataset, it is `GeometryExtended2026D110` and/or `GeometryExtended2026D110Reco` (not yet clear what the difference is).
- Global tag: can get it in the same way as the geometry. For this dataset, it is `140X_mcRun4_realistic_v4`.

Status: runs and produces some nonzero output!
But does not seem to correspond 100% with the already existing "HLT" process outputs. To check.


### How to make event display

Just run `cmsShow -i <output file from reconstruction>`.

Notes:
- Takes a while to load...
- Requires a CMSSW version to have been sourced with `cmsenv`.
- Requires an lxplus connection with screen forwarding, using the `-X` option in `ssh`.


### How to modify clustering parameters

The safest option seems to be to modify the configuration fragment (`_cff.py`).
This overwrites any default values and other silent modifications (e.g. era modifiers) that might be present.
For example, one can add a line like `process.ticlTrackstersCLUE3DHigh.pluginPatternRecognitionByCLUE3D.criticalDensity = cms.double(0.0)` to the template config fragment.

How to figure out which parameter names are available and what their default value is?
For this, one can dump the full config using `edmConfigDump` (or the utility script in this folder).
This lists all the configurable parameters with their value.

Notes:
- Need to figure out if it matters where in the config fragment these lines are added. Probably it doesn't matter as long as they are low enough (i.e. after any other modifications that might be happening).


### Which parameters to modify / scan?

?


### Other tips and tricks

Run `edmDumpEventContent.py <input file>` to see file contents.
Use the same followed by `| grep <search term>` to filter.
