import os
import sys
import argparse


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-n', '--max_events', default=-1, type=int)
    parser.add_argument('-w', '--workdir', default='.')
    parser.add_argument('--template', default='templates/hgcalreco_cff_template.py')
    parser.add_argument('--globaltag', default='150X_mcRun4_realistic_v1')
    parser.add_argument('--geometry', default='GeometryExtendedRun4D121')
    parser.add_argument('--no_exec', default=False, action='store_true')
    args = parser.parse_args()

    # check file existence
    if not os.path.exists(args.inputfile):
        if args.inputfile.startswith('root:'): pass # exception for remote files
        else: raise Exception(f'Input file {args.inputfile} does not exist.')
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

    # make working directory
    if not os.path.exists(args.workdir):
        os.makedirs(args.workdir)

    # write config
    cffile = os.path.basename(args.template).replace('_template', '')
    cffile = os.path.join(args.workdir, cffile)
    with open(cffile, 'w') as f:
        for line in lines: f.write(line)

    # stop here if no execution is needed
    if args.no_exec: sys.exit()

    # run config
    cffilebase = os.path.basename(cffile)
    cmd = f'cd {args.workdir} && cmsRun {cffilebase}'
    os.system(cmd)
