import os
import sys
import json
import tempfile
import subprocess
import numpy as np
import pandas as pd
rng = np.random.default_rng()


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


def run_local_evaluation(params, context, dryrun=False, use_tmpdir=False):
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
    if use_tmpdir: workdir = tempfile.mkdtemp(dir=workdir)

    # make working directory
    if not os.path.exists(workdir): os.makedirs(workdir)

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

    # run cmsRun
    try:
        subprocess.run(["cmsRun", "config.py"], cwd=workdir, check=True)
    except subprocess.CalledProcessError:
        return {"loss": 1e6, "status": "fail"}

    # run efficiency calculation
    try:
        subprocess.run(
            [
                "python3",
                context["efficiency_script"],
                "-i", "hgcalreco_out.root",
                "-o", "efficiency",
                "--input_config", context["efficiency_config"],
            ],
            cwd=workdir,
            check=True,
        )
    except subprocess.CalledProcessError:
        return {"loss": 1e6, "status": "fail"}

    # remove root file (to save disk space when running many trials)
    try: subprocess.run(["rm", "hgcalreco_out.root"], cwd=workdir, check=True)
    except subprocess.CalledProcessError:
        print('WARNING: could not remove hgcalreco_out.root.')

    # metric extraction
    metric = extract_metric(os.path.join(workdir, "efficiency/metrics_lc.parquet"))

    return {
        "loss": -metric,
        "status": "ok",
        "metric": metric,
        "params": params,
        "output_reco_file": os.path.join(workdir, "hgcalreco_out.root"),
        "output_metrics_file": os.path.join(workdir, "efficiency/metrics_lc.parquet")
    }


def extract_metric(parquet_file):
    """
    Calculate simple scalar metric from output file.
    """
    # simple placeholder for now, to extend later
    df = pd.read_parquet(parquet_file)
    pur_avg = np.mean(df['pur'].values)
    eff_avg = np.mean(df['eff'].values)
    return (pur_avg + eff_avg)/2
