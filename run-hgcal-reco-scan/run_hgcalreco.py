import os
import sys
import json
import itertools
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

import tools.condortools as ct


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-g', '--grid', required=True)
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='auto')
    parser.add_argument('--tag', default='auto')
    parser.add_argument('--template', default='templates/hgcalreco_cff_template.py')
    parser.add_argument('--globaltag', default='150X_mcRun4_realistic_v1')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D121')
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--submit', default=False, action='store_true')
    args = parser.parse_args()

    # parse tag
    if args.tag == 'auto': args.tag = os.path.basename(args.grid).replace('.json', '')

    # parse working directory
    if args.workdir == 'auto': args.workdir = f'output_{args.tag}'

    # set CMSSW if provided
    # priority:
    # - command line arg
    # - environment
    cmssw = None
    envcmssw = os.getenv('CMSSW_BASE')
    if args.cmssw is not None:
        cmssw = os.path.abspath(cmssw)
        if not os.path.exists(cmssw):
            raise Exception(f'Provided CMSSW {cmssw} does not exist.')
        if envcmssw is not None and envcmssw!=cmssw:
            msg = 'WARNING: provided CMSSW {cmssw} is different from current environment CMSSW {envcmssw}.'
            print(msg)
    elif envcmssw is not None:
        cmssw = envcmssw
    else:
        msg = 'A CMSSW version must be provided either explicitly with --cmssw'
        msg += ' or implicitly in the environment.'
        raise Exception(msg)
    print(f'Found following CMSSW: {cmssw}')

    # check file existence
    if args.inputfile.startswith('root:'): pass # exception for remote files
    else:
        args.inputfile = os.path.abspath(args.inputfile) # important for CMSSW, cannot read relative paths
        if not os.path.exists(args.inputfile):
            raise Exception(f'Input file {args.inputfile} does not exist.')
    if not os.path.exists(args.template):
        raise Exception(f'Template config {args.template} does not exist.')

    # read template
    with open(args.template, 'r') as f:
        lines = f.readlines()

    # replace tags
    for idx, line in enumerate(lines):
        line = line.replace('TEMPLATE_INPUT_FILE', args.inputfile)
        line = line.replace('TEMPLATE_MAX_EVENTS', str(args.max_events))
        line = line.replace('TEMPLATE_GLOBAL_TAG', args.globaltag)
        line = line.replace('TEMPLATE_GEOMETRY', args.geometry)
        lines[idx] = line
    template = ''.join(lines)

    # read grid
    with open(args.grid, 'r') as f:
        grid = json.load(f)

    # make working directory
    #if os.path.exists(args.workdir):
    #    raise Exception(f'Working directory {args.workdir} already exists.')
    #os.makedirs(args.workdir)

    # loop over all combinations of parameter values
    # and make cmsRun config.
    allvalues = [param['values'] for param in grid]
    paramnames = [param['name'] for param in grid]
    combinations = itertools.product(*allvalues)
    for jobidx, valueset in enumerate(combinations):
        
        # modify config
        modifiers = [param['mod'].replace('VALUE', str(value)) for param, value in zip(grid, valueset)]
        modifier = '\n'.join(modifiers)
        config = template.replace('TEMPLATE_MOD', modifier)

        # make subdirectory and write config
        subdir = os.path.join(args.workdir, f'job{jobidx}')
        if not os.path.exists(subdir): os.makedirs(subdir)
        cffile = os.path.join(subdir, 'config.py')
        with open(cffile, 'w') as f: f.write(config)

        # write short file with parameter values for easier retrieval later
        paramdict = {name: val for name, val in zip(paramnames, valueset)}
        dfile = os.path.join(subdir, 'params.json')
        with open(dfile, 'w') as f: json.dump(paramdict, f, indent=2)

    # determine number of jobs from last index
    njobs = jobidx + 1

    # make efficiency calculation command
    # (hard-coded for now, maybe make more flexible later)
    eff_script = os.path.join(topdir, 'analysis/efficiency/calculate_associations.py')
    eff_cmd = f'python3 {eff_script} -i hgcalreco_out.root -o efficiency.parquet\n'

    # make working directories and executable files
    # note: ideally, would write the executable files in the working directories,
    #       but that does not work with condor if the working directories are on eos...
    #       so instead write them locally (and copy them to the working directory just for reference).
    exes = []
    for jobidx in range(njobs):
        workdir = os.path.abspath(os.path.join(args.workdir, f'job{jobidx}'))
        jobscript = os.path.abspath(f'cjob_run_{args.tag}_{jobidx}.sh')
        jobscript_copy = os.path.join(workdir, os.path.basename(jobscript))
        ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
        with open(jobscript, 'a') as f:
            # go to working directory
            f.write(f'cd {workdir}\n')
            # write actual commands to run
            f.write('cmsRun config.py\n')
            cmd = 'python3 ../../../analysis/efficiency/calculate_associations.py -i hgcalreco_out.root -o .'
            cmd += ' --input_config ../../../analysis/configs/input_config_customreco.json'
            f.write(f'{cmd}\n')
        exes.append(jobscript)
        # copy to workdir for reference
        cmd = f'cp {jobscript} {jobscript_copy}'
        os.system(cmd)

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
