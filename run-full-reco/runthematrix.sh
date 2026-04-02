# Workflows are defined here:
# - Configuration/PyReleaseValidation/python/relval_upgrade.py
# - Configuration/PyReleaseValidation/python/upgradeWorkflowComponents.py

# The .207 variant is define here:
# https://github.com/cms-sw/cmssw/blob/4de582dbdd39567ab5ea6897a0c86dc4cfeead74/Configuration/PyReleaseValidation/python/upgradeWorkflowComponents.py#L956

# The workflow can be shown using
# runTheMatrix.py -w upgrade --showMatrix | grep <workflow number>

# Somehow the provided 29690.207 does not seem to be defined (in 15_0_1),
# though both 29690 and .207 are defined individually (but not in combination).
# Is an even newer release needed?

runTheMatrix.py -w upgrade --nEvents 100 -l 29690.207  --maxSteps 4
