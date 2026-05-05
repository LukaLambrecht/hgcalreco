# Run minimal HGCAL reco

Note: still to figure out in a somewhat systematic way which combinations of CMSSW versions, arguments, and input files are working...


### First version (10 March 2026)

Settings:
- Input files: produced with CMSSW `14_0_X` (e.g. this dataset: `SinglePion_PT2to200/Phase2Spring24DIGIRECOMiniAOD-noPU_Trk1GeV_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD`)
- CMSSW version: run everything in CMSSW `14_0_9` for consistency.
- Geometry: can get it from DAS, click `Configs` and scan the cmsRun config. For this dataset, it is `GeometryExtended2026D110` and/or `GeometryExtended2026D110Reco` (not yet clear what the difference is).
- Global tag: can get it in the same way as the geometry. For this dataset, it is `140X_mcRun4_realistic_v4`.

Status:
- Runs and produces sensible output!
- Also very fast, O(10 events / second).
- Does not seem to correspond 100% with the already existing "HLT" process outputs (in event displays).
To check. Could be different geometry or other settings, or simply HLT vs offline.


### Second version (2 April 2026)

Settings:
- Input files: custom produced samples, see `sample-production` folder.
- CMSSW version: run everything in CMSSW `16_0_5` for consistency.
- Geometry: GeometryExtendedRun4D121 (see production configuration).
- Global tag: `150X_mcRun4_realistic_v1` (see production configuration).

Note: the switch from `CMSSW_14_0_9` to `CMSSW_16_0_5` also required a slightly different syntax in the template.
Details not yet completely understood, but it is a matter of correctly taking the upstream input
(in either the RECO or HLT process) and making it available to the custom current process,
which apparently has to be done in different ways in both CMSSW versions.
Maybe try to find cleaner solution later, but at least for now the templates for both releases have been verified
to work in their respective targeted release, so good enough for now.


# Expected input format

Currently there is no complete list of objects / collections that are strictly required in the input file.
See the `sample-production` folder for `cmsDriver` commands that produce files that have been tested to work.

Note: currently only the files produced with "minimal" HGCAL-specific output seem to work with this re-reco code.
Files produced with the "full" output seem to have missing products, so probably not so full after all.
It seems some RECO collections (in particular the HGCalRecHits) are not written to the output by default in "full" mode,
while they are required as input for this "minimal" HGCAL-specific re-reco.

Follow-up on the issue above: try to explicitly add all required collections / objects to the "full" output mode
for the produced samples to work with this re-reco code.
-> Seems to work after adding the "hgcalDigis" collection to the "full" output.
Now this "minimal" HGCAL-specific re-reco works on input files produced with both minimal and full output mode.
