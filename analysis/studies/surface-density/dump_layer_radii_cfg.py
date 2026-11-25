# Dump the HGCAL layer parameters (z position and radial range per layer) of the D127 geometry,
# with the HGCalParameterTester analyzer of Geometry/HGCalCommonData (test plugin, part of the release).
# The values of zLayerHex, rMinLayHex and rMaxLayHex for EE, HE silicon and HE scintillator in the output
# are hard-coded in surfacedensitytools.py (LAYER_Z, LAYER_RMIN, LAYER_RMAX).
#
# Usage (in the CMSSW environment): cmsRun dump_layer_radii_cfg.py > layer_parameters.log 2>&1


import FWCore.ParameterSet.Config as cms
from Configuration.Eras.Era_Phase2C26I13M9_cff import Phase2C26I13M9

process = cms.Process("GEOM", Phase2C26I13M9)
process.load("Configuration.Geometry.GeometryExtendedRun4D127_cff")
process.load("Configuration.Geometry.GeometryExtendedRun4D127Reco_cff")
process.load('FWCore.MessageService.MessageLogger_cfi')
process.MessageLogger.HGCalGeom = dict()
process.MessageLogger.cerr.threshold = 'INFO'
process.MessageLogger.cerr.HGCalGeom = cms.untracked.PSet(limit=cms.untracked.int32(-1))
process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(1))

# Mode 1: silicon (v17+ geometries), Mode 2: scintillator
process.hgcParameterTesterEE = cms.EDAnalyzer("HGCalParameterTester", Name=cms.string("HGCalEESensitive"), Mode=cms.int32(1))
process.hgcParameterTesterHESil = process.hgcParameterTesterEE.clone(Name="HGCalHESiliconSensitive")
process.hgcParameterTesterHESci = process.hgcParameterTesterEE.clone(Name="HGCalHEScintillatorSensitive", Mode=2)
process.p1 = cms.Path(process.hgcParameterTesterEE * process.hgcParameterTesterHESil * process.hgcParameterTesterHESci)
