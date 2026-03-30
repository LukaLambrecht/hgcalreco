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

### Todo
Then later update to newer CMSSW, other particles, etc.
