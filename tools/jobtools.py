import os
import sys


def get_cmssw(cmdlcmssw, error_if_none=False):
    # get CMSSW version if provided
    # priority:
    # - command line arg
    # - environment
    cmssw = None
    envcmssw = os.getenv('CMSSW_BASE')
    if cmdlcmssw is not None:
        cmssw = os.path.abspath(cmdlcmssw)
        if not os.path.exists(cmssw):
            raise Exception(f'Provided CMSSW {cmssw} does not exist.')
        if envcmssw is not None and envcmssw!=cmssw:
            msg = 'WARNING: provided CMSSW {cmssw} is different from current environment CMSSW {envcmssw}.'
            print(msg)
    elif envcmssw is not None:
        cmssw = envcmssw
    elif error_if_none:
        msg = 'A CMSSW version must be provided either explicitly with --cmssw'
        msg += ' or implicitly in the environment.'
        raise Exception(msg)
    return cmssw
