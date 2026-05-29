# Do some sanity checks.

# In particular: check distribution of RecHit energies per layer.


import os
import sys
import argparse
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.geometrytools import get_detid_layer
from tools.geometrytools import get_detid_subdetid
from tools.geometrytools import get_detid_silicon_thickness
from tools.layertools import get_quantity_per_layer


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-c', '--configs', nargs='+',
        default = [
            os.path.join(topdir, 'configs/input_config_centralreco_baseline.json'),
            os.path.join(topdir, 'configs/input_config_centralreco_hits.json'),
        ]
    )
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    parser.add_argument('-o', '--outputdir', default='output_plots_rechit_energy')
    parser.add_argument('--filter-by-layercluster', default=False, action='store_true')
    args = parser.parse_args()

    # read events
    events = Events(args.inputfiles)
    reader = Reader(args.configs)

    # initialize counters
    nevents = 0

    # initializations
    rechit_energy = []
    rechit_layer = []
    rechit_subdet = []
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

        # optional: take only rechits that are clustered in layer clusters
        if args.filter_by_layercluster:
            layercluster_rechit_ids = []
            for layercluster in layerclusters:
                layercluster_rechit_ids += [el.first.rawId() for el in layercluster.hitsAndFractions()]
            rechit_map = {key: val for key, val in rechit_map.items() if key in layercluster_rechit_ids}

        # get layers, subdetectors, thicknesses, and energy of calohits and rechits
        calohit_ids = np.array(list(calohit_map.keys()))
        rechit_ids = np.array(list(rechit_map.keys()))
        rechit_layer.append( np.array([get_detid_layer(int(detid)) for detid in rechit_ids]) )
        rechit_subdet.append( np.array([get_detid_subdetid(int(detid)) for detid in rechit_ids]) )
        rechit_thickness.append( np.array([get_detid_silicon_thickness(int(detid)) for detid in rechit_ids]) )
        rechit_energy.append( np.array([rechit_map[detid].energy() for detid in rechit_ids]) )

        if args.nevents > 0 and nevents >= args.nevents: break

    # concatenate
    rechit_layer = np.concatenate(rechit_layer)
    rechit_subdet = np.concatenate(rechit_subdet)
    rechit_thickness = np.concatenate(rechit_thickness)
    rechit_energy = np.concatenate(rechit_energy)

    # make masks for subdetectors
    subdet_masks = {
        'all': np.ones(len(rechit_subdet)).astype(bool),
        'EE': (rechit_subdet==0).astype(bool),
        'HSi': (rechit_subdet==1).astype(bool),
        'HSci': (rechit_subdet==2).astype(bool),
    }

    # make masks for thicknesses
    thickness_masks = {
        'all': np.ones(len(rechit_thickness)).astype(bool),
        'thin': (rechit_thickness==0).astype(bool),
        'medium': (rechit_thickness==1).astype(bool),
        'thick': (rechit_thickness==2).astype(bool),
    }

    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    # loop over subdetectors and thicknesses
    for subdet_key, subdet_mask in subdet_masks.items():
        for thickness_key, thickness_mask in thickness_masks.items():
            mask = ((subdet_mask) & (thickness_mask))
            tag = f'{subdet_key}_{thickness_key}'

            # skip some combinations that don't make sense
            #if thickness_key!='all' and subdet_key not in ['EE', 'HSi']: continue

            # divide energy per layer
            xax = np.arange(1, 48)
            rechit_energy_per_layer = get_quantity_per_layer(rechit_energy[mask], rechit_layer[mask], keys=xax, absolute=True)

            # make text to write in plot
            text = f'Subdetector: {subdet_key}'
            if thickness_key!='all': text += f'\nSi thickness: {thickness_key}'
    
            # make a plot of rechit energy distribution
            fig, ax = plt.subplots(figsize=(8,6))
            cmap = plt.get_cmap('jet')
            bins = np.linspace(0, 1, num=50)
            legend_labels = []
            legend_entries = []
            for idx, (key, val) in enumerate(rechit_energy_per_layer.items()):
                color = cmap(idx/len(rechit_energy_per_layer))
                if ((key-1) % 2) == 0:
                    legend_labels.append(f'Layer {key}')
                    legend_entries.append(Line2D([0], [0], color=color, linewidth=4))
                ax.hist(val, bins=bins, histtype='step',
                        linewidth = 2,
                        color = color
                )
            ax.set_xlabel('Energy', fontsize=12)
            ax.set_ylabel('Number of hits', fontsize=12)
            ax.legend(legend_entries, legend_labels, loc='upper left', bbox_to_anchor=(1.02, 1))
            ax.text(0.99, 0.99, text, ha='right', va='top', fontsize=12, transform=ax.transAxes)
            fig.tight_layout()
            fig.savefig(os.path.join(args.outputdir, f'test_{tag}.png'))
            ax.set_yscale('log')
            fig.savefig(os.path.join(args.outputdir, f'test_{tag}_log.png'))
    
            # make a plot of normalized rechit energy distribution
            fig, ax = plt.subplots(figsize=(8,6))
            for idx, (key, val) in enumerate(rechit_energy_per_layer.items()):
                label = f'Layer {key}' if ((key-1) % 2) == 0 else None
                ax.hist(val, bins=bins, density=True, histtype='step',
                        linewidth = 2,
                        color=cmap(idx/len(rechit_energy_per_layer))
                )
            ax.set_xlabel('Energy', fontsize=12)
            ax.set_ylabel('Number of hits (normalized)', fontsize=12)
            ax.legend(legend_entries, legend_labels, loc='upper left', bbox_to_anchor=(1.02, 1))
            ax.text(0.99, 0.99, text, ha='right', va='top', fontsize=12, transform=ax.transAxes)
            fig.tight_layout()
            fig.savefig(os.path.join(args.outputdir, f'test_{tag}_normalized.png'))
            ax.set_yscale('log')
            fig.savefig(os.path.join(args.outputdir, f'test_{tag}_normalized_log.png'))

            plt.close()
