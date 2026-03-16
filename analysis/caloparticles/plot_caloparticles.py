import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


if __name__=='__main__':

    # read input file from command line
    inputfiles = sys.argv[1:]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config.json')
    outputdir = 'output_plots3'

    # initialize reader
    reader = Reader(input_config)

    # initialize variables
    varnames = [
        'event_ncp',
        'cp_nsc',
        'cp_ncalohits',
        'cp_pt',
        'cp_eta',
        'cp_phi'
    ]
    varmap = {varname: [] for varname in varnames}

    # loop over input files
    for file_idx, inputfile in enumerate(inputfiles):
        print(f'Reading events from file {file_idx+1} / {len(inputfiles)}...')
        events = Events(inputfile)
    
        # loop over event
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

            # object and event selection
            if len(caloparticles) < 2: continue
            selected_caloparticles = []
            for caloparticle in caloparticles:
                nch = 0
                for sc_ref in caloparticle.simClusters():
                    sc = sc_ref.get()
                    nch += len(sc.hits_and_fractions())
                if nch > 10: selected_caloparticles.append(caloparticle)
            if len(selected_caloparticles) < 2: continue

            # fill event variables
            varmap['event_ncp'].append(len(caloparticles))

            # loop over caloparticles
            for caloparticle in selected_caloparticles:

                # fill caloparticle variables
                varmap['cp_nsc'].append(len(caloparticle.simClusters()))
                nch = 0
                for sc_ref in caloparticle.simClusters():
                    sc = sc_ref.get()
                    nch += len(sc.hits_and_fractions())
                varmap['cp_ncalohits'].append(nch)
                varmap['cp_pt'].append(caloparticle.pt())
                varmap['cp_eta'].append(caloparticle.eta())
                varmap['cp_phi'].append(caloparticle.phi())

    # define plot settings
    variable_settings = {
        'event_ncp': {
            'yaxtitle': 'Events',
            'xaxtitle': 'Number of CaloParticles per event',
            'bins': np.linspace(-0.5, 3.5, num=5)
        },
        'cp_nsc': {
            'yaxtitle': 'CaloParticles',
            'xaxtitle': 'Number of SimClusters per CaloParticle'
        },
        'cp_ncalohits': {
            'yaxtitle': 'CaloParticles',
            'xaxtitle': 'Number of CaloHits per CaloParticle'
        },
        'cp_pt': {
            'yaxtitle': 'CaloParticles',
            'xaxtitle': 'CaloParticle pT'
        },
        'cp_eta': {
            'yaxtitle': 'CaloParticles',
            'xaxtitle': 'CaloParticle eta'
        },
        'cp_phi': {
            'yaxtitle': 'CaloParticles',
            'xaxtitle': 'CaloParticle phi'
        }
    }

    # convert everything to arrays
    for varname, varvalues in varmap.items():
        varmap[varname] = np.array(varvalues)

    # make output directory
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # make plots
    for varname, varvalues in varmap.items():
        
        # get variable settings
        settings = variable_settings.get(varname, {})
        bins = settings.get('bins', None)
        if bins is None: bins = np.linspace(np.amin(varvalues), np.amax(varvalues), num=31)
        xaxtitle = settings.get('xaxtitle', varname)
        yaxtitle = settings.get('yaxtitle', 'Instances')
        
        # make histogram
        hist = np.histogram(varvalues, bins=bins)[0]
        errors = np.sqrt(hist)

        # make plot
        fig, ax = plt.subplots()
        ax.stairs(hist, edges=bins, linewidth=2, color='dodgerblue')
        ax.stairs(hist+errors, baseline=hist-errors, edges=bins,
            fill=True, color='dodgerblue', alpha=0.2)

        # plot aesthetics
        ax.set_ylabel(yaxtitle, fontsize=12)
        ax.set_xlabel(xaxtitle, fontsize=12)
        ax.grid(which='both', axis='both')

        # save figure
        fig.tight_layout()
        outputfile = os.path.join(outputdir, varname+'.png')
        fig.savefig(outputfile)

        # same with log scale
        ax.set_yscale('log')
        fig.tight_layout()
        outputfile = os.path.join(outputdir, varname+'_log.png')
        fig.savefig(outputfile)

        # close figures to save memory
        plt.close()
