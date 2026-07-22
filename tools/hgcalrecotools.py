import os
import sys
import json
import shutil
import tempfile
import subprocess
import numpy as np
import pandas as pd
rng = np.random.default_rng()

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)
from analysis.tools.layertools import get_layer_counts


def format_vstring_files(files):
    """
    Format one or more input file paths as separate, individually quoted
    and protocol-prefixed cms.vstring entries for a PoolSource.
    ("root:"-prefixed remote files are left as-is; everything else gets "file:" prepended.)
    Note: not to be confused with tools.filetools.format_input_files,
    which expands a dataset/directory/pattern into a list of file names;
    this function instead formats an already-resolved list of file names
    for use in a cmsRun config template.
    """
    entries = [f if f.startswith('root:') else f'file:{f}' for f in files]
    return ',\n        '.join(f"'{entry}'" for entry in entries)


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
    config = config.replace('TEMPLATE_INPUT_FILES', format_vstring_files(context["inputfiles"]))
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

    # optional: do the actual running in a temporary directory
    # (for large output files), while final results will still be stored in workdir.
    # note: prefer the condor job's own local scratch directory if available
    # (set by HTCondor, cleaned up automatically when the job ends) over a hardcoded
    # /tmp, which on a shared worker node is common to all jobs running on it.
    rundir = workdir
    if use_tmpdir:
        basetmpdir = os.environ.get('_CONDOR_SCRATCH_DIR', '/tmp')
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
    # note: stdout/stderr are written directly to a small log file in workdir (not
    # rundir, which may be local/scratch storage), rather than captured via a pipe.
    # This makes cmsRun's own progress printouts (e.g. "Begin processing the Nth
    # record...") visible in near-real-time from the persistent output directory
    # while the job is still running (see jobprogress.py), instead of being buffered
    # in memory and only surfaced if the call fails.
    cmsrun_log_path = os.path.join(workdir, "cmsRun.log")
    with open(cmsrun_log_path, "w") as logfile:
        try:
            subprocess.run(["cmsRun", "config.py"], cwd=rundir, check=True,
                            stdout=logfile, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            with open(cmsrun_log_path, "r") as f: logtext = f.read()
            error_msg = f"cmsRun failed with return code {e.returncode}"
            error_msg += f"\nLog (last 1000 chars):\n{logtext[-1000:]}"  # avoid huge logs
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
    efficiency_level = context.get("efficiency_level", "both")
    if efficiency_level not in ["lc", "tc", "both"]:
        raise ValueError(f'Unknown efficiency_level "{efficiency_level}".')
    if efficiency_level in ["lc", "both"]:
        cmd.append("--do_lc_level")
    if efficiency_level in ["tc", "both"]:
        cmd.append("--do_tc_level")
    if context["efficiency_recalculate"]: cmd.append("--recalculate")
    # note: see the note above the cmsRun call for why this is written to a log file
    # in workdir rather than captured via a pipe (this also surfaces the per-event
    # "Reading event N..." printouts from calculate_associations.py).
    efficiency_log_path = os.path.join(workdir, "efficiency.log")
    with open(efficiency_log_path, "w") as logfile:
        try:
            subprocess.run(cmd, cwd=rundir, check=True,
                            stdout=logfile, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            with open(efficiency_log_path, "r") as f: logtext = f.read()
            error_msg = f"Efficiency calculation failed with return code {e.returncode}"
            error_msg += f"\nLog (last 1000 chars):\n{logtext[-1000:]}"
            print(error_msg, file=sys.stderr)
            return {"loss": 1e6, "status": "fail", "error": error_msg}

    # remove root file (to save disk space when running many trials),
    # or copy it back to workdir if requested and rundir is a separate (temporary)
    # directory, since it would otherwise be lost once that directory is cleaned up.
    if keep_root_output:
        if rundir != workdir:
            cmd = ["cp", os.path.join(rundir, "hgcalreco_out.root"), workdir]
            try: subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                print('WARNING: could not copy hgcalreco_out.root back to workdir.')
    else:
        try: subprocess.run(["rm", "hgcalreco_out.root"], cwd=rundir, check=True)
        except subprocess.CalledProcessError:
            print('WARNING: could not remove hgcalreco_out.root.')

    # clean up the temporary running directory itself (e.g. its copy of config.py).
    # on a condor job this is harmless either way (the whole scratch area is wiped
    # when the job ends), but matters for repeated local/interactive runs.
    if rundir != workdir:
        shutil.rmtree(rundir, ignore_errors=True)

    # metric extraction
    metrics_lc_file = os.path.join(outputdir, "metrics_lc.parquet")
    metrics_cp_file = os.path.join(outputdir, "metrics_cp_lc.parquet")
    metrics_tc_file = os.path.join(outputdir, "metrics_tc.parquet")
    metrics_cp_tc_file = os.path.join(outputdir, "metrics_cp_tc.parquet")
    if efficiency_level == "tc":
        metric = extract_tc_metric(metrics_tc_file, metrics_cp_tc_file)
        output_metrics_files = [metrics_tc_file, metrics_cp_tc_file]
    elif efficiency_level == "both":
        metric = extract_metric(metrics_lc_file, metrics_cp_file)
        output_metrics_files = [
            metrics_lc_file, metrics_cp_file,
            metrics_tc_file, metrics_cp_tc_file
        ]
    else:
        metric = extract_metric(metrics_lc_file, metrics_cp_file)
        output_metrics_files = [metrics_lc_file, metrics_cp_file]

    return {
        "loss": -metric,
        "status": "ok",
        "metric": metric,
        "params": params,
        "output_reco_file": os.path.join(workdir, "hgcalreco_out.root"),
        "output_metrics_files": output_metrics_files
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

    if len(results_lc) == 0 or len(results_cp) == 0:
        return 0.

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
    if not np.isfinite(metric):
        return 0.
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


def extract_tc_metric(results_tc, results_cp_tc):
    """
    Calculate a scalar metric from TICLCandidate-level association results.
    """

    if isinstance(results_tc, str):
        results_tc = pd.read_parquet(results_tc)
    if isinstance(results_cp_tc, str):
        results_cp_tc = pd.read_parquet(results_cp_tc)

    if len(results_tc) == 0 or len(results_cp_tc) == 0:
        return 0.

    tc_pur_avg = np.mean(results_tc['pur'].values)
    tc_eff_avg = np.mean(results_tc['eff'].values)
    cp_eff_avg = np.mean(results_cp_tc['eff_primary'].values)
    metric = (tc_pur_avg + tc_eff_avg + cp_eff_avg)/3.
    if not np.isfinite(metric):
        return 0.
    return metric
