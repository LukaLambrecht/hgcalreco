import os
import sys
import json
import pickle

from hyperopt import fmin, tpe, hp
from hyperopt import Trials

thisdir = os.path.abspath(os.path.dirname(__file__))
topdir = thisdir.split('/hgcalreco/')[0] + '/hgcalreco'
sys.path.append(topdir)

from tools.hgcalrecotools import run_local_evaluation


if __name__=='__main__':

    grid_file = os.path.abspath(sys.argv[1])
    context_file = os.path.abspath(sys.argv[2])

    # read grid
    with open(grid_file, 'r') as f:
        grid = json.load(f)

    # load context
    with open(context_file) as f:
        context = json.load(f)

    # parse grid to hyperopt grid
    param_mods = {el["name"]: el["mod"] for el in grid}
    space = {}
    for el in grid:
        param_name = el["name"]
        param_values = el["values"]
        space[param_name] = hp.choice(param_name, param_values)

    # define objective function
    def objective(params):
        # make dict of the form {parameter name: {"value": value, "mod": modifier string}}
        # as expected by run_local_evaluation
        paramdict = {}
        for param_name in params.keys():
            paramdict[param_name] = {"value": params[param_name], "mod": param_mods[param_name]}
        return run_local_evaluation(paramdict, context, use_tmpdir=True)

    # define helper function for running hyperopt just a few times before storing the result,
    # so that progress does not get lost if the job crashes at some later point.
    # note: running hyperopt in short batches while providing it the previous trials
    #       should give exactly the same result as running it in one long batch, see e.g. here:
    #       https://github.com/hyperopt/hyperopt/issues/267
    def run_hyperopt_batch(num_iterations=1):
        
        # load previously saved trials or create empty trials object
        trials_file = "trials.pkl"
        if os.path.exists(trials_file):
            with open(trials_file, 'rb') as f:
                trials = pickle.load(f)
        else: trials = Trials()

        # set maximum iterations (refers to total length of trials object, not just this batch)
        max_iterations = len(trials.trials) + num_iterations

        # run hyperopt
        best = fmin(
            fn = objective,
            space = space,
            algo = tpe.suggest,
            max_evals = max_iterations,
            trials = trials
        )

        # store results
        with open(trials_file, 'wb') as f:
            pickle.dump(trials, f)

    # run hyperopt
    num_iterations_per_batch = 1 # maybe later add as cmd line arg
    max_iterations = 100 # maybe later add as cmd line arg
    num_batches = int((max_iterations-1)/num_iterations_per_batch)+1
    print(f'Will run hyperopt in {num_batches} batches of size {num_iterations_per_batch}.')
    for batch_idx in range(num_batches):
        run_hyperopt_batch(num_iterations=num_iterations_per_batch)
