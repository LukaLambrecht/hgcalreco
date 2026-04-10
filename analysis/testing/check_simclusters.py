# Do some sanity checks.
# In particular, check simcluster hits and fractions and their energy.

# Conclusions so far:
# - CaloParticle energy matches sum of SimCluster energies.
# - The fractions per SimCluster do not add up to 1;
#   they are probably not the faction of SimCluster energy in that hit,
#   but the fraction of energy in that hit coming from this SimCluster.
# - In the overwhelming majority of cases, the fractions are 1.
#   (But maybe this changes with more crowded events and/or pileup.)


import os
import sys
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

        # loop over simclusters
        for cp in caloparticles:
            print('--- calo particle ---')
            print(cp.energy())
            sc_energy_sum = 0
            for sc_ref in cp.simClusters():
                sc = sc_ref.get()
                sc_energy_sum += sc.energy()
            print(len(cp.simClusters()), sc_energy_sum)
            for sc_ref in cp.simClusters():
                sc = sc_ref.get()
                fractions = []

                # loop over hits per simcluster
                hits = sc.hits_and_fractions()
                for hit in hits:
                    detid = hit.first
                    fraction = hit.second
                    fractions.append(fraction)
                #print(fractions)
                print(sum(fractions))
