# Dump full event config

# First create one from template
python3 run_hgcalreco.py -i /eos/user/l/llambrec/hgcalreco-data/SinglePion_PT2to200/Phase2Spring24DIGIRECOMiniAOD-noPU_Trk1GeV_140X_mcRun4_realistic_v4-v1/GEN-SIM-DIGI-RAW-MINIAOD/0ae38198-d757-400c-9c55-beaf7dd1486a.root -n 10 -w temp_config_dump --no_exec

# Then run edmConfigDump
edmConfigDump temp_config_dump/hgcalreco_cff.py >> temp_config_dump/hgcalreco_cfg_full.py
echo "Output written to temp_config_dump/hgcalreco_cfg_full.py"
