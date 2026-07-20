#!/usr/bin/bash

# Simple setup utility to install CMSSW, check out some useful packages,
# and symlink the custom packages in cmssw_packages into it.

# Set CMSSW version
#cmssw_version=CMSSW_14_0_9
#cmssw_version=CMSSW_15_1_1
#cmssw_version=CMSSW_16_0_5
cmssw_version=CMSSW_20_0_0_pre1

# Resolve this script's own directory, so it can be run from anywhere
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Setup CMSSW
cmsrel $cmssw_version
cd $cmssw_version/src
cmsenv

# Clone packages
git cms-addpkg RecoLocalCalo/HGCalRecProducers
git cms-addpkg RecoLocalCalo/HGCalRecAlgos
git cms-addpkg RecoHGCal/TICL
git cms-addpkg DataFormats/HGCalReco
git cms-addpkg Fireworks/Geometry

# Symlink custom packages (see cmssw_packages/README.md) into this CMSSW area
cd "$script_dir/cmssw_packages"
python3 make_symlinks.py

# Prepare CMSSW for sample production (see sample-production/README.md)
mkdir -p $CMSSW_BASE/src/Configuration/GenProduction/python
cp "$script_dir"/sample-production/fragments/*.py $CMSSW_BASE/src/Configuration/GenProduction/python/

# Recompile (once, after all of the above)
cd $CMSSW_BASE/src
scram b -j 8

# Go back to this directory
cd $script_dir
