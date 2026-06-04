# Dump full event config

# First create one from template
python3 run_hgcalreco.py -i ../sample-production/output_test/job0/step2.root -n 10 -w temp_config_dump --no_exec

# Then run edmConfigDump
edmConfigDump temp_config_dump/hgcalreco_cff.py >> temp_config_dump/hgcalreco_cfg_full.py
echo "Output written to temp_config_dump/hgcalreco_cfg_full.py"
