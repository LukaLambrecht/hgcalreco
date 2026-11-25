# Extract the kinematics at the calorimeter boundary of the "caloBoundary" particles of the MC-truth graph
# (all interactions, i.e. including pileup), and store them for plot_surface_density.py.
#
# This is the slow step (reading the truth::Graph, ~1 s per PU200 event, since the graph is stored as one
# unsplit object of ~12 MB per event); the selection, extrapolation and plotting run on its output in seconds.
#
# Per particle: position (x, y, z in cm) and momentum (px, py, pz in GeV) at the calorimeter boundary
# (trajectory checkpoint 0) and the absolute PDG id; event_offsets gives the first particle of each event.
# Only particles crossing the boundary in the endcap regions (|z| >= --zmin, default 250 cm) are stored.
#
# Example: python3 extract_boundary_particles.py -i <production file(s)> -n 100 -o <output npz file>


import os
import time
import argparse
import numpy as np


DEFAULT_INPUT = ['/eos/home-l/llambrec/hgcalreco-data/production/SinglePion_201X_D127_PU200/file_0.root']
DEFAULT_OUTPUT = '/eos/home-l/llambrec/hgcalreco-data/surface-density/boundary_particles_SinglePion_201X_D127_PU200_file_0.npz'
CALO_BOUNDARY_BIT = 1 << 3  # see SimDataFormats/TruthInfo/interface/ParticleData.h
CALO_BOUNDARY_CHECKPOINT = 0
FIELDS = ['x', 'y', 'z', 'px', 'py', 'pz', 'pdgid']

# C++ helper to extract the boundary kinematics of the caloBoundary particles
# (looping over the ~150k particles per PU200 event in python takes ~25 s per event)
CPP_HELPER = '''
#include "SimDataFormats/TruthInfo/interface/Graph.h"
#include <vector>
#include <cmath>
std::vector<std::vector<float>> getCaloBoundaryKinematics(const truth::Graph& graph, unsigned int bit,
                                                          unsigned int checkpointId, float zmin) {
  // returns {x, y, z, px, py, pz, abs(pdgId)} at the calorimeter boundary
  std::vector<std::vector<float>> out(7);
  for (const auto& p : graph.particles()) {
    if (!(p.levelFlags & bit)) continue;
    for (const auto& cp : p.checkpoints) {
      if (cp.checkpointId != checkpointId) continue;
      if (std::abs(cp.position.z()) < zmin) break;
      out[0].push_back(cp.position.x()); out[1].push_back(cp.position.y()); out[2].push_back(cp.position.z());
      out[3].push_back(cp.momentum.px()); out[4].push_back(cp.momentum.py()); out[5].push_back(cp.momentum.pz());
      out[6].push_back(std::abs(p.pdgId));
      break;
    }
  }
  return out;
}
'''


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Extract the boundary kinematics of the caloBoundary truth particles')
    parser.add_argument('-i', '--inputfiles', nargs='+', default=DEFAULT_INPUT, help='Input (production) files with the truth::Graph')
    parser.add_argument('-n', '--nevents', default=-1, type=int, help='Maximum number of events (default: all)')
    parser.add_argument('-o', '--outputfile', default=DEFAULT_OUTPUT)
    parser.add_argument('--zmin', default=250., type=float, help='Minimum |z| (cm) of the boundary crossing (default: 250)')
    args = parser.parse_args()

    import ROOT
    from DataFormats.FWLite import Events, Handle
    ROOT.gInterpreter.Declare(CPP_HELPER)

    handle = Handle('truth::Graph')
    events = Events(args.inputfiles)
    nevents = events.size() if args.nevents < 0 else min(args.nevents, events.size())
    print(f'Processing {nevents} events (~1 s per PU200 event)...')
    data = {field: [] for field in FIELDS}
    offsets = [0]
    start = time.time()
    for idx, event in enumerate(events):
        if idx >= nevents: break
        event.getByLabel('truthLogicalGraphProducer', handle)
        res = ROOT.getCaloBoundaryKinematics(handle.product(), CALO_BOUNDARY_BIT, CALO_BOUNDARY_CHECKPOINT, args.zmin)
        for fidx, field in enumerate(FIELDS): data[field].append(np.array(res[fidx], dtype=np.float32))
        offsets.append(offsets[-1] + len(res[0]))
        if (idx + 1) % 10 == 0 or idx + 1 == nevents:
            elapsed = time.time() - start
            print(f'  {idx + 1}/{nevents} events ({elapsed:.0f} s, ETA {elapsed / (idx + 1) * (nevents - idx - 1):.0f} s)')

    os.makedirs(os.path.dirname(os.path.abspath(args.outputfile)), exist_ok=True)
    arrays = {field: np.concatenate(values) for field, values in data.items()}
    arrays['pdgid'] = arrays['pdgid'].astype(np.int32)
    np.savez(args.outputfile, event_offsets=np.array(offsets, dtype=np.int64), inputfiles=np.array(args.inputfiles), **arrays)
    print(f'Stored {offsets[-1]} particles ({offsets[-1] / nevents:.0f} per event) in {args.outputfile}')
