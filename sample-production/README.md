# Custom sample production

### Baseline reference sample
Start from this example:
```
/SinglePion_PT2to200/
Phase2Spring24DIGIRECOMiniAOD-noPU_Trk1GeV_140X_mcRun4_realistic_v4-v1/
GEN-SIM-DIGI-RAW-MINIAOD
```

Check DAS/McM for exact cmsDriver commands:
- [chain](https://cms-pdmv-prod.web.cern.ch/mcm/chained_requests?contains=TSG-Phase2Spring24DIGIRECOMiniAOD-00124&page=0&shown=15)
- [gen-sim](https://cms-pdmv-prod.web.cern.ch/mcm/requests?prepid=TSG-Phase2Spring24GS-00168&page=0&shown=549756078207)
- [digi-reco-miniaod](https://cms-pdmv-prod.web.cern.ch/mcm/requests?prepid=TSG-Phase2Spring24DIGIRECOMiniAOD-00124&page=0&shown=549756078207)

### Adding pileup
Use this as an example:
```
/SinglePion_PT2to200/
Phase2Spring24DIGIRECOMiniAOD-PU200_Trk1GeV_pilot_140X_mcRun4_realistic_v4-v1/
GEN-SIM-DIGI-RAW-MINIAOD
```

Check DAS/McM for exact cmsDriver commands:
- [chain](https://cms-pdmv-prod.web.cern.ch/mcm/chained_requests?contains=TSG-Phase2Spring24DIGIRECOMiniAOD-00123&page=0&shown=15)
- gen-sim: same as without pileup.
- [digi-reco-miniaod](https://cms-pdmv-prod.web.cern.ch/mcm/requests?prepid=TSG-Phase2Spring24DIGIRECOMiniAOD-00123&page=0&shown=549756078207). Seems very similar to the case without pileup except for the addition of `--pileup_input "dbs:/MinBias_TuneCP5_14TeV-pythia8/Phase2Spring24GS-140X_mcRun4_realistic_v4-v1/GEN-SIM" --pileup 'AVE_200_BX_25ns'` to the `step1` command.

### Switching to a different CMSSW version
Not yet clear how to do this very systematically, but here are a few pointers.

Latest available releases: see e.g. [here](https://github.com/cms-sw/cmssw/releases)

Combinations of global tags, geometries, and eras:
one can check e.g. [Configuration/PyReleaseValidation/python/upgradeWorkflowComponents.py](https://github.com/cms-sw/cmssw/blob/master/Configuration/PyReleaseValidation/python/upgradeWorkflowComponents.py).
Switch to the branch for the targeted CMSSW version, and scroll (almost) all the way down until you see something like [this](https://github.com/cms-sw/cmssw/blob/3c20d4cff8115035a716ef635a1def5cf6e66249/Configuration/PyReleaseValidation/python/upgradeWorkflowComponents.py#L3741):
```
    'Run4D123' : {
        'Geom' : 'ExtendedRun4D123',
        'HLTmenu': '@relvalRun4',
        'GT' : 'auto:phase2_realistic_T33',
        'Era' : 'Phase2C26I13M9',
        'ScenToRun' : ['GenSimHLBeamSpot','DigiTrigger','RecoGlobal', 'HARVESTGlobal', 'ALCAPhase2'],
    },
```
Unfortunately, this might still crash because it doesn't give you a full valid cmsDriver command.
For now this has been trial-and-error, and help from CG (the second best thing after actual experts).

Other than that, just check with experts.
For example, the recommended geometry at the time of writing appears to be 121, which does not seem to be the latest one.

Finding a good pileup dataset:
also a bit of trial and error.
Try to find samples on DAS with the same CMSSW verion and geometry (typically at least some RelVal samples exist),
and check which pileup dataset they are using.

### Todo
Try out other particles instead of pions by modifying the PDG ID in the generator fragment, etc.
