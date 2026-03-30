# Prepare a CMSSW version for sample production

# The generator fragment must be placed inside a CMSSW module in order to be read correctly.
# This script creates a suitable directory inside a CMSSW release (the naming is arbitrary)
# and recompiles such that the module can be found by cmsDriver / cmsRun.

cd $CMSSW_BASE/src
mkdir -p Configuration/GenProduction/python
scramv1 b -j8
