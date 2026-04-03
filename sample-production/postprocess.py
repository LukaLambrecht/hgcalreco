# Do some post processing on produced samples.

# Nothing fancy, mainly just folder reshuffling.


import os
import sys
import glob


if __name__=='__main__':

    # read production directory from the command line
    proddir = sys.argv[1]
    # expected content: subdirectories named job{idx},
    # each of which has the job script, the cmsRun configs,
    # and the output file.

    # copy all metadata from the first job to the top-level directory
    tocopy = sorted([f for f in os.listdir(os.path.join(proddir, 'job0')) if not f.endswith('.root')])
    metadir = os.path.join(proddir, 'metadata')
    if not os.path.exists(metadir): os.makedirs(metadir)
    print('Copying metadata...')
    for f in tocopy:
        cmd = f'cp {os.path.join(proddir, "job0", f)} {metadir}'
        print('  ' + cmd)
        os.system(cmd)

    # move all output root files to the top-level directory
    output = sorted(glob.glob(os.path.join(proddir, 'job*', 'step2.root')))
    print('Moving output files...')
    for f in output:
        idx = int(f.split('/')[-2].replace('job', ''))
        new = os.path.join(proddir, f'file_{idx}.root')
        cmd = f'mv {f} {new}'
        print('  ' + cmd)
        os.system(cmd)

    print('Check the result. If everything looks fine, run the following command:')
    print(f'rm -r {os.path.join(proddir, "job*")}')
