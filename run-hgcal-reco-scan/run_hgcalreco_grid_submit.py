import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
thisdir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(topdir)

from tools.gridtools import get_grid_points
from tools.jobtools import get_cmssw
import tools.condortools as ct


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-g', '--grid', required=True)
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='auto')
    parser.add_argument('--tag', default='auto')
    parser.add_argument('--config', default=os.path.join(thisdir, 'configs/hgcalreco_cff_template.py'))
    parser.add_argument('--globaltag', default='auto:phase2_realistic_T35')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D121')
    parser.add_argument('--efficiency_level', default='both',
        choices=['lc', 'tc', 'both'],
        help='Efficiency metrics to calculate after re-reco.')
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--overwrite', default=False, action='store_true')
    parser.add_argument('--submit', default=False, action='store_true')
    args = parser.parse_args()

    # parse tag
    if args.tag == 'auto': args.tag = os.path.basename(args.grid).replace('.json', '')

    # parse working directory
    if args.workdir == 'auto': args.workdir = os.path.abspath(f'output_{args.tag}')
    else: args.workdir = os.path.abspath(args.workdir)

    # get CMSSW if provided
    cmssw = get_cmssw(args.cmssw, error_if_none=True)
    print(f'Found following CMSSW: {cmssw}')

    # check input file existence
    for idx, inputfile in enumerate(args.inputfiles):
        if inputfile.startswith('root:'): pass # exception for remote files
        else:
            inputfile = os.path.abspath(inputfile) # important for CMSSW, cannot read relative paths
            if not os.path.exists(inputfile):
                raise Exception(f'Input file {inputfile} does not exist.')
            args.inputfiles[idx] = inputfile
    
    # check config template file existence
    if not os.path.exists(args.config):
        raise Exception(f'Template config {args.config} does not exist.')

    # read grid
    with open(args.grid, 'r') as f:
        grid = json.load(f)

    # make working directory
    if os.path.exists(args.workdir) and not args.overwrite:
        raise Exception(f'Working directory {args.workdir} already exists.')
    if not os.path.exists(args.workdir):
        os.makedirs(args.workdir)

    # make full context
    # (shared between all jobs)
    context = {
        "topdir": topdir,
        "template": args.config,
        "inputfiles": args.inputfiles,
        "max_events": args.max_events,
        "globaltag": args.globaltag,
        "geometry": args.geometry,
        "efficiency_script": os.path.join(topdir, 'analysis/efficiency/calculate_associations.py'),
        "efficiency_config_type": "customreco",
        "efficiency_level": args.efficiency_level,
        "efficiency_recalculate": False
    }

    # loop over all grid points
    exes = []
    gridpoints = get_grid_points(grid)
    for jobidx, gridpoint in enumerate(gridpoints):
        
        # make job directory
        jobdir = os.path.join(args.workdir, f'job{jobidx}')
        if not os.path.exists(jobdir): os.makedirs(jobdir)

        # copy script to run to job directory
        cmd = f'cp {os.path.join(thisdir, "templates", "run_hgcalreco.py")} {jobdir}'
        os.system(cmd)

        # write context to job directory
        context["workdir"] = jobdir
        context_file = os.path.join(jobdir, "context.json")
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)

        # write parameters to job directory
        param_file = os.path.join(jobdir, "params.json")
        with open(param_file, 'w') as f:
            json.dump(gridpoint, f, indent=2)
        
        # make job script
        jobscript = os.path.abspath(f'cjob_run_{args.tag}_{jobidx}.sh')
        ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
        with open(jobscript, 'a') as f:
            # go to working directory
            f.write(f'cd {jobdir}\n')
            # write actual commands to run
            f.write('python3 run_hgcalreco.py params.json context.json\n')
        exes.append(jobscript)

    # make job description
    name = f'cjob_run_{args.tag}'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    ct.makeJobDescription(jobdescriptor, '$(script)', doqueue=False,
        proxy=args.proxy, jobflavour='workday')
    with open(jobdescriptor, 'a') as f:
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')

    # print output (and submit jobs if requested)
    print(f'Job working directory {args.workdir} has been prepared.')
    if args.submit: os.system(f'condor_submit {jobdescriptor}')
    else: print(f'Check if everything looks fine, then run condor_submit {jobdescriptor} to submit the jobs.')
