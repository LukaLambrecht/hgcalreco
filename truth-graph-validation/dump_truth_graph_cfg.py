# Dump the MC-truth graph (see PhysicsTools/TruthInfo, cms-sw/cmssw PR #51213)
# from a sample-production file produced with `produce.py --output-mode truth`,
# as visualizable DOT files.
#
# Unlike the upstream PhysicsTools/TruthInfo/test/dumpTruthGraphsFromGENSIMRECO_cfg.py
# (which re-runs the TruthGraphProducer/TruthLogicalGraphProducer/
# TruthLogicalGraphHitIndexProducer EDProducers from raw SimTracks/RecHits), this
# reads the already-persisted TruthGraph/truth::Graph/truth::LogicalGraphHitIndex
# products directly from the input file and only runs the two dumper EDAnalyzers.
# This works because --output-mode truth already computed and kept those products
# at production time (see sample-production/produce.py), and keeps this script
# usable on the same small, lean output file rather than requiring one that also
# carries raw g4SimHits/generatorSmeared (which --output-mode truth deliberately
# does not keep, to keep the output small).


import os
import FWCore.ParameterSet.Config as cms
from argparse import ArgumentParser, BooleanOptionalAction

parser = ArgumentParser()
parser.add_argument("inputFile", nargs='?', default="step2.root",
                    metavar='FILE', help="Input file produced with --output-mode truth, default=%(default)r")
parser.add_argument('-o', "--outdir", default='',
                    help="output directory, default=%(default)r")
parser.add_argument('-n', "--maxevts", type=int, default=-1,
                    help="maximum number of events to process, default=%(default)s")
parser.add_argument('-t', "--tag", default='', help="tag for output file names")
parser.add_argument("--process", default="RECO",
                    help="process name the truth-graph producers ran in during"
                         " production (RECO for the default sample-production"
                         " chain), default=%(default)r")
parser.add_argument("--layout", default="dot",
                    help="DOT layout for the logical-graph dump: 'dot' (default,"
                         " hierarchical L->R ranks) or a force-directed engine"
                         " ('sfdp'/'fdp'/'neato') for node repulsion + spring edges")
parser.add_argument("--showAll", action='store_true',
                    help="do not hide zero-simhit subgraphs or large SIM source"
                         " vertices in the logical DOT dump")
args = parser.parse_args()

if '/' not in args.inputFile and ':' not in args.inputFile:
    args.inputFile = 'file:' + args.inputFile
elif not args.inputFile.startswith('file:') and not args.inputFile.startswith('root:'):
    # produce.py output files are given as plain (possibly absolute) paths;
    # the upstream script's own "no '/' or ':'" heuristic misses those.
    args.inputFile = 'file:' + args.inputFile
if args.outdir and not os.path.exists(args.outdir):
    os.makedirs(args.outdir, exist_ok=True)

process = cms.Process("TRUTHGRAPHDUMP")

process.load("FWCore.MessageService.MessageLogger_cfi")

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(args.maxevts))

process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(args.inputFile),
)

process.options = cms.untracked.PSet(wantSummary=cms.untracked.bool(True))

truthGraphTag = cms.InputTag("truthGraphProducer", "", args.process)
truthLogicalGraphTag = cms.InputTag("truthLogicalGraphProducer", "", args.process)
hitIndexTag = cms.InputTag("truthLogicalGraphHitIndexProducer", "", args.process)

process.truthGraphDumper = cms.EDAnalyzer(
    "TruthGraphDumper",
    src=truthGraphTag,
    dotFile=cms.string(os.path.join(args.outdir, f"truthgraph{args.tag}.dot")),
    maxNodes=cms.uint32(20000),
    maxEdgesPerNode=cms.uint32(50),
    # SimTracks/SimVertices/HepMC are optional (mayConsume) enrichments the
    # dumper does not strictly need; --output-mode truth output does not keep
    # them, so leave these at their (absent, harmlessly skipped) defaults.
    simTracks=cms.InputTag("g4SimHits"),
    simVertices=cms.InputTag("g4SimHits"),
    genEventHepMC=cms.InputTag("generatorSmeared"),
    genEventHepMC3=cms.InputTag("generatorSmeared"),
)

process.truthLogicalGraphDumper = cms.EDAnalyzer(
    "TruthLogicalGraphDumper",
    src=truthLogicalGraphTag,
    rawSrc=truthGraphTag,
    hitIndex=hitIndexTag,

    hgcalRecHits=cms.VInputTag(
        cms.InputTag("HGCalRecHit", "HGCEERecHits", args.process),
        cms.InputTag("HGCalRecHit", "HGCHEFRecHits", args.process),
        cms.InputTag("HGCalRecHit", "HGCHEBRecHits", args.process),
    ),
    # PFRecHits are not part of --output-mode truth's lean output; the dumper
    # handles missing collections gracefully (as DetIdToRecHitMapProducer does).
    pfRecHits=cms.VInputTag(),

    dotFile=cms.string(os.path.join(args.outdir, f"truthlogicalgraph{args.tag}.dot")),

    layout=cms.string(args.layout),

    maxParticles=cms.uint32(20000),
    maxVertices=cms.uint32(20000),
    maxEdgesPerNode=cms.uint32(1000000 if args.showAll else 300),

    hideLargeSimSourceVertices=cms.bool(not args.showAll),
    largeSimSourceVertexMinOutgoing=cms.uint32(50),

    hideZeroSimHitSubgraphs=cms.bool(not args.showAll),
)

process.MessageLogger.cerr.threshold = "INFO"
process.MessageLogger.cerr.default = cms.untracked.PSet(limit=cms.untracked.int32(0))
process.MessageLogger.cerr.TruthGraphDumper = cms.untracked.PSet(limit=cms.untracked.int32(-1))
process.MessageLogger.cerr.TruthLogicalGraphDumper = cms.untracked.PSet(limit=cms.untracked.int32(-1))

process.dump_step = cms.EndPath(
    process.truthGraphDumper
    + process.truthLogicalGraphDumper
)
