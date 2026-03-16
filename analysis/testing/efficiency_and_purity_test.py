import os
import sys
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader
from tools.efficiencytools import efficiency


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config.json')

    # read events
    events = Events(inputfile)
    reader = Reader(input_config)

    for event in events:

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
        if len(caloparticles) != 2: continue
        if len(tracksters) < 2: continue

        # loop over calo particles and layer clusters
        print(f'--- Event with {len(caloparticles)} calo particles and {len(layerclusters)} layer clusters ---')
        for caloparticle in caloparticles:
            for layercluster in layerclusters:
                print(efficiency(caloparticle, calohit_map, layercluster, rechit_map))
