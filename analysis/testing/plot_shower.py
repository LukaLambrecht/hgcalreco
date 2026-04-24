# Plot the shower profile on both reco and sim level

# Use case: try to figure out why the response looks so weird...


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
from tools.geometrytools import get_caloparticle_hits_per_layer
from tools.geometrytools import get_caloparticle_energy_per_layer
from tools.geometrytools import get_layercluster_hits
from tools.geometrytools import get_layercluster_energy_sum_per_layer


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-o', '--outputdir', default='output_plots_shower')
    parser.add_argument('-c', '--config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    args = parser.parse_args()

    # read events
    events = Events(args.inputfile)
    reader = Reader(args.config)

    # initialize counter
    event_counter = 0

    # loop over events
    cp_es = []
    lc_es = []
    for event in events:
            event_counter += 1
            print(f'Now running on event {event_counter}...')

            # get collections
            collections = reader.read_event(event)
            caloparticles = collections['caloparticles']
            simclusters = collections['simclusters']
            calohits_ee = collections['calohitees']
            calohits_heb = collections['calohithebs']
            calohits_hef = collections['calohithefs']
            tracksters = collections['tracksters']
            layerclusters = collections['layerclusters']
            rechits_ee = collections['rechitees']
            rechits_heb = collections['rechithebs']
            rechits_hef = collections['rechithefs']

            # make dicts mapping ID to object
            calohit_map = {hit.id(): hit for hit in calohits_ee}
            calohit_map.update({hit.id(): hit for hit in calohits_heb})
            calohit_map.update({hit.id(): hit for hit in calohits_hef})
            #rechit_map = {hit.id(): hit for hit in rechits_ee}
            #rechit_map.update({hit.id(): hit for hit in rechits_heb})
            #rechit_map.update({hit.id(): hit for hit in rechits_hef})

            # split caloparticles per layer and calculate energy per layer
            cps_hits_per_layer = []
            for caloparticle in caloparticles:
                cps_hits_per_layer.append(get_caloparticle_hits_per_layer(caloparticle, calohit_map))
            cps_energy_per_layer = []
            for cp_hits_per_layer in cps_hits_per_layer:
                cps_energy_per_layer.append(get_caloparticle_energy_per_layer(cp_hits_per_layer, normalize=True))

            # get layercluster energy per layer
            # sum layer cluster energies per layer
            lc_energy_sum_per_layer = get_layercluster_energy_sum_per_layer(layerclusters)
 
            # restrict to the positive z-side
            # (arbitrary, just to isolate a single CaloParticle and its LayerClusters in an easy way)
            cp_idx = 0 if list(cps_hits_per_layer[0].keys())[0] > 0 else 1
            cp_hits_per_layer = cps_hits_per_layer[cp_idx]
            cp_energy_per_layer = cps_energy_per_layer[cp_idx]
            lc_energy_sum_per_layer = {k: v for k, v in lc_energy_sum_per_layer.items() if k > 0}

            # calculate scale factor
            scale = caloparticles[cp_idx].energy() / sum(list(cp_energy_per_layer.values()))

            # initialize arrays for plotting
            xax = np.arange(1, 48)
            edges = np.concatenate([xax - 0.5, xax[-1:]+0.5])
            cp_e = np.array([scale*cp_energy_per_layer.get(x, 0) for x in xax])
            lc_e = np.array([lc_energy_sum_per_layer.get(x, 0) for x in xax])
            cp_es.append(cp_e)
            lc_es.append(lc_e)

            # make a plot of shower profile
            if True:
                fig, ax = plt.subplots()
                ax.stairs(cp_e, edges=edges, linewidth=2, color='crimson', label='CaloParticle shower profile')
                ax.stairs(lc_e, edges=edges, linewidth=2, color='dodgerblue', label='LayerCluster shower profile')
                ax.set_xlabel('Layer', fontsize=15)
                ax.set_ylabel('Total energy per layer', fontsize=15)
                ax.legend(fontsize=12)
                fig.tight_layout()
                fig.savefig(f'test_{event_counter}.png')

            if args.nevents > 0 and event_counter >= args.nevents: break
    
    # make plot of average profiles        
    cp_e = np.mean(np.array(cp_es), axis=0)
    lc_e = np.mean(np.array(lc_es), axis=0)
    fig, ax = plt.subplots()
    ax.stairs(cp_e, edges=edges, linewidth=2, color='crimson', label='CaloParticle shower profile')
    ax.stairs(lc_e, edges=edges, linewidth=2, color='dodgerblue', label='LayerCluster shower profile')
    ax.set_xlabel('Layer', fontsize=15)
    ax.set_ylabel('Total energy per layer', fontsize=15)
    ax.legend(fontsize=12)
    fig.tight_layout()
    fig.savefig('test.png')
