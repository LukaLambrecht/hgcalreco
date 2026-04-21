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
        return run_local_evaluation(paramdict, context)

    # run hyperopt
    trials = Trials()
    best = fmin(
        fn = objective,
        space = space,
        algo = tpe.suggest,
        max_evals = 20,
        trials = trials
    )

    # store results
    with open('trials.pkl', 'wb') as f:
        pickle.dump(trials, f)
