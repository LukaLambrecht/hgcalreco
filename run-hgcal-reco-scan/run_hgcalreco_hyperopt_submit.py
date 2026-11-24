import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
thisdir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(topdir)

from tools.jobtools import get_cmssw
import tools.condortools as ct


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-g', '--grid', required=True, nargs='+')
    parser.add_argument('-n', '--max_events', default=-1, type=int,
        help='Maximum number of events (per input file, unless --no_per_file is given; default: all)')
    parser.add_argument('--no_per_file', default=False, action='store_true',
        help='Run a single re-reco over all input files (and a single efficiency calculation on its output),'
            + ' instead of the default re-reco and efficiency calculation per input file,'
            + ' with the outputs combined at the end')
    parser.add_argument('--space', default='discrete', choices=['discrete', 'uniform', 'loguniform'],
        help='Search space per parameter: the values in the grid file(s) (discrete, default),'
             ' or continuous between their minimum and maximum (uniform or loguniform;'
             ' loguniform falls back to uniform for parameters with a minimum value <= 0)')
    parser.add_argument('--max_trials', default=100, type=int,
        help='Total number of trials per run (resubmitting a run continues from its stored trials)')
    parser.add_argument('--max_hours', default=None, type=float,
        help='Time budget per run in hours: no new trial is started if it would be expected to end'
             ' after this time (default: no limit; keep it below the wall time of --job_flavour)')
    parser.add_argument('--no_default', default=False, action='store_true',
        help='Do not evaluate the default point (the default values in the grid file(s)) as the first trial of each run'
             ' (by default it is, if all parameters have a default value)')
    parser.add_argument('--nruns', default=1, type=int,
        help='Number of independent hyperopt runs (one job each, in subdirectories run<i> of the working directory)')
    parser.add_argument('--job_flavour', default='workday',
        choices=['espresso', 'microcentury', 'longlunch', 'workday', 'tomorrow', 'testmatch', 'nextweek'],
        help='Condor job flavour (wall time: 20 min, 1 h, 2 h, 8 h, 1 day, 3 days, 1 week)')
    parser.add_argument('-w', '--workdir', default='auto')
    parser.add_argument('--tag', default='auto')
    parser.add_argument('--config', default=os.path.join(thisdir, 'configs/hgcalreco_cff_template.py'))
    parser.add_argument('--globaltag', default='auto:phase2_realistic_T35')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D127')
    parser.add_argument('--era', default='Phase2C26I13M9',
        help='CMSSW era name (e.g. "Phase2C26I13M9" for D122/D127, "Phase2C22I13M9" for D121).'
             ' Must match the era used for sample production, similar to --geometry.')
    parser.add_argument('--gen_level', default=['truthbranch-signal'], nargs='+',
        help='Truth object type(s) for the efficiency calculation (see analysis/efficiency/calculate_associations.py),'
             ' default: truthbranch-signal; the main metric is the one for the first type.'
             ' CaloParticles ("cp") and/or SimClusters ("sc") are opt-in: if requested, the corresponding'
             ' (slow) truth associations are also run in the re-reco.')
    parser.add_argument('--do_composition', default=False, action='store_true',
        help='Also store the composition of TICLCandidates and truth objects per HGCAL subdetector'
             ' (see analysis/efficiency/calculate_associations.py).')
    parser.add_argument('--efficiency_level', default='tc',
        choices=['lc', 'tc', 'both'],
        help='Efficiency metrics to calculate after re-reco: TICLCandidate level (tc, default),'
             ' LayerCluster level (lc), or both. Note: the LayerCluster-level metrics need too much memory'
             ' for PU200 samples (dense truth x LayerCluster matrices, about 19 GB per event).')
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--overwrite', default=False, action='store_true')
    parser.add_argument('--submit', default=False, action='store_true')
    parser.add_argument('--request-memory', default=8000, type=int,
        help='Requested memory in MB. The re-reco + efficiency calculation pipeline'
             ' can need substantially more than the site default (a few GB even for'
             ' --do_tc_level alone), so this defaults higher than a typical condor job.')
    args = parser.parse_args()

    # parse tag
    if args.tag == 'auto': args.tag = os.path.basename(args.grid[0]).replace('.json', '')

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
    args.config = os.path.abspath(args.config) # important since the job runs from its own workdir

    # read grid
    grid = []
    for gridfile in args.grid:
        with open(gridfile, 'r') as f:
            grid += json.load(f)

    # make working directory
    if os.path.exists(args.workdir) and not args.overwrite:
        raise Exception(f'Working directory {args.workdir} already exists.')
    if not os.path.exists(args.workdir):
        os.makedirs(args.workdir)

    # make full context
    context = {
        "topdir": topdir,
        "template": args.config,
        "inputfiles": args.inputfiles,
        "max_events": args.max_events,
        "process_per_file": not args.no_per_file,
        "globaltag": args.globaltag,
        "geometry": args.geometry,
        "era": args.era,
        "efficiency_script": os.path.join(topdir, 'analysis/efficiency/calculate_associations.py'),
        "efficiency_config_type": "customreco",
        "efficiency_level": args.efficiency_level,
        "efficiency_gen_level": args.gen_level,
        "efficiency_do_composition": args.do_composition,
        "efficiency_recalculate": False
    }

    # write all required files to working directory
    # (one subdirectory per run, with its own context, all sharing the grid file and job script template)
    cmd = f'cp {os.path.join(thisdir, "templates", "run_hgcalreco_hyperopt.py")} {args.workdir}'
    os.system(cmd)
    grid_file = os.path.join(args.workdir, "grid.json")
    with open(grid_file, 'w') as f:
        json.dump(grid, f, indent=2)
    hyperopt_args = f'--space {args.space} --max_trials {args.max_trials}'
    if args.max_hours is not None: hyperopt_args += f' --max_hours {args.max_hours}'
    if args.no_default: hyperopt_args += ' --no_default'
    exes = []
    for run_idx in range(args.nruns):
        rundir = os.path.join(args.workdir, f'run{run_idx}') if args.nruns > 1 else args.workdir
        if not os.path.exists(rundir): os.makedirs(rundir)
        context_file = os.path.join(rundir, "context.json")
        with open(context_file, 'w') as f:
            json.dump({**context, "workdir": rundir}, f, indent=2)

        # make job script
        suffix = f'_run{run_idx}' if args.nruns > 1 else ''
        jobscript = os.path.abspath(f'cjob_run_{args.tag}{suffix}.sh')
        ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
        with open(jobscript, 'a') as f:
            # go to working directory
            f.write(f'cd {rundir}\n')
            # write actual commands to run
            f.write(f'python3 {os.path.join(args.workdir, "run_hgcalreco_hyperopt.py")} {grid_file} context.json {hyperopt_args}\n')
        exes.append(jobscript)

    # make job description
    name = f'cjob_run_{args.tag}'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    ct.makeJobDescription(jobdescriptor, '$(script)', doqueue=False,
        proxy=args.proxy, jobflavour=args.job_flavour, mem=args.request_memory)
    with open(jobdescriptor, 'a') as f:
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')

    # print output (and submit jobs if requested)
    print(f'Job working directory {args.workdir} has been prepared.')
    if args.submit: os.system(f'condor_submit {jobdescriptor}')
    else: print(f'Check if everything looks fine, then run condor_submit {jobdescriptor} to submit the jobs.')
