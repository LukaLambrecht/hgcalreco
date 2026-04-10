# Do some sanity checks.
# In particular: check overlap between detector IDs for RecHits and CaloHits,
# and check if their reported energies are the same.

# Conclusions (so far):
# - There are O(10) times more RecHits than CaloHits.
#   Is this just electronics noise? Maybe cross-talk between neighbouring cells?
# - Most CaloHits (60-90%) seem to have a match in the collection of RecHits,
#   but obviously not the other way around.
# - Even for the ones that match, the energy is vastly different,
#   probably completely different quantities and/or units;
#   can definitely not compare directly to each other.


import os
import sys
import numpy as np
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config_centralreco.json')

    # read events
    events = Events(inputfile)
    reader = Reader(input_config)

    # initialize counters
    nevents = 0
    ncp = 0
    nlc = 0

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

        # check overlap between detids between calohits and rechits
        calohit_ids = np.array(list(calohit_map.keys()))
        rechit_ids = np.array(list(rechit_map.keys()))
        both_ids = np.intersect1d(calohit_ids, rechit_ids)
        print(len(calohit_ids))
        print(len(rechit_ids))
        print(len(both_ids))
        print(len(both_ids)/len(calohit_ids))

        # check energy of common detids
        test_id = both_ids[0]
        print(calohit_map[test_id].energy())
        print(rechit_map[test_id].energy())
