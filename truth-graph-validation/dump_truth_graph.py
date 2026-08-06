# Convenience wrapper: dump and render the MC-truth graph (see PhysicsTools/TruthInfo,
# cms-sw/cmssw PR #51213) for a sample-production file produced with
# `produce.py --output-mode truth` (see ../sample-production).
#
# Runs dump_truth_graph_cfg.py via cmsRun to produce .dot files (one raw-graph
# and one logical-graph dump per event), then renders them to images with
# graphviz, so there's a single command from production output to viewable graph.


import os
import sys
import glob
import shutil
import argparse
import subprocess

thisdir = os.path.abspath(os.path.dirname(__file__))


if __name__=='__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True,
        help='Sample-production file produced with --output-mode truth.')
    parser.add_argument('-o', '--outputdir', default='output_truth_graph_dump')
    parser.add_argument('-n', '--maxevents', default=-1, type=int,
        help='Maximum number of events to process (default: all).')
    parser.add_argument('--tag', default='', help='Tag appended to output file names.')
    parser.add_argument('--process', default='RECO',
        help='Process name the truth-graph producers ran in during production'
             ' (check with edmDumpEventContent on the input file if unsure;'
             ' "RECO" matches the default sample-production chain).')
    parser.add_argument('--layout', default='dot', choices=['dot', 'sfdp', 'fdp', 'neato'],
        help='DOT layout for the logical-graph dump: "dot" for a hierarchical'
             ' tree (default), or a force-directed engine for dense graphs.')
    parser.add_argument('--show-all', default=False, action='store_true',
        help='Do not hide zero-simhit subgraphs or large SIM source vertices'
             ' in the logical-graph dump.')
    parser.add_argument('--format', default='png', choices=['png', 'svg', 'pdf'],
        help='Image format to render .dot files to with graphviz.')
    parser.add_argument('--no-render', default=False, action='store_true',
        help='Only produce .dot files, skip rendering to images (e.g. if'
             ' graphviz is not available).')
    args = parser.parse_args()

    if not os.path.exists(args.inputfile):
        raise Exception(f'Input file {args.inputfile} does not exist.')
    if not os.path.exists(args.outputdir):
        os.makedirs(args.outputdir)

    # run the dumper
    cfg = os.path.join(thisdir, 'dump_truth_graph_cfg.py')
    cmd = [
        'cmsRun', cfg, os.path.abspath(args.inputfile),
        '-o', args.outputdir,
        '-n', str(args.maxevents),
        '-t', args.tag,
        '--process', args.process,
        '--layout', args.layout,
    ]
    if args.show_all: cmd.append('--showAll')
    print(f'Running: {" ".join(cmd)}')
    subprocess.run(cmd, check=True)

    # render dot files to images
    if args.no_render:
        print(f'Skipping rendering (--no-render); .dot files are in {args.outputdir}')
        sys.exit(0)
    if shutil.which('dot') is None:
        print('WARNING: graphviz "dot" command not found on PATH; skipping'
              ' rendering. Install graphviz, or pass --no-render to suppress'
              ' this warning and just keep the .dot files.')
        sys.exit(0)

    dotfiles = sorted(glob.glob(os.path.join(args.outputdir, '*.dot')))
    print(f'Rendering {len(dotfiles)} .dot file(s) to .{args.format}...')
    for dotfile in dotfiles:
        outfile = os.path.splitext(dotfile)[0] + f'.{args.format}'
        subprocess.run(['dot', f'-T{args.format}', dotfile, '-o', outfile], check=True)
        print(f'  {outfile}')
