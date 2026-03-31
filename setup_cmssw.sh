# Simple setup utility to install CMSSW and check out some useful packages

# Set CMSSW version
#cmssw_version=CMSSW_14_0_9
cmssw_version=CMSSW_15_1_1

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
