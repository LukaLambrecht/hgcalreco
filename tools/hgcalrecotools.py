import os
import sys
import subprocess
import tempfile
import json


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
    modifiers = '\n'.join([val["mod"] for val in params.values()])
    config = config.replace('TEMPLATE_MOD', modifiers)

    return config


def run_local_evaluation(params, context):
    """
    Runs a single evaluation locally.
    Input arguments:
    - params: dict of the form {parameter name: {"value": parameter value, "mod": modifier string}}.
    - context: dict with extra info.
    Returns a dict with loss + metadata.
    """

    # make a working directory if requested
    if "workdir" in context.keys():
        workdir = context["workdir"]
        if not os.path.exists(workdir): os.makedirs(workdir)
    else: workdir = '.'

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

    # metric extraction
    metric = extract_metric(os.path.join(workdir, "efficiency.parquet"))

    return {
        "loss": -metric,
        "status": "ok",
        "metric": metric,
        "params": params,
    }


def extract_metric(parquet_file):
    """
    Calculate simple scalar metric from output file.
    """
    # placeholder
    return 0.5
