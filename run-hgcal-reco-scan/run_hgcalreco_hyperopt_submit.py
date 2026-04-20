import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

import tools.condortools as ct
from run_hgcalreco_grid_submit import get_cmssw


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-g', '--grid', required=True)
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='auto')
    parser.add_argument('--tag', default='auto')
    parser.add_argument('--template', default=os.path.abspath('templates/hgcalreco_cff_template.py'))
    parser.add_argument('--globaltag', default='150X_mcRun4_realistic_v1')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D121')
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--submit', default=False, action='store_true')
    args = parser.parse_args()

    # parse tag
    if args.tag == 'auto': args.tag = os.path.basename(args.grid).replace('.json', '')

    # parse working directory
    if args.workdir == 'auto': args.workdir = os.path.abspath(f'output_{args.tag}')
    else: args.workdir = os.path.abspath(args.workdir)

    # get CMSSW if provided
    cmssw = get_cmssw(args)
    print(f'Found following CMSSW: {cmssw}')

    # check input file existence
    if args.inputfile.startswith('root:'): pass # exception for remote files
    else:
        args.inputfile = os.path.abspath(args.inputfile) # important for CMSSW, cannot read relative paths
        if not os.path.exists(args.inputfile):
            raise Exception(f'Input file {args.inputfile} does not exist.')
    
    # check template file existence
    if not os.path.exists(args.template):
        raise Exception(f'Template config {args.template} does not exist.')

    # read grid
    with open(args.grid, 'r') as f:
        grid = json.load(f)

    # make working directory
    if os.path.exists(args.workdir):
        raise Exception(f'Working directory {args.workdir} already exists.')
    os.makedirs(args.workdir)

    # make full context
    context = {
        "template": args.template,
        "inputfile": args.inputfile,
        "max_events": args.max_events,
        "globaltag": args.globaltag,
        "geometry": args.geometry,
        "efficiency_script": os.path.join(topdir, 'analysis/efficiency/calculate_associations.py'),
        "efficiency_config": os.path.join(topdir, 'analysis/configs/input_config_customreco.json'),
    }

    # write all required files to working directory
    cmd = f'cp templates/run_hgcalreco_hyperopt.py {args.workdir}'
    os.system(cmd)
    cmd = f'cp {args.grid} {os.path.join(args.workdir, "grid.json")}'
    os.system(cmd)
    context["workdir"] = args.workdir
    context_file = os.path.join(args.workdir, "context.json")
    with open(context_file, 'w') as f:
        json.dump(context, f, indent=2)
    
    # make job script
    jobscript = os.path.abspath(f'cjob_run_{args.tag}.sh')
    ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
    with open(jobscript, 'a') as f:
        # go to working directory
        f.write(f'cd {args.workdir}\n')
        # write actual commands to run
        f.write('python3 run_hgcalreco_hyperopt.py grid.json context.json\n')

    # make job description
    name = f'cjob_run_{args.tag}'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    ct.makeJobDescription(jobdescriptor, '$(script)', doqueue=False,
        proxy=args.proxy, jobflavour='workday')
    exes = [jobscript]
    with open(jobdescriptor, 'a') as f:
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')

    # print output (and submit jobs if requested)
    print(f'Job working directory {args.workdir} has been prepared.')
    if args.submit: os.system(f'condor_submit {jobdescriptor}')
    else: print(f'Check if everything looks fine, then run condor_submit {jobdescriptor} to submit the jobs.')
