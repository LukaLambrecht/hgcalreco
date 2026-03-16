# Run minimal HGCAL reco

Note: still to figure out which combinations of CMSSW versions, arguments, and input files are working...

For current version (10 March 2026):
- Input files: produced with CMSSW `14_0_X` (e.g. this dataset: `SinglePion_PT2to200/Phase2Spring24DIGIRECOMiniAOD-noPU_Trk1GeV_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD`)
- CMSSW version: run everything in CMSSW `14_0_9` for consistency.
- Geometry: can get it from DAS, click `Configs` and scan the cmsRun config. For this dataset, it is `GeometryExtended2026D110` and/or `GeometryExtended2026D110Reco` (not yet clear what the difference is).
- Global tag: can get it in the same way as the geometry. For this dataset, it is `140X_mcRun4_realistic_v4`.

Status: runs and produces some nonzero output!
But does not seem to correspond 100% with the already existing "HLT" process outputs. To check.
