#!/usr/bin/bash

# Prepare a CMSSW version for sample production
# Note: this is done automatically by ../cmssw_setup.sh when setting up a new CMSSW version,
# so normally you do not need to run this script yourself.
# Kept here for the case of an already-set-up CMSSW area that still needs this step.

# The generator fragment must be placed inside a CMSSW module in order to be read correctly.
# This script creates a suitable directory inside a CMSSW release
# (the naming is arbitrary but must correspond to what is used in produce.py),
# copies the available fragments into it,
# and recompiles such that the module can be found by cmsDriver / cmsRun.

# Resolve this script's own directory, so it can be run from anywhere
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cd $CMSSW_BASE/src
mkdir -p Configuration/GenProduction/python
cp "$script_dir"/fragments/*.py Configuration/GenProduction/python/
scramv1 b -j8
