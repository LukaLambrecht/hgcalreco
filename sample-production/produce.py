# Run a sample production chain

import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

import tools.condortools as ct


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
    parser.add_argument('--remove-intermediate-output', default=False, action='store_true')
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
    print(f'Found following CMSSW: {cmssw}')

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

    # other customizations
    for stepidx, cmd in enumerate(cmds):

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
        if stepidx == len(cmds)-1:
            
            # option 1: keep everything
            # note: directly copied from example sample, see README for more info.
            # note: gives very large files, but contains all info to re-run HGCAL reco.
            #customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_*_*_HLT\')')
            #customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_*_*_SIM\')')

            # option 2: minimal content
            # note: copied from run-hgcal-reco.
            # note: gives lean files, but not sure if they contain enough info to re-run HGCAL reco on top.
            #       update: seems like they do (at least with the minimal setup in run-hgcal-reco, probably not the full reco)!
            drop = [
              '*_*_*_*'
            ]
            keep = [
              '*_HGCalRecHit_*_*',
              '*_hgcalMergeLayerClusters_*_*',
              '*_ticlTracksters*_*_*',
              '*GenParticle*_*_*_*',
              '*TrackingParticle*_*_*_*',
              '*TrackingVertex*_*_*_*',
              '*SimTrack*_*_*_*',
              '*CaloParticle*_*_*_*',
              '*SimCluster*_*_*_*',
              '*CaloHit*_*_*_*'
            ]
            for collection in drop:
                customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'drop {collection}\')')
            for collection in keep:
                customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'keep {collection}\')')

        # others: to do as the need arises

        # (re-)add customization to command
        if len(customization)==0: continue
        customizationstr = '; '.join(customization)
        cmd += f' --{tag} "{customizationstr}"'

        # replace original command
        cmds[stepidx] = cmd

    # make set of commands for each job
    job_cmds = []
    for jobidx in range(args.number_of_jobs):
        this_job_cmds = []
        # add random seed
        # note: use jobidx + 1 because using random seed 0 gives errors!
        # note: the --customise_commands option seems to silently override any previous option with the same name...
        #       so need to take care in how to add it.
        tag = 'customise_commands'
        opt = f'process.RandomNumberGeneratorService.generator.initialSeed = {jobidx+1}'
        for cmd in cmds:
            if f'--{tag}' not in cmd:
                appendix = f'--{tag} "{opt}"'
                cmd = cmd + ' ' + appendix
            else:
                parts = cmd.split('--')
                idx = [idx for idx, part in enumerate(parts) if part.startswith(tag)][0]
                newpart = parts[idx].rstrip(';" \t\n') + f'; {opt}" '
                parts[idx] = newpart
                cmd = '--'.join(parts)
            this_job_cmds.append(cmd)
        # remove intermediate files if requested
        if args.remove_intermediate_output:
            for stepidx in range(len(cmds)-1):
                rm_cmd = f'rm step{stepidx}.root'
                this_job_cmds.append(rm_cmd)
        job_cmds.append(this_job_cmds)

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
        ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
        with open(jobscript, 'a') as f:
            # go to working directory
            f.write(f'cd {workdir}\n')
            # write actual commands to run
            for cmd in job_cmds[jobidx]: f.write(cmd+'\n')
        exes.append(jobscript)
        # copy to workdir for reference
        cmd = f'cp {jobscript} {jobscript_copy}'
        os.system(cmd)

    # make job description
    name = 'cjob_produce'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    ct.makeJobDescription(jobdescriptor, '$(script)', doqueue=False,
        proxy=args.proxy, jobflavour='workday')
    with open(jobdescriptor, 'a') as f:
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')

    # print output
    print(f'Job working directory {args.workdir} has been prepared.')
    print(f'Check if everything looks fine, then run condor_submit {jobdescriptor} to submit the jobs.')
