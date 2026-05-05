cmsDriver.py step2 \
  --python_filename step2_MINIAOD.py \
  --eventcontent MINIAODSIM \
  --customise SLHCUpgradeSimulations/Configuration/aging.customise_aging_1000 \
  --datatier GEN-SIM-DIGI-RAW-MINIAOD \
  --inputCommands "keep *" \
  --conditions auto:phase2_realistic_T33 \
  --step RAW2DIGI,RECO,RECOSIM,PAT \
  --geometry ExtendedRun4D121 \
  --era Phase2C22I13M9 \
  --mc \
  -n -1 \
  --filein file:FILEIN \
  --fileout FILEOUT \
  --processName HGCALTICL \
  --customise_commands "process.load('SimCalorimetry.HGCalAssociatorProducers.LCToCPAssociation_cfi');
        process.load('SimCalorimetry.HGCalAssociatorProducers.LCToSCAssociation_cfi');
        process.load('SimCalorimetry.HGCalSimProducers.hgcHitAssociation_cfi');
        process.hgcalAssociatorTask = cms.Task(
            process.lcAssocByEnergyScoreProducer,
            process.scAssocByEnergyScoreProducer,
            process.layerClusterCaloParticleAssociation,
            process.layerClusterSimClusterAssociation
        );
        process.reconstruction_step.associate(process.hgcalAssociatorTask)"
