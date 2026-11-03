#!/usr/bin/bash

# Simple setup utility to install CMSSW, check out some useful packages,
# and symlink the custom packages in cmssw_packages into it.

# Usage: ./cmssw_setup.sh [install_dir]
# The optional install_dir (default: this directory) is where the CMSSW area is created.
# Useful to install it on a location with more disk quota (e.g. /afs/cern.ch/work).

# Set CMSSW version
#cmssw_version=CMSSW_14_0_9
#cmssw_version=CMSSW_15_1_1
#cmssw_version=CMSSW_16_0_5
#cmssw_version=CMSSW_20_0_0_pre1
#cmssw_version=CMSSW_20_0_0
cmssw_version=CMSSW_20_1_0_pre5

# Set architecture
# (production architecture of the CMSSW version above, see /cvmfs/cms.cern.ch/releases.map)
export SCRAM_ARCH=el9_amd64_gcc14

# Resolve this script's own directory, so it can be run from anywhere
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
install_dir=${1:-$script_dir}
mkdir -p $install_dir
cd $install_dir

# Setup CMSSW
cmsrel $cmssw_version
cd $cmssw_version/src
cmsenv

# Clone packages
# note: from CMSSW_20_1_X onwards, RecoHGCal/TICL is restructured into RecoTICL/*
#       (with CLUE layer clustering in RecoTICL/LayerClustering).
git cms-addpkg RecoLocalCalo/HGCalRecProducers
git cms-addpkg RecoLocalCalo/HGCalRecAlgos
git cms-addpkg RecoTICL/LayerClustering
git cms-addpkg RecoTICL/PatternRecognition
git cms-addpkg DataFormats/HGCalReco
git cms-addpkg Fireworks/Geometry
git cms-addpkg SimCalorimetry/HGCalAssociatorProducers

# Apply local patches (see cmssw_patches)
for patch in "$script_dir"/cmssw_patches/*.patch; do
    git apply "$patch"
done

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
