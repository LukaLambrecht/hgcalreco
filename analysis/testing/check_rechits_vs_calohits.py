# Do some sanity checks.

# In particular: check overlap between detector IDs for RecHits and CaloHits,
# and check if their reported energies are the same.

# Conclusions (so far):
# - There are O(10) times more RecHits than CaloHits.
#   Is this just electronics noise? Maybe cross-talk between neighbouring cells?
# - Most CaloHits (60-90%) seem to have a match in the collection of RecHits,
#   but obviously not the other way around.
# - More puzzlingly, the number of RecHits transitions very sharply depending on the layer;
#   the transition seems to be between the last all-silicon layer and the first mixed layer.
# - Even for the ones that match, the energy is vastly different,
#   probably completely different quantities and/or units;
#   can definitely not compare directly to each other.


import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_detid_layer
from tools.geometrytools import get_detid_subdetid
from tools.geometrytools import get_detid_silicon_thickness
from tools.layertools import get_layer_counts


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-c', '--config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    args = parser.parse_args()

    # read events
    events = Events(args.inputfiles)
    reader = Reader(args.config)

    # initialize counters
    nevents = 0
    ncp = 0
    nlc = 0
    calohit_counts = None
    rechit_counts = None

    # other initializations
    calohit_layer = []
    rechit_layer = []
    calohit_subdet = []
    rechit_subdet = []
    calohit_thickness = []
    rechit_thickness = []

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

        # calculate overlap between detids between calohits and rechits
        calohit_ids = np.array(list(calohit_map.keys()))
        rechit_ids = np.array(list(rechit_map.keys()))
        both_ids = np.intersect1d(calohit_ids, rechit_ids)

        # do printouts
        if False:
            print(f'Number of CaloHits: {len(calohit_ids)}')
            print(f'Number of RecHits: {len(rechit_ids)}')
            print(f'Number of DetIds in both: {len(both_ids)}')
            print(f'Fraction of CaloHits also in RecHits: {len(both_ids)/len(calohit_ids)}')

        # check energy of common detids
        if False:
            test_id = both_ids[0]
            print(calohit_map[test_id].energy())
            print(rechit_map[test_id].energy())

        # get layers, subdetectors, and sensor thicknesses of calohits and rechits
        calohit_layer.append( np.array([get_detid_layer(int(detid)) for detid in calohit_ids]) )
        rechit_layer.append( np.array([get_detid_layer(int(detid)) for detid in rechit_ids]) )
        calohit_subdet.append( np.array([get_detid_subdetid(int(detid)) for detid in calohit_ids]) )
        rechit_subdet.append( np.array([get_detid_subdetid(int(detid)) for detid in rechit_ids]) )
        calohit_thickness.append( np.array([get_detid_silicon_thickness(int(detid)) for detid in calohit_ids]) )
        rechit_thickness.append( np.array([get_detid_silicon_thickness(int(detid)) for detid in rechit_ids]) )

        if args.nevents > 0 and nevents >= args.nevents: break

    # concatenate
    calohit_layer = np.concatenate(calohit_layer)
    calohit_subdet = np.concatenate(calohit_subdet)
    calohit_thickness = np.concatenate(calohit_thickness)
    rechit_layer = np.concatenate(rechit_layer)
    rechit_subdet = np.concatenate(rechit_subdet)
    rechit_thickness = np.concatenate(rechit_thickness) 

    # make masks for subdetectors
    calohit_subdet_masks = {
        'all': np.ones(len(calohit_subdet)).astype(bool),
        'EE': (calohit_subdet==0).astype(bool),
        'HSi': (calohit_subdet==1).astype(bool),
        'HSci': (calohit_subdet==2).astype(bool),
    }
    rechit_subdet_masks = {
        'all': np.ones(len(rechit_subdet)).astype(bool),
        'EE': (rechit_subdet==0).astype(bool),
        'HSi': (rechit_subdet==1).astype(bool),
        'HSci': (rechit_subdet==2).astype(bool),
    }

    # make masks for thicknesses
    calohit_thickness_masks = {
        'all': np.ones(len(calohit_thickness)).astype(bool),
        'thin': (calohit_thickness==0).astype(bool),
        'medium': (calohit_thickness==1).astype(bool),
        'thick': (calohit_thickness==2).astype(bool),
    }
    rechit_thickness_masks = {
        'all': np.ones(len(rechit_thickness)).astype(bool),
        'thin': (rechit_thickness==0).astype(bool),
        'medium': (rechit_thickness==1).astype(bool),
        'thick': (rechit_thickness==2).astype(bool),
    }

    outputdir = 'output_plots_rechits_vs_calohits'
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # loop over subdetectors and thicknesses
    for subdet_key in rechit_subdet_masks.keys():
        for thickness_key in rechit_thickness_masks.keys():
            rechit_mask = ((rechit_subdet_masks[subdet_key]) & (rechit_thickness_masks[thickness_key]))
            calohit_mask = ((calohit_subdet_masks[subdet_key]) & (calohit_thickness_masks[thickness_key]))
            tag = f'{subdet_key}_{thickness_key}'

            # skip some combinations that don't make sense
            if thickness_key!='all' and subdet_key not in ['EE', 'HSi']: continue

            # divide counts per layer
            xax = np.arange(1, 48)
            calohit_counts = np.array(list(get_layer_counts(calohit_layer[calohit_mask], keys=xax, absolute=True).values()))
            rechit_counts = np.array(list(get_layer_counts(rechit_layer[rechit_mask], keys=xax, absolute=True).values()))

            # make text to write in plot
            text = f'Subdetector: {subdet_key}'
            if thickness_key!='all': text += f'\nSi thickness: {thickness_key}'

            # make a plot of number of rechits and calohits
            fig, ax = plt.subplots()
            ax.errorbar(xax, calohit_counts/nevents, yerr=np.sqrt(calohit_counts)/nevents,
                marker='o', markersize=5, fmt='o', color='b', label='CaloHits')
            ax.errorbar(xax, rechit_counts/nevents, yerr=np.sqrt(rechit_counts)/nevents,
                marker='o', markersize=5, fmt='o', color='r', label='RecHits')
            ax.set_xlabel('Layer number', fontsize=12)
            ax.set_ylabel('Number of hits per layer per event', fontsize=12)
            ax.text(0.99, 0.99, text, ha='right', va='top', fontsize=12, transform=ax.transAxes)
            ax.legend(fontsize=12)
            ax.set_yscale('log')
            fig.savefig(os.path.join(outputdir, f'test_absolute_{tag}.png'))

            # make a plot of the ratio
            fig, ax = plt.subplots()
            ratio = np.divide(rechit_counts, calohit_counts)
            error = np.multiply(ratio, np.sqrt(1/rechit_counts + 1/calohit_counts))
            xax = np.arange(1, len(ratio)+1)
            ax.errorbar(xax, ratio, yerr=error, marker='o', markersize=5, fmt='o', color='b')
            ax.axhline(y=1, color='grey', linestyle='--')
            ax.set_xlabel('Layer number', fontsize=12)
            ax.set_ylabel('Number of RecHits / number of CaloHits', fontsize=12)
            ax.text(0.99, 0.99, text, ha='right', va='top', fontsize=12, transform=ax.transAxes)
            ax.set_yscale('log')
            fig.savefig(os.path.join(outputdir, f'test_ratio_{tag}.png'))
