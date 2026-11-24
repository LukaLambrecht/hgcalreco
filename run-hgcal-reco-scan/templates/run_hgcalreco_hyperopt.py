# Run a hyperopt optimization of the re-reco parameters
# (re-reco + efficiency calculation per trial, see tools/hgcalrecotools.py::run_local_evaluation).
#
# Usage: python3 run_hgcalreco_hyperopt.py grid.json context.json [options]
# - grid.json: list of parameters in the same format as the grid scans (name, mod, values, and optionally default);
#   see --space for how the values are turned into a search space.
# - context.json: run settings (input files, efficiency calculation, working directory, ...).
#
# The trials are stored in trials.pkl in the working directory after each trial,
# so that a crashed or resubmitted job continues where it stopped
# (--max_trials is the total number of trials, including the ones already in trials.pkl).
# The output of trial i is stored in the subdirectory trial<i> of the working directory.
# If all parameters in grid.json have a default value, the default point is evaluated as the first trial
# of a new run (unless --no_default is given), marked with "is_default": true in its result.


import os
import sys
import json
import time
import pickle
import argparse
import numpy as np

from hyperopt import fmin, tpe, hp
from hyperopt import Trials, STATUS_FAIL
from hyperopt.exceptions import AllTrialsFailed
from hyperopt.fmin import generate_trials_to_calculate


def get_space(grid, space_type):
    '''
    Make a hyperopt search space from the parameters in a grid file.
    - space_type "discrete": choice between the values of each parameter.
    - space_type "uniform": uniform between the minimum and maximum value of each parameter.
    - space_type "loguniform": log-uniform between the minimum and maximum value of each parameter
      (uniform for parameters with a minimum value <= 0, where log-uniform is not possible).
    '''
    space = {}
    for el in grid:
        name, values = el["name"], el["values"]
        if space_type == "discrete" or len(values) < 2:
            space[name] = hp.choice(name, values)
            continue
        vmin, vmax = min(values), max(values)
        if space_type == "loguniform" and vmin > 0:
            space[name] = hp.loguniform(name, np.log(vmin), np.log(vmax))
        else:
            if space_type == "loguniform":
                print(f'WARNING: minimum value of parameter {name} is {vmin} <= 0;'
                      + ' using a uniform instead of a log-uniform distribution.')
            space[name] = hp.uniform(name, vmin, vmax)
        print(f'Search space for parameter {name}: {space_type} between {vmin} and {vmax}')
    return space


def get_default_point(grid, space_type):
    '''
    Get the default point of the parameters in a grid file, in the format of hyperopt's points to evaluate
    (the value for continuous parameters, the index of the value for discrete ones), or None if not all parameters
    have a default value. The default values must be in the search space (one of the values for discrete parameters,
    between the minimum and maximum value for continuous ones).
    '''
    if not all('default' in el for el in grid): return None
    point = {}
    for el in grid:
        name, values, default = el["name"], el["values"], el["default"]
        if space_type == "discrete" or len(values) < 2:
            matches = [idx for idx, value in enumerate(values) if np.isclose(value, default)]
            if len(matches) == 0: raise Exception(f'Default value {default} of parameter {name} is not one of its values.')
            point[name] = matches[0]
        else:
            if not min(values) <= default <= max(values):
                raise Exception(f'Default value {default} of parameter {name} is outside of its range.')
            point[name] = default
    return point


if __name__=='__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('grid_file')
    parser.add_argument('context_file')
    parser.add_argument('--space', default='discrete', choices=['discrete', 'uniform', 'loguniform'],
        help='Search space per parameter: the values in the grid file (discrete),'
             ' or continuous between their minimum and maximum (uniform or loguniform)')
    parser.add_argument('--max_trials', default=100, type=int,
        help='Total number of trials (including the ones already stored in trials.pkl)')
    parser.add_argument('--max_hours', default=None, type=float,
        help='Time budget in hours: no new trial is started if it would be expected to end after this time'
             ' (based on the average duration of the trials in this job so far); default: no limit')
    parser.add_argument('--no_default', default=False, action='store_true',
        help='Do not evaluate the default point (the default values in the grid file) as the first trial of a new run')
    args = parser.parse_args()
    start_time = time.time()

    # read grid
    with open(os.path.abspath(args.grid_file), 'r') as f:
        grid = json.load(f)

    # load context
    with open(os.path.abspath(args.context_file)) as f:
        context = json.load(f)
    workdir = context.get("workdir", os.getcwd())

    topdir = context.get("topdir")
    if topdir is None:
        thisdir = os.path.abspath(os.path.dirname(__file__))
        topdir = thisdir.split('/hgcalreco/')[0] + '/hgcalreco'
    sys.path.append(topdir)

    from tools.hgcalrecotools import run_local_evaluation

    # make the search space
    param_mods = {el["name"]: el["mod"] for el in grid}
    space = get_space(grid, args.space)
    defaults = {el["name"]: el["default"] for el in grid} if all('default' in el for el in grid) else None

    # define objective function
    def objective(params):
        # make dict of the form {parameter name: {"value": value, "mod": modifier string}}
        # as expected by run_local_evaluation
        paramdict = {}
        for param_name in params.keys():
            value = params[param_name]
            if isinstance(value, np.generic): value = value.item()
            paramdict[param_name] = {"value": value, "mod": param_mods[param_name]}
        # whether this is the default point
        is_default = (defaults is not None and all(np.isclose(paramdict[n]["value"], defaults[n]) for n in defaults))
        # run in a new subdirectory trial<i> (first index not yet in use)
        trial_idx = 0
        while os.path.exists(os.path.join(workdir, f'trial{trial_idx}')): trial_idx += 1
        trial_context = {**context, "workdir": os.path.join(workdir, f'trial{trial_idx}')}
        print(f'Running trial {trial_idx} with parameters {json.dumps({k: v["value"] for k, v in paramdict.items()})}')
        # note: an exception in a trial (e.g. a transient I/O error on the output storage) is recorded
        #       as a failed trial (ignored by hyperopt), instead of ending the whole run.
        try:
            res = run_local_evaluation(paramdict, trial_context, use_tmpdir=True)
            res["trial_dir"] = trial_context["workdir"]
            res["is_default"] = bool(is_default)
            # write the result next to the trial output, for reading it without the trials object
            with open(os.path.join(trial_context["workdir"], "result.json"), "w") as f:
                json.dump(res, f, indent=2, default=float)
        except Exception as e:
            print(f'WARNING: trial {trial_idx} failed with an exception: {e!r}')
            res = {"status": STATUS_FAIL, "error": repr(e), "params": paramdict, "trial_dir": trial_context["workdir"],
                   "is_default": bool(is_default)}
        return res

    # run hyperopt one trial at a time, storing the trials object after each one,
    # so that progress does not get lost if the job crashes at some later point.
    # note: running hyperopt in short batches while providing it the previous trials
    #       should give exactly the same result as running it in one long batch, see e.g. here:
    #       https://github.com/hyperopt/hyperopt/issues/267
    trials_file = os.path.join(workdir, "trials.pkl")
    if os.path.exists(trials_file):
        with open(trials_file, 'rb') as f: trials = pickle.load(f)
        print(f'Loaded {len(trials.trials)} previous trials from {trials_file}.')
    else:
        # new run: start with the default point (if available), queued as the first trial
        # (note: hyperopt evaluates a queued trial together with the next one it suggests, so the first call
        #  of fmin below runs two trials)
        default_point = None if args.no_default else get_default_point(grid, args.space)
        if default_point is not None:
            print(f'Starting with the default point: {defaults}')
            trials = generate_trials_to_calculate([default_point])
            trials.refresh()
        else: trials = Trials()
    print(f'Will run hyperopt up to a total of {args.max_trials} trials'
          + (f' or {args.max_hours} hours.' if args.max_hours is not None else '.'))
    durations = []
    while len(trials.trials) < args.max_trials:
        # check the time budget
        elapsed = time.time() - start_time
        if args.max_hours is not None and len(durations) > 0:
            if elapsed + np.mean(durations) > args.max_hours * 3600:
                print(f'Stopping: the next trial would likely exceed the time budget of {args.max_hours} hours.')
                break
        # run one trial
        trial_start = time.time()
        # (note: determining the best point fails if all trials so far failed; return_argmin=False avoids that,
        #  but is ignored if fmin delegates to Trials.fmin, hence also allow_trials_fmin=False and the guard)
        n_before = len([trial for trial in trials.trials if trial['result'].get('status') != 'new'])
        try:
            fmin(fn=objective, space=space, algo=tpe.suggest,
                 max_evals=len(trials.trials) + 1, trials=trials, show_progressbar=False,
                 return_argmin=False, allow_trials_fmin=False)
        except AllTrialsFailed:
            pass
        # (duration per trial, also if this call ran more than one trial)
        n_run = max(len(trials.trials) - n_before, 1)
        durations += [(time.time() - trial_start) / n_run] * n_run
        with open(trials_file, 'wb') as f: pickle.dump(trials, f)
        losses = [loss for loss in trials.losses() if loss is not None]
        for idx in range(len(trials.trials) - n_run, len(trials.trials)):
            result = trials.trials[idx]["result"]
            print(f'Finished trial {idx} in {durations[-1] / 60:.1f} min'
                  + f' (status: {result["status"]}, loss: {result.get("loss")}, default point: {result.get("is_default")},'
                  + f' best so far: {min(losses) if len(losses) > 0 else None}).')
    print(f'Done: {len(trials.trials)} trials in total.')
