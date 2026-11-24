# Common tools for the studies on hyperopt runs of the CLUE parameters
# (see run-hgcal-reco-scan/run_hgcalreco_hyperopt_submit.py).
#
# A hyperopt output directory contains one subdirectory run<i> per independent run (or is a single run itself),
# each with a context.json, a trials.pkl (all trials, in chronological order) and one subdirectory trial<i> per trial
# (with params_summary.json, result.json and the efficiency output, like a grid scan point).
# The analysis tools of the grid scans (../clue-parameter-sensitivity) are reused as much as possible.
# Only the hyperopt outputs themselves are used. The default parameter point is the first trial of each run
# (flagged with is_default) for runs submitted with default values in their grid file.


import os
import sys
import json
import glob
import pickle
import numpy as np

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)
sys.path.append(os.path.join(thisdir, '../clue-parameter-sensitivity'))


# default hyperopt output directory
DEFAULT_INPUT = '/eos/home-l/llambrec/hgcalreco-data/hyperopt/output_20261120_201X_D127_PU200_5d_loguniform'


def get_default_outputdir(inputdir):
    '''Default output directory for an input directory: output_<name without "output_" prefix> next to these scripts.'''
    name = os.path.basename(os.path.normpath(inputdir))
    if name.startswith('output_'): name = name[len('output_'):]
    return os.path.join(thisdir, f'output_{name}')


def get_runs(inputdir):
    '''
    Get the run directories in a hyperopt output directory (run<i>, sorted by i),
    or the directory itself if it is a single run.
    '''
    if os.path.exists(os.path.join(inputdir, 'context.json')): return [inputdir]
    runs = glob.glob(os.path.join(inputdir, 'run[0-9]*'))
    return sorted(runs, key=lambda d: int(os.path.basename(d)[len('run'):]))


def load_trials(rundir):
    '''
    Get the trials of a run in chronological order, as a list of dicts with keys:
    index (chronological trial number), status, metric (minus the hyperopt loss; None if not ok),
    trial_dir (directory with the trial output), params (parameter name -> value),
    and is_default (whether the trial is the default point).
    Uses trials.pkl (needs the hyperopt package); falls back to the trial directories
    (ordered by their number, which is chronological except after an interrupted trial).
    '''
    trials_file = os.path.join(rundir, 'trials.pkl')
    trials = []
    try:
        with open(trials_file, 'rb') as f: hyperopt_trials = pickle.load(f)
        for idx, trial in enumerate(hyperopt_trials.trials):
            result = trial['result']
            ok = (result.get('status') == 'ok')
            trials.append({'index': idx, 'status': result.get('status'), 'metric': -result['loss'] if ok else None,
                'trial_dir': result.get('trial_dir'), 'is_default': bool(result.get('is_default', False)),
                'params': {name: val['value'] for name, val in result.get('params', {}).items()}})
        return trials
    except (OSError, ImportError) as e:
        print(f'WARNING: could not read {trials_file} ({e!r}); using the trial directories instead.')
    trialdirs = sorted(glob.glob(os.path.join(rundir, 'trial[0-9]*')), key=lambda d: int(os.path.basename(d)[len('trial'):]))
    for trialdir in trialdirs:
        resultfile = os.path.join(trialdir, 'result.json')
        if not os.path.exists(resultfile): continue
        with open(resultfile) as f: result = json.load(f)
        ok = (result.get('status') == 'ok')
        trials.append({'index': len(trials), 'status': result.get('status'), 'metric': result['metric'] if ok else None,
            'trial_dir': trialdir, 'is_default': bool(result.get('is_default', False)),
            'params': {name: val['value'] for name, val in result.get('params', {}).items()}})
    return trials


def get_default_point(rundir, trials=None):
    '''
    Get the default point of a run (the trial flagged as the default point, a dict as returned by load_trials),
    or None if there is none.
    '''
    if trials is None: trials = load_trials(rundir)
    for trial in trials:
        if trial['is_default'] and trial['status'] == 'ok': return trial
    return None


def get_metric(truth):
    '''
    The main metric (see tools/hgcalrecotools.py::extract_tc_metric, the hyperopt objective) from a per-truth-object
    table as returned by load_job: the average of the mean combined purity and the mean efficiency
    normalized to the truth energy in RecHits.
    '''
    return (np.nanmean(truth['pur_all'].values) + np.mean(truth['eff_all_rechits'].values)) / 2
