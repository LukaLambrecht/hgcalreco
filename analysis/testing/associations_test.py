import os
import sys
import numpy as np
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.associationtools import get_associations
from tools.associationtools import get_cptolc_matrix, get_lctocp_matrix


if __name__=='__main__':

    # read input file from command line
    inputfiles = sys.argv[1:]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config.json')

    # initialize reader
    reader = Reader(input_config)

    # loop over input files
    for file_idx, inputfile in enumerate(inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(inputfiles)}...')
        events = Events(inputfile)

        # loop over events
        for event_idx, event in enumerate(events):
            if (event_idx+1) % 10 == 0:
                print(f'Reading event {event_idx+1}...', end='\r')
        
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
            rechit_map = {hit.id(): hit for hit in rechits_ee}
            rechit_map.update({hit.id(): hit for hit in rechits_heb})
            rechit_map.update({hit.id(): hit for hit in rechits_hef})

            # do some event selection
            if len(caloparticles) < 2: continue
            if len(tracksters) < 1: continue

            # loop over calo particles and layer clusters
            print(f'--- Event with {len(caloparticles)} calo particles and {len(layerclusters)} layer clusters ---')
            associations = get_associations(caloparticles, calohit_map, layerclusters, rechit_map)
            print('Efficiency:')
            eff = get_cptolc_matrix(associations)
            print(np.transpose(eff))
            print('Purity:')
            pur = get_lctocp_matrix(associations)
            print(np.transpose(pur))
            sys.exit()
