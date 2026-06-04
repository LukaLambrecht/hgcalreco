# Make symbolic links inside a CMSSW version to these packages

import os
import sys
import json


if __name__=='__main__':

    # find all packages in this folder
    packages = [os.path.abspath(d) for d in os.listdir('.') if os.path.isdir(d)]
    print('Found following packages to symlink:')
    print(json.dumps(packages, indent=2))

    # find CMSSW version
    cmssw = os.getenv('CMSSW_BASE')
    if cmssw is None or len(cmssw)==0:
        raise Exception('No CMSSW environment found; first do cmsenv.')

    # make symlink commands
    cmds = []
    for p in packages:
        dest = os.path.join(cmssw, 'src', os.path.basename(p))
        if os.path.lexists(dest):
            if os.path.islink(dest) or os.path.isfile(dest):
                os.unlink(dest)
            elif os.path.isdir(dest):
                raise Exception(f'Cannot replace existing directory {dest}.')
            else:
                raise Exception(f'Cannot replace existing path {dest}.')
        cmd = f'ln -s {p} {dest}'
        cmds.append(cmd)

    # run commands
    for cmd in cmds:
        print(cmd)
        os.system(cmd)
