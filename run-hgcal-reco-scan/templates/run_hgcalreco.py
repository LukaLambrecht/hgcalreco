# Script that runs the full evaluation function
# (e.g. for usage in job submission)


import os
import sys
import json


if __name__=='__main__':

    params_file = os.path.abspath(sys.argv[1])
    context_file = os.path.abspath(sys.argv[2])

    # load params
    with open(params_file) as f:
        params = json.load(f)

    # load context
    with open(context_file) as f:
        context = json.load(f)

    topdir = context.get("topdir")
    if topdir is None:
        thisdir = os.path.abspath(os.path.dirname(__file__))
        topdir = thisdir.split('/hgcalreco/')[0] + '/hgcalreco'
    sys.path.append(topdir)

    from tools.hgcalrecotools import run_local_evaluation

    # run full evaluation
    # note: use_tmpdir=True runs cmsRun (and the large hgcalreco_out.root it produces)
    # in a separate scratch directory rather than directly in the (typically AFS/EOS,
    # quota-constrained) workdir; only the small, final outputs (config, params,
    # efficiency parquet files, result.json) ever get written there. This matters most
    # when running many jobs in parallel, since the large transient file never touches
    # shared/quota-constrained storage at all.
    result = run_local_evaluation(params, context,
        use_tmpdir=True,
        keep_root_output=False
    )

    # write final result
    outputfile = os.path.join(context["workdir"], "result.json")
    with open(outputfile, "w") as f:
        json.dump(result, f, indent=2)
