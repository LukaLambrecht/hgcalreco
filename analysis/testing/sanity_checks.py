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
    input_config = os.path.join(topdir, 'configs/input_config_customreco.json')

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

        # sanity check for calo particles:
        # check that the sum of energies of associated sim clusters is equal to the calo particle energy.
        # note: the sum of sim hits can be a lot smaller, as sim hits are only produced in sensitive material
        #       (while sim clusters contain the full energy, including that deposited in absorbers).
        #       [to double check]
        print('Checking calo particles...')
        for cp_idx, cp in enumerate(caloparticles):
            ncp += 1

            cp_energy = cp.energy()
            clusters_energy_sum = 0
            hits_energy_sum = 0

            simcluster_refs = cp.simClusters()
            for sc_ref in simcluster_refs:
                sc = sc_ref.get()
                clusters_energy_sum += sc.energy()

                # the sum of calohit energies does not need to match (see above),
                # but at least we check that all calohits are found in the mapping.
                # update: check if the same holds for rechits as well
                #         -> it does not; many detids are not found in the map of rechits.
                for hf in sc.hits_and_fractions():
                    detid = hf.first
                    fraction = hf.second
                    if detid in calohit_map.keys(): hits_energy_sum += calohit_map[detid].energy() * fraction
                    else: print('WARNING: calohit not found')
                    if detid in rechit_map.keys(): pass
                    #else:
                    #    print('WARNING: rechit not found')

            difference = abs(cp_energy - clusters_energy_sum) / cp_energy
            if difference > 0.05:
                msg = f'WARNING: CaloParticle energy: {cp_energy}'
                msg += f' vs. sum of SimCluster energies: {clusters_energy_sum}'
                msg += f' vs. sum of CaloHit energies: {hits_energy_sum}'
                print(msg)

        # sanity check for layer clusters:
        # check that the sum of energies of associated hits is equal to the cluster energy.
        print('Checking layer clusters...')
        for lc_idx, lc in enumerate(layerclusters):
            nlc += 1

            lc_energy = lc.energy()
            hits_energy_sum = 0

            for hf in lc.hitsAndFractions():
                # note: fraction is not the energy fraction of this hit in this layercluster,
                #       but the assignment fraction of this hit to this layercluster
                #       (always 1 for hgcal as hits are only assigned to one cluster).
                detid = hf.first
                fraction = hf.second

                if detid in rechit_map.keys(): hits_energy_sum += rechit_map[detid].energy() * fraction
                else: print('WARNING: rechit not found')

            difference = abs(lc_energy - hits_energy_sum) / lc_energy
            if difference > 0.05:
                msg = f'WARNING: LayerCluster energy: {lc_energy}'
                msg += ' vs. sum of RecHit energies: {hits_energy_sum}'
                print(msg)

        # sanity check for calo particles and tracksters:
        # there should be about one trackster per calo particle
        # note: their energies are not expected to match, because the trackster just contains layer clusters
        #       in the active material, while energy deposited in the absorbers is not recorded.
        # note: can compare direction intead, but tracksters do not have precomputed eta and phi;
        #       instead, need to calculate them from energy-weighted layercluster positions.
        #       maybe later, probably a bit of an overkill for now.
        # note: some calo particles do not have tracksters, but it seems to be ok because they are at low abs(eta),
        #       i.e. outside the HGCAL acceptance.
        # note: there seem to be many tracksters per calo particle (in acceptance);
        #       probably expected as the tracksters are not yet merged.
        print('Checking calo particle to trackster association...')
        if len(caloparticles) > 0:
            for cp in caloparticles: print(f'CaloParticle: {cp.eta()}, {cp.phi()}')
        if len(tracksters) > 0: print(f'{len(tracksters)} trackster present!')

    # printouts
    print(f'Processed {nevents} events.')
    print(f'Processed {ncp} CaloParticles.')
    print(f'Processed {nlc} LayerClusters.')
