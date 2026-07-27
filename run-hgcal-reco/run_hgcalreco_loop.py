import os
import sys
import six
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.filetools import format_input_files
from tools.jobtools import get_cmssw
import tools.condortools as ct


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='.')
    parser.add_argument('-r', '--runmode', default='local', choices=['local', 'condor'])
    parser.add_argument('-p', '--proxy', default=None)
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--template', default='configs/hgcalreco_cff_template.py')
    parser.add_argument('--globaltag', default='auto:phase2_realistic_T35')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D122')
    parser.add_argument('--modifiers', default=None)
    parser.add_argument('--no_exec', default=False, action='store_true')
    args = parser.parse_args()

    # check file existence
    if not os.path.exists(args.template):
        raise Exception(f'Template config {args.template} does not exist.')
    if args.modifiers is not None:
        if not os.path.exists(args.modifiers):
            raise Exception(f'Modifier {args.modifiers} does not exist.')

    # get cmssw
    cmssw = get_cmssw(args.cmssw, error_if_none=True)

    # find input files depending on what is provided
    print('Finding input files...')
    inputfiles = format_input_files(args.input)
    print(f'Found following input files ({len(inputfiles)}):')
    for inputfile in inputfiles[:10]: print(f'  - {inputfile}')
    if len(inputfiles) > 10: print('  - ...')

    # ask for confirmation
    print(f'Will submit {len(inputfiles)} jobs. Continue? (y/n)')
    go = six.moves.input()
    if go != 'y': sys.exit()

    # make commands
    cmds = []
    for file_idx, inputfile in enumerate(inputfiles):
        workdir = os.path.join(args.workdir, f'file_{file_idx}')
        cmd = 'python3 run_hgcalreco.py'
        cmd += f' -i {inputfile}'
        if args.max_events > 0: cmd += f' -n {args.max_events}'
        cmd += f' -w {workdir}'
        cmd += f' --template {args.template}'
        cmd += f' --globaltag {args.globaltag}'
        cmd += f' --geometry {args.geometry}'
        if args.modifiers is not None: cmd += f' --modifiers {args.modifiers}'
        if args.no_exec: cmd += f' --no_exec'
        cmds.append(cmd)

   # run or submit commands
    if args.runmode == 'local':
        for cmd in cmds:
            print(cmd)
            os.system(cmd)
    elif args.runmode=='condor':
        ct.submitCommandsAsCondorCluster('cjob_run_hgcalreco', cmds,
          jobflavour='workday', cmssw_version=cmssw, proxy=args.proxy) 
