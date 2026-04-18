# Script that runs the full evaluation function
# (e.g. for usage in job submission)


import os
import sys
import json

thisdir = os.path.abspath(os.path.dirname(__file__))
topdir = thisdir.split('/hgcalreco/')[0] + '/hgcalreco'
sys.path.append(topdir)

from tools.hgcalrecotools import run_local_evaluation


if __name__=='__main__':

    params_file = os.path.abspath(sys.argv[1])
    context_file = os.path.abspath(sys.argv[2])

    # load params
    with open(params_file) as f:
        params = json.load(f)

    # load context
    with open(context_file) as f:
        context = json.load(f)

    # run full evaluation
    result = run_local_evaluation(params, context)

    # write final result
    outputfile = os.path.join(context["workdir"], "result.json")
    with open(outputfile, "w") as f:
        json.dump(result, f, indent=2)
