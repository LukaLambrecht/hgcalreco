# Plot integral of response (i.e. not per layer but total CaloParticle vs sum-of-LayerCluster)


import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_energy_sum_per_layer


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_plots_response_integral')
    parser.add_argument('-c', '--config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    args = parser.parse_args()

    # initialize reader
    reader = Reader(args.config)

    # initialize counter
    event_counter = 0

    # loop over events
    cp_es = []
    lc_es = []
    for inputfile in args.inputfile:
        events = Events(args.inputfile)
        for event in events:
            event_counter += 1
            print(f'Now running on event {event_counter}...')

            # get collections
            collections = reader.read_event(event)
            caloparticles = collections['caloparticles']
            layerclusters = collections['layerclusters']

            # get layercluster energy per layer
            lc_energy_sum_per_layer = get_layercluster_energy_sum_per_layer(layerclusters)

            # sum positive and negative side
            lc_energy_sum_pos = sum([v for k, v in lc_energy_sum_per_layer.items() if k > 0])
            lc_energy_sum_neg = sum([v for k, v in lc_energy_sum_per_layer.items() if k < 0])

            # add to results
            # note: this only makes sense for single-particle samples
            #       (actually 2 particles, back to back, with the same energy) and no pileup! 
            #       in that case it doesn't matter how the layerclusters are assigned to each caloparticle.
            cp_es.append(caloparticles[0].energy())
            cp_es.append(caloparticles[1].energy())
            lc_es.append(lc_energy_sum_pos)
            lc_es.append(lc_energy_sum_neg)

            if args.nevents > 0 and event_counter >= args.nevents: break
    
    # make response
    cp_es = np.array(cp_es)
    lc_es = np.array(lc_es)
    response = np.divide(lc_es, cp_es)
    print(np.mean(response))
    print(np.std(response))

    # bin response in caloparticle energy
    bins = np.linspace(0, 2000, num=21)
    ids = np.digitize(cp_es, bins)
    response_binned = [response[ids==idx] for idx in range(1, len(bins))]
    response_avg = np.array([np.mean(el) for el in response_binned])
    cp_es_counts = np.histogram(cp_es, bins=bins)[0]
    cp_es_counts = cp_es_counts / np.amax(cp_es_counts)

    # make plot
    fig, ax = plt.subplots()
    ax.stairs(cp_es_counts, edges=bins, fill=True, color='grey', alpha=0.3, label='CaloParticles (normalized)')
    ax.stairs(response_avg, edges=bins, linewidth=2, color='dodgerblue', label='Average response')
    ax.set_xlabel('CaloParticle energy', fontsize=15)
    ax.set_ylabel('Response', fontsize=15)
    ax.legend(fontsize=12)
    fig.tight_layout()
    fig.savefig('test.png')
