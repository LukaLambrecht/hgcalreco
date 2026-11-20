import os
import sys
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)
from tools.hgcalrecotools import build_config


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='.')
    parser.add_argument('--template', default='configs/hgcalreco_cff_template.py')
    parser.add_argument('--globaltag', default='auto:phase2_realistic_T35')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D127')
    parser.add_argument('--era', default='Phase2C26I13M9',
        help='CMSSW era name (e.g. "Phase2C26I13M9" for D122/D127, "Phase2C22I13M9" for D121).'
             ' Must match the era used for sample production, similar to --geometry.')
    parser.add_argument('--modifiers', default=None)
    parser.add_argument('--calo_truth', default=False, action='store_true',
        help='Also run the CaloParticle/SimCluster-based truth associations (and store CaloParticles,'
             ' SimClusters and SimTracksters in the output); off by default, since the default truth'
             ' reference is the MC-truth graph.')
    parser.add_argument('--no_exec', default=False, action='store_true')
    args = parser.parse_args()

    # check file existence
    for inputfile in args.inputfiles:
        if not os.path.exists(inputfile):
            if inputfile.startswith('root:'): pass # exception for remote files
            else: raise Exception(f'Input file {inputfile} does not exist.')
    if not os.path.exists(args.template):
        raise Exception(f'Template config {args.template} does not exist.')

    # read template
    with open(args.template, 'r') as f:
        template = f.read()

    # read modifiers
    modifier = None
    if args.modifiers is not None:
        with open(args.modifiers, 'r') as f:
            modifier = f.read()

    # fill the template
    # (same function as used in the grid scans in run-hgcal-reco-scan, to keep both in sync)
    context = {
        "inputfiles": args.inputfiles,
        "max_events": args.max_events,
        "globaltag": args.globaltag,
        "geometry": args.geometry,
        "era": args.era,
        "calo_truth": args.calo_truth,
    }
    config = build_config(template, {}, context, extra_modifiers=modifier)

    # make working directory
    if not os.path.exists(args.workdir):
        os.makedirs(args.workdir)

    # write config
    cffile = os.path.basename(args.template).replace('_template', '')
    cffile = os.path.join(args.workdir, cffile)
    with open(cffile, 'w') as f:
        f.write(config)

    # stop here if no execution is needed
    if args.no_exec: sys.exit()

    # run config
    cffilebase = os.path.basename(cffile)
    cmd = f'cd {args.workdir} && cmsRun {cffilebase}'
    os.system(cmd)
