# Run a sample production chain

import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.jobtools import get_cmssw
import tools.condortools as ct


if __name__=='__main__':

    # read command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-c', '--cmsdriver', required=True)
    parser.add_argument('-w', '--workdir', required=True)
    parser.add_argument('--tag', default=None)
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    args = parser.parse_args()

    # parse tag
    tagstr = '' if args.tag is None else f'_{args.tag}'

    # set CMSSW if provided
    cmssw = get_cmssw(args.cmssw, error_if_none=True)
    print(f'Found following CMSSW: {cmssw}')

    # read the cmsDriver command
    with open(args.cmsdriver) as f:
        lines = f.readlines()
    cmd = ' '.join([line.strip(' \\\n\t') for line in lines])

    # replace placeholders
    cmd = cmd.replace('FILEIN', os.path.abspath(args.inputfile))
    cmd = cmd.replace('FILEOUT', f'test.root')

    # get customization options that are already in the command (if any)
    customization = []
    tag = 'customise_commands'
    if f'--{tag}' in cmd:
        parts = cmd.split('--')
        idx = [idx for idx, part in enumerate(parts) if part.startswith(tag)][0]
        customization = [parts[idx].replace(tag, '').strip(';" \t\n')]
        parts.pop(idx)
        cmd = '--'.join(parts)

    # set output of the last step
    # note: this currently assumes the last step is MiniAOD level,
    #       maybe later try to generalize.
    output_mode = "hgcal" # choose from "full" or "hgcal", maybe later add as argument

    # option 1: keep everything
    # note: keeping literally everything does not work yet, gives weird CMSSW errors hard to interpret.
    #       maybe it's because the process name is expected to be RECO, while here HGCALTICL is used?
    #       either need to go slightly more specific (see similar case in sample production),
    #       but probably not even needed here; output mode "hgcal" should be good enough.
    # note: another option to make this work seems to be to drop the PAT step from the cmsRun config.
    #       runs in principle, but is very slow and produces huge output files,
    #       only use when really needed (else just use output mode "hgcal", with or without PAT step).
    if output_mode == "full":
        customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_*_*_*\')')

    # option 2: minimal content
    # note: do not use *_*_*_HGCALTICL (keep everything for this process),
    #       as it crashes with the same error as when trying to keep all output (see above).
    #       either go more specific (see below, preferred option), or drop the PAT step from the cmsRun config.
    elif output_mode == "hgcal":
        drop = [
            '*_*_*_*'
        ]
        keep = [
            # add reco-level objects of interest
            '*_hgcalDigis_*_HGCALTICL',
            '*_HGCalUncalibRecHit_*_HGCALTICL',
            '*_HGCalRecHit_*_HGCALTICL',
            '*_hgcalMergeLayerClusters_*_HGCALTICL',
            '*_ticlTracksters*_*_HGCALTICL',
            # add gen-level objects of interest
            '*GenParticle*_*_*_*',
            '*TrackingParticle*_*_*_*',
            '*TrackingVertex*_*_*_*',
            '*SimTrack*_*_*_*',
            '*CaloParticle*_*_*_*',
            '*SimCluster*_*_*_*',
            '*CaloHit*_*_*_*',
            # add links and associations
            '*_layerClusterCaloParticleAssociation_*_HGCALTICL',
            '*_layerClusterSimClusterAssociation_*_HGCALTICL'
        ]
        for collection in drop:
            customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'drop {collection}\')')
        for collection in keep:
            customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'keep {collection}\')')
    
    else:
        msg = f'Output mode "{output_mode}" not recognized.'
        raise Exception(msg)

    # others: to do as the need arises

    # (re-)add customization to command
    if len(customization)>0:
        customizationstr = '; '.join(customization)
        cmd += f' --{tag} "{customizationstr}"'

    # to continue here, just placeholder
    print(cmd)
    os.system(cmd) 
