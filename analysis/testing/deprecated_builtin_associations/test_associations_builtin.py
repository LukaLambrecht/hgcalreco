import os
import sys
import numpy as np
from DataFormats.FWLite import Events, Handle

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


if __name__=='__main__':

    # read input file from command line
    inputfiles = sys.argv[1:]

    # other settings (hard-coded for now)
    recotype = 'centralreco'
    input_configs = [
        os.path.join(topdir, f'configs/input_config_{recotype}_baseline.json'),
        os.path.join(topdir, f'configs/input_config_{recotype}_associations.json')
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
            tracksters = collections['tracksters']
            layerclusters = collections['layerclusters']
            cptolc = collections['cptolcassociation']
            lctocp = collections['lctocpassociation']

            # print sizes and check with collections of objects
            print('--- Sizes of collections ---')
            #print(cptolc)
            print(cptolc.size())
            print(caloparticles.size())
            #print(lctocp)
            print(lctocp.size())
            print(layerclusters.size())

            # check whether order in map correspond to indices in object list
            # -> seems to be the case in most events, but not all, cannot rely on it...
            #    actually, differences only seem to occur in rare events where the size
            #    of layerclusters is slightly different from the size of lctocp;
            #    not yet sure what is causing that.
            '''print('--- Order of calo particles ---')
            cp_keys = cptolc.keys()
            ratios = np.array([cp1.eta()/cp2.eta() for cp1, cp2 in zip(cp_keys, caloparticles)])
            diff = (ratios!=1)
            if diff.any(): print(np.sum(diff), len(diff), ratios)
            print('--- Order of the layer clusters ---')
            lc_keys = lctocp.keys()
            ratios = np.array([lc1.eta()/lc2.eta() for lc1, lc2 in zip(lc_keys, layerclusters)])
            diff = (ratios!=1)
            if diff.any(): print(np.sum(diff), len(diff), ratios)'''

            # check whether the indices stored in lctocp correspond to the indices
            # in the layercluster object list
            # -> no, strong mismatches in sign of eta, ordering/indexing not yet correct,
            #    or can simply not be done this way...
            it = lctocp.begin()
            end = lctocp.end()
            i = 0
            while it != end:
                key = it.key
                lcidx = key.index()
                lckey = key.key()
                try: lc = key.get()
                except: lc = None
                if lcidx != lckey: print('WARNING: LC idx != key')
                if lcidx >= len(layerclusters): print('WARNING: LC idx > len'); lcidx_eta = 0
                else: lcidx_eta = layerclusters[lcidx].eta()
                if lckey >= len(layerclusters): print('WARNING: LC key > len'); lckey_eta = 0
                else: lckey_eta = layerclusters[lckey].eta()
                if lc is not None: lc_eta = lc.eta()
                else: lc_eta = 0
                if lc_eta != lcidx_eta: print('WARNING: LC eta does not match')
                values = lctocp[key]
                for j, val in enumerate(values):
                    cpidx = val.first.index()
                    cpkey = val.first.key()
                    cp = val.first.get()
                    if cpidx != cpkey: print('WARNING: CP idx != key')
                    if cpidx >= len(caloparticles): print('WARNING: CP idx > len'); cpidx_eta = 0
                    else: cpidx_eta = caloparticles[cpidx].eta()
                    if cpkey >= len(caloparticles): print('WARNING: CP key > len'); cpkey_eta = 0
                    else: cpkey_eta = caloparticles[cpkey].eta()
                    if cp is not None: cp_eta = cp.eta()
                    else: cp_eta = 0
                    if cp_eta != cpidx_eta: print('WARNING: CP eta does not match')
                    if cpkey_eta*lckey_eta < 0:
                        print('WARNING: CP and LC eta do not match')
                        print(cpkey_eta, lckey_eta, val.second)
                i += 1
                it.__preinc__()
            continue

            # loop over cp-to-lc map to test score retrieval
            it = cptolc.begin()
            end = cptolc.end()
            i = 0
            while it != end:
                key = it.key
                cpidx = key.index()
                values = cptolc[key]
                for j, val in enumerate(values):
                    lcidx = val.first.index()
                    quality = val.second
                    score1 = quality.first
                    score2 = quality.second
                    print(f'  - CP {cpidx} to LC {lcidx}: {score1}, {score2}')
                    if j >= 9:
                        print('  - [...]')
                        break
                if i >= 9:
                    print('  - [...]')
                    break
                i += 1
                it.__preinc__()
            print('---')

            # loop over lc-to-cp map to test score retrieval
            it = lctocp.begin()
            end = lctocp.end()
            i = 0
            while it != end:
                key = it.key
                lcidx = key.index()
                values = lctocp[key]
                for j, val in enumerate(values):
                    cpidx = val.first.index()
                    score = val.second
                    print(f'  - LC {lcidx} to CP {cpidx}: {score}')
                    if j >= 9:
                        print('  - [...]')
                        break
                #if i >= 9:
                #    print('  - [...]')
                #    break
                i += 1
                it.__preinc__()
            sys.exit()
