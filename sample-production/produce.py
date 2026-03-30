# Run a sample production chain

import os
import sys
import json
import argparse


if __name__=='__main__':

    # read command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fragment', required=True)
    parser.add_argument('-c', '--chain', required=True)
    parser.add_argument('-w', '--workdir', required=True)
    parser.add_argument('-n', '--events-per-job', default=10, type=int)
    parser.add_argument('-j', '--number-of-jobs', default=1, type=int)
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--overwrite', default=False, action='store_true')
    args = parser.parse_args()

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

    # check if the fragment exists and move it to Configuration/GenProduction
    if not os.path.exists(args.fragment):
        raise Exception(f'Fragment {fragment} does not exist.')
    cmd = f'cp {args.fragment} $CMSSW_BASE/src/Configuration/GenProduction/python/'
    print(f'Copying fragment: {cmd}')
    os.system(cmd)

    # read the chain
    cmds = []
    with open(args.chain, 'r') as f:
        chain = json.load(f)
    for step in chain:
        stepfile = os.path.join('cmsdriver/steps', step)
        with open(stepfile) as f:
            lines = f.readlines()
        cmd = ' '.join([line.strip(' \\\n\t') for line in lines])
        cmds.append(cmd)

    # replace placeholders
    for stepidx, cmd in enumerate(cmds):
        cmd = cmd.replace('FRAGMENT', os.path.basename(args.fragment))
        cmd = cmd.replace('FILEIN', f'step{stepidx-1}.root')
        cmd = cmd.replace('FILEOUT', f'step{stepidx}.root')
        cmd = cmd.replace('NUM_EVENTS', f'{args.events_per_job}')
        cmds[stepidx] = cmd

    # make combined command for each job
    combined_cmds = []
    for jobidx in range(args.number_of_jobs):
        this_cmds = []
        # add random seed
        # note: use jobidx + 1 because using random seed 0 gives errors! 
        appendix = f'--customise_commands "process.RandomNumberGeneratorService.generator.initialSeed = {jobidx+1}"'
        for cmd in cmds:
            this_cmds.append(cmd + ' ' + appendix)
        combined_cmd = ' && '.join(this_cmds)
        combined_cmds.append(combined_cmd)

    # make working directories and executable files
    # note: ideally, would write the executable files in the working directories,
    #       but that does not work with condor if the working directories are on eos...
    #       so instead write them locally (and copy them to the working directory just for reference).
    if os.path.exists(args.workdir) and not args.overwrite:
        raise Exception(f'Working directory {args.workdir} already exists.')
    exes = []
    for jobidx in range(args.number_of_jobs):
        workdir = os.path.abspath(os.path.join(args.workdir, f'job{jobidx}'))
        if not os.path.exists(workdir): os.makedirs(workdir)
        jobscript = os.path.abspath(f'cjob_produce{jobidx}.sh')
        jobscript_copy = os.path.join(workdir, os.path.basename(jobscript))
        with open(jobscript, 'w') as f:
	        # write bash shebang
            f.write('#!/bin/bash\n')
	        # write sourcing of common software
            f.write('source /cvmfs/cms.cern.ch/cmsset_default.sh\n')
	        # write setting correct cmssw release
            if cmssw is not None:
                srcdir = os.path.join(cmssw, 'src')
                f.write(f'cd {srcdir}\n')
                f.write('eval `scram runtime -sh`\n')
                f.write('cmsenv\n')
	        # write export proxy
            if args.proxy is not None:
                f.write(f'export X509_USER_PROXY={args.proxy}\n')
            # go to working directory
            f.write(f'cd {workdir}\n')
            # write actual commands to run
            f.write(combined_cmds[jobidx]+'\n')
        # make executable
        os.system(f'chmod +x {jobscript}')
        exes.append(jobscript)
        # copy to workdir for reference
        cmd = f'cp {jobscript} {jobscript_copy}'
        os.system(cmd)

    # make job description
    name = 'cjob_produce'
    stdout = name + '_out_$(ClusterId)_$(ProcId)'
    stderr = name + '_err_$(ClusterId)_$(ProcId)'
    log = name + '_log_$(ClusterId)'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    with open(jobdescriptor, 'w') as f:
        f.write('executable = $(script)\n')
        f.write('output = {}\n'.format(stdout))
        f.write('error = {}\n'.format(stderr))
        f.write('log = {}\n\n'.format(log))
        f.write('request_cpus = 1\n')
        f.write('request_memory = 1024\n')
        f.write('request_disk = 10240\n')
        if args.proxy is not None: 
            f.write('x509userproxy = {}\n'.format(proxy))
            f.write('use_x509userproxy = true\n\n')
        f.write('+JobFlavour = "workday"\n')
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')
