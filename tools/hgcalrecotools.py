import os
import sys
import json
import tempfile
import subprocess
import numpy as np
import pandas as pd
rng = np.random.default_rng()

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)
from tools.layertools import get_layer_counts


def build_config(template, params, context):
    """
    Builds a cmsRun config starting from a template.
    Input arguments:
    - template: template cmsRun config in string format.
    - params: dict of the form {parameter name: {"value": parameter value, "mod": modifier string}}.
    - context: dict with extra info.
    Returns the cmsRun config in string format.
    """

    config = template

    # generic settings (independent of specific parameters)
    config = config.replace('TEMPLATE_INPUT_FILE', context["inputfile"])
    config = config.replace('TEMPLATE_MAX_EVENTS', str(context["max_events"]))
    config = config.replace('TEMPLATE_GLOBAL_TAG', context["globaltag"])
    config = config.replace('TEMPLATE_GEOMETRY', context["geometry"])

    # specific parameter modifiers
    modifiers = '\n'.join([val["mod"].replace("VALUE", str(val["value"])) for val in params.values()])
    config = config.replace('TEMPLATE_MOD', modifiers)

    return config


def run_local_evaluation(params, context,
    dryrun=False,
    use_subdir=False,
    use_tmpdir=False,
    keep_root_output=False):
    """
    Runs a single evaluation locally.
    Input arguments:
    - params: dict of the form {parameter name: {"value": parameter value, "mod": modifier string}}.
    - context: dict with extra info.
    Returns a dict with loss + metadata.
    """

    # get working directory
    if "workdir" in context.keys(): workdir = context["workdir"]
    else: workdir = '.'
    if use_subdir: workdir = tempfile.mkdtemp(dir=workdir)

    # optional: do the actual running in a temporary directory in /tmp
    # (for large ouptput files), while final results will still be stored in workdir.
    rundir = workdir
    if use_tmpdir:
        basetmpdir = '/tmp'
        rundir = tempfile.mkdtemp(dir=basetmpdir)

    # make working directory (and potentially different running directory)
    if not os.path.exists(workdir): os.makedirs(workdir)
    if not os.path.exists(rundir): os.makedirs(rundir)

    # read provided cmsRun template
    template_file = context["template"]
    with open(template_file, 'r') as f:
        template = f.read()

    # build and write config
    config = build_config(template, params, context)
    config_path = os.path.join(workdir, "config.py")
    with open(config_path, "w") as f:
        f.write(config)

    # write params to workdir for later reference
    with open(os.path.join(workdir, "params.json"), "w") as f:
        json.dump(params, f, indent=2)

    # also write parameter summary for easier reading
    param_dict = {key: val["value"] for key, val in params.items()}
    with open(os.path.join(workdir, "params_summary.json"), 'w') as f:
        json.dump(param_dict, f, indent=2) 

    # dryrun option: return dummy values without actually running something
    if dryrun:
        rnd = rng.random()
        res = {
            "loss": -rnd,
            "status": "ok",
            "metric": rnd,
            "params": params,
        }
        return res

    # in case the actual running directory is a temporary directory different from workdir,
    # copy the cmsRun config to that directory
    if rundir != workdir:
        cmd = ["cp", config_path, rundir]
        try: subprocess.run(cmd, cwd=workdir, check=True)
        except subprocess.CalledProcessError:
            print('WARNING: could not copy config to rundir.')

    # run cmsRun
    try:
        result = subprocess.run(["cmsRun", "config.py"], cwd=rundir, check=True, 
                              capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"cmsRun failed with return code {e.returncode}"
        if e.stdout:
            error_msg += f"\nStdout:\n{e.stdout[-1000:]}"  # Last 1000 chars to avoid huge logs
        if e.stderr:
            error_msg += f"\nStderr:\n{e.stderr[-1000:]}"
        print(error_msg, file=sys.stderr)
        return {"loss": 1e6, "status": "fail", "error": error_msg}

    # run efficiency calculation
    outputdir = os.path.join(workdir, "efficiency")
    cmd = ([
        "python3",
        context["efficiency_script"],
        "-i", "hgcalreco_out.root",
        "-o", outputdir,
        "--input_config_type", context["efficiency_config_type"]
    ])
    if context["efficiency_recalculate"]: cmd.append("--recalculate")
    try:
        result = subprocess.run(
            cmd,
            cwd = rundir,
            check = True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Efficiency calculation failed with return code {e.returncode}"
        if e.stdout:
            error_msg += f"\nStdout:\n{e.stdout[-1000:]}"
        if e.stderr:
            error_msg += f"\nStderr:\n{e.stderr[-1000:]}"
        print(error_msg, file=sys.stderr)
        return {"loss": 1e6, "status": "fail", "error": error_msg}

    # remove root file (to save disk space when running many trials)
    if keep_root_output: pass
    else:
        try: subprocess.run(["rm", "hgcalreco_out.root"], cwd=rundir, check=True)
        except subprocess.CalledProcessError:
            print('WARNING: could not remove hgcalreco_out.root.')

    # metric extraction
    metrics_lc_file = os.path.join(outputdir, "metrics_lc.parquet")
    metrics_cp_file = os.path.join(outputdir, "metrics_cp.parquet")
    metric = extract_metric(metrics_lc_file, metrics_cp_file)

    return {
        "loss": -metric,
        "status": "ok",
        "metric": metric,
        "params": params,
        "output_reco_file": os.path.join(workdir, "hgcalreco_out.root"),
        "output_metrics_files": [metrics_lc_file, metrics_cp_file]
    }


def extract_metric(results_lc, results_cp):
    """
    Calculate simple scalar metric from dataframes with results
    for LayerClusters and CaloParticles.
    """
    # simple placeholder for now, to extend later

    # read input file(s) if needed
    if isinstance(results_lc, str):
        results_lc = pd.read_parquet(results_lc)
    if isinstance(results_cp, str):
        results_cp = pd.read_parquet(results_cp)

    # calculate metrics
    lc_pur_avg = np.mean(results_lc['pur'].values)
    lc_eff_avg = np.mean(results_lc['eff'].values)
    cp_eff_avg = np.mean(results_cp['eff'].values)
    layers = results_lc['layer'].values
    eventids = results_lc['event'].values
    counts_per_layer = get_layer_counts(layers, eventids=eventids, absolute=True)
    counts_per_layer_avg = np.mean(list(counts_per_layer.values())) / 40.

    # combine them into a single metric
    metric = (lc_pur_avg + lc_eff_avg + cp_eff_avg)/3.
    #metric = lc_pur_avg * lc_eff_avg * cp_eff_avg
    #metric = (lc_pur_avg + lc_eff_avg + cp_eff_avg + (1-counts_per_layer_avg)) / 4.

    # printouts for testing
    '''print()
    print(lc_pur_avg)
    print(lc_eff_avg)
    print(cp_eff_avg)
    print(counts_per_layer_avg)
    print(metric)
    print()'''

    return metric
