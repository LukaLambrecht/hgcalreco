import os
import sys
import numpy as np
from DataFormats.FWLite import Events, Handle


if __name__=='__main__':

    # read input file from command line
    inputfiles = sys.argv[1:]

    # loop over input files
    for file_idx, inputfile in enumerate(inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(inputfiles)}...')
        events = Events(inputfile)

        # loop over events
        for event_idx, event in enumerate(events):
            if (event_idx+1) % 1 == 0:
                print(f'Reading event {event_idx+1}...')
        
            # get collections
            lctocp_handle = Handle('edm::AssociationMap<edm::OneToManyWithQualityGeneric<vector<reco::CaloCluster>,vector<CaloParticle>,float,unsigned int,edm::RefProd<vector<reco::CaloCluster> >,edm::RefProd<vector<CaloParticle> >,edm::Ref<vector<reco::CaloCluster>,reco::CaloCluster,edm::refhelper::FindUsingAdvance<vector<reco::CaloCluster>,reco::CaloCluster> >,edm::Ref<vector<CaloParticle>,CaloParticle,edm::refhelper::FindUsingAdvance<vector<CaloParticle>,CaloParticle> > > >')
            event.getByLabel(("layerClusterCaloParticleAssociation", "", "RECO"), lctocp_handle)
            lctocp = lctocp_handle.product()

            # materialize the map first, before further getters
            # (attempt to fix segfaults)
            print('Reading map...')
            lctocpmap = []
            it = lctocp.begin()
            end = lctocp.end()
            while it != end:
                key = it.key
                vals = lctocp[key]
                tmp = []
                for val in vals:
                    cpref = val.first
                    score = val.second
                    tmp.append((cpref, score))
                lctocpmap.append((key, tmp))
                it.__preinc__()

            # check whether the layerclusters and matched caloparticles look consistent
            # note: still gives segmentation violations...
            #       probably the .get() method is fundamentally unusable in python FWLite
            #       for this AssociationMap object...
            #       can only use indices, not actual (references to) objects stored in this map,
            #       see test_associations_builtin.py, but that approach als has issues;
            #       nicely summarized by CG: "one crashes, the other appears reordered"...
            print('Getting objects...')
            for (lcref, cplist) in lctocpmap:
                for (cpref, score) in cplist:
                    lc = lcref.get()
                    cp = cpref.get()

