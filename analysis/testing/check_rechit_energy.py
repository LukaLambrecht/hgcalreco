# Do some sanity checks.

# In particular: check distribution of RecHit energies per layer.


import os
import sys
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_detid_layer
from tools.geometrytools import get_detid_subdetid
from tools.layertools import get_quantity_per_layer


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-c', '--config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    args = parser.parse_args()

    # read events
    events = Events(args.inputfile)
    reader = Reader(args.config)

    # initialize counters
    nevents = 0

    # loop over event
    for event in events:
        nevents += 1
        print(f'--- Event {nevents} ---')

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
        # note: for rechits, the id seems to return a DetId object,
        #       while for calohits, the id seems to be an integer
        #       (probably corresponding to the raw id);
        #       try to use the integer for both, for consistency.
        calohit_map = {hit.id(): hit for hit in calohits_ee}
        calohit_map.update({hit.id(): hit for hit in calohits_heb})
        calohit_map.update({hit.id(): hit for hit in calohits_hef})
        rechit_map = {hit.id().rawId(): hit for hit in rechits_ee}
        rechit_map.update({hit.id().rawId(): hit for hit in rechits_heb})
        rechit_map.update({hit.id().rawId(): hit for hit in rechits_hef})

        # get layers and subdetector IDs and energy of calohits and rechits
        calohit_ids = np.array(list(calohit_map.keys()))
        rechit_ids = np.array(list(rechit_map.keys()))
        calohit_layers = np.array([get_detid_layer(int(detid)) for detid in calohit_ids])
        rechit_layers = np.array([get_detid_layer(int(detid)) for detid in rechit_ids])
        calohit_subdets = np.array([get_detid_subdetid(int(detid)) for detid in calohit_ids])
        rechit_subdets = np.array([get_detid_subdetid(int(detid)) for detid in rechit_ids])
        calohit_energy = np.array([calohit_map[detid].energy() for detid in calohit_ids])
        rechit_energy = np.array([rechit_map[detid].energy() for detid in rechit_ids])

        # optional: select subdetector
        #calohit_mask = np.ones(len(calohit_ids)).astype(bool)
        #rechit_mask = np.ones(len(rechit_ids)).astype(bool)
        calohit_mask = (calohit_subdets==1)
        rechit_mask = (rechit_subdets==1)

        # divide energy per layer
        xax = np.arange(1, 48)
        this_calohit_energy_per_layer = get_quantity_per_layer(calohit_energy[calohit_mask], calohit_layers[calohit_mask], keys=xax, absolute=True)
        this_rechit_energy_per_layer = get_quantity_per_layer(rechit_energy[rechit_mask], rechit_layers[rechit_mask], keys=xax, absolute=True)
        if nevents==1:
            calohit_energy_per_layer = {key: [val] for key, val in this_calohit_energy_per_layer.items()}
            rechit_energy_per_layer = {key: [val] for key, val in this_rechit_energy_per_layer.items()}
        else:
            for key in this_calohit_energy_per_layer.keys(): calohit_energy_per_layer[key].append(this_calohit_energy_per_layer[key])
            for key in this_rechit_energy_per_layer.keys(): rechit_energy_per_layer[key].append(this_rechit_energy_per_layer[key])

        if args.nevents > 0 and nevents >= args.nevents: break

    # concatenate
    for key in calohit_energy_per_layer.keys(): calohit_energy_per_layer[key] = np.concatenate(calohit_energy_per_layer[key])
    for key in rechit_energy_per_layer.keys(): rechit_energy_per_layer[key] = np.concatenate(rechit_energy_per_layer[key])

    # make a plot of rechit energy distribution
    fig, ax = plt.subplots()
    cmap = plt.get_cmap('jet')
    bins = np.linspace(0, 1, num=50)
    for idx, (key, val) in enumerate(rechit_energy_per_layer.items()):
        ax.hist(val, bins=bins, histtype='step', color=cmap(idx/len(rechit_energy_per_layer)))
    ax.set_xlabel('Energy', fontsize=12)
    ax.set_ylabel('Number of hits (normalized)', fontsize=12)
    fig.savefig('test.png')
    ax.set_yscale('log')
    fig.savefig('test_log.png')
    
    # make a plot of rechit energy distribution
    fig, ax = plt.subplots()
    for idx, (key, val) in enumerate(rechit_energy_per_layer.items()):
        ax.hist(val, bins=bins, density=True, histtype='step', color=cmap(idx/len(rechit_energy_per_layer)))
    ax.set_xlabel('Energy', fontsize=12)
    ax.set_ylabel('Number of hits (normalized)', fontsize=12)
    fig.savefig('test_normalized.png')
    ax.set_yscale('log')
    fig.savefig('test_normalized_log.png')
