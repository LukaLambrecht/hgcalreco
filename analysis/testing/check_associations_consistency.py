# Check if built-in and custom associations are consistent

import os
import sys
import numpy as np
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.associationtools import get_associations
from tools.associationtools import get_cptolc_matrix, get_lctocp_matrix
from tools.associationtools import get_cptolc_matrix_from_builtin
from tools.associationtools import get_lctocp_matrix_from_builtin
from tools.associationtools import get_mapping
from tools.geometrytools import get_layercluster_layer


if __name__=='__main__':

    # read input file from command line
    inputfiles = sys.argv[1:]

    # other settings (hard-coded for now)
    input_configs = [
        os.path.join(topdir, 'configs/input_config_customreco_baseline.json'),
        os.path.join(topdir, 'configs/input_config_customreco_hits.json'),
        os.path.join(topdir, 'configs/input_config_customreco_associations.json')
    ]

    # initialize reader
    reader = Reader(input_configs)

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
            #cptolc = collections['cptolcassociation'] # not yet implemented
            lctocp_lcidx = collections['lctocpassociation_lcids']
            lctocp_cpidx = collections['lctocpassociation_cpids']
            lctocp_score = collections['lctocpassociation_scores']

            # make dicts mapping ID to object
            calohit_map = {hit.id(): hit for hit in calohits_ee}
            calohit_map.update({hit.id(): hit for hit in calohits_heb})
            calohit_map.update({hit.id(): hit for hit in calohits_hef})
            rechit_map = {hit.id(): hit for hit in rechits_ee}
            rechit_map.update({hit.id(): hit for hit in rechits_heb})
            rechit_map.update({hit.id(): hit for hit in rechits_hef})

            # get builtin associations
            pur_builtin = get_lctocp_matrix_from_builtin(lctocp_lcidx, lctocp_cpidx, lctocp_score, len(layerclusters), len(caloparticles))
            mapping_builtin = get_mapping(pur_builtin)
            cp_ids_builtin = mapping_builtin[1]

            # calculate associations
            associations = get_associations(caloparticles, calohit_map, layerclusters, rechit_map)
            #eff = get_cptolc_matrix(associations)
            pur = get_lctocp_matrix(associations)
            mapping = get_mapping(pur)
            cp_ids = mapping[1]

            # check if mapping is the same
            diff = (cp_ids_builtin != cp_ids).astype(bool)
            if diff.any():
                ndiff = np.sum(diff.astype(int))
                msg = f'WARNING: different mapping found (for {ndiff} / {len(diff)} LC).'
                print(msg)

                # print an example
                firstdiff = np.where(diff)[0][0]
                print(firstdiff)
                firstdiff = int(firstdiff)
                lc = layerclusters[firstdiff]
                print('Builtin: ', pur_builtin[:,firstdiff], ' -> ', cp_ids_builtin[firstdiff])
                print('Custom: ', pur[:,firstdiff], ' -> ', cp_ids[firstdiff])
                print('Layer: ', get_layercluster_layer(lc))
                print('CP[0] eta: ', caloparticles[0].eta())
                print('CP[1] eta: ', caloparticles[1].eta())

            # do some printouts
            print(pur_builtin[:, :10])
            print(pur[:, :10])
            print('---')

            #if event_idx >= 10: break
