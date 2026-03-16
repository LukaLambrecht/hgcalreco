# Dump detector geometry for event visualization

# Note: still to figure out which arguments to use exaclty.

# The version below should be synchronized with the current version of run_hgcalreco.py.
# Note: when including tracker and/or muon, gives an error "size mismatch between geometry and alignments"...

cmsRun $CMSSW_BASE/src/Fireworks/Geometry/python/dumpRecoGeometry_cfg.py \
tag=2026 \
version=D110 \
tracker=False \
muon=False \
calo=True
