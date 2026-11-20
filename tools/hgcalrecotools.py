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


# truth object types (see analysis/efficiency/calculate_associations.py --gen_level)
# default: truth Branches of the MC-truth graph at the "signal" level
DEFAULT_GEN_LEVELS = ["truthbranch-signal"]
# truth object types that need the (opt-in) CaloParticle/SimCluster-based truth in the re-reco
CALO_TRUTH_GEN_LEVELS = ["cp", "sc", "both"]


def uses_calo_truth(context):
    """
    Whether the CaloParticle/SimCluster-based truth associations should be run in the re-reco
    (and stored in its output): if explicitly requested with context["calo_truth"],
    or if needed for the requested truth object types (context["efficiency_gen_level"]).
    """
    if context.get("calo_truth", False): return True
    gen_levels = context.get("efficiency_gen_level", DEFAULT_GEN_LEVELS)
    return any(gen_level in CALO_TRUTH_GEN_LEVELS for gen_level in gen_levels)


def build_config(template, params, context, extra_modifiers=None):
    """
    Builds a cmsRun config starting from a template.
    Input arguments:
    - template: template cmsRun config in string format.
    - params: dict of the form {parameter name: {"value": parameter value, "mod": modifier string}}.
    - context: dict with extra info (inputfiles, max_events, globaltag, geometry, era,
      and optionally calo_truth and/or efficiency_gen_level, see uses_calo_truth).
    - extra_modifiers: optional string with additional config modifications
      (e.g. the content of a modifier file), added after the parameter modifiers.
    Returns the cmsRun config in string format.
    Used by both run-hgcal-reco/run_hgcalreco.py and the grid scans in run-hgcal-reco-scan.
    """

    config = template

    # generic settings (independent of specific parameters)
    config = config.replace('TEMPLATE_INPUT_FILES', format_vstring_files(context["inputfiles"]))
    config = config.replace('TEMPLATE_MAX_EVENTS', str(context["max_events"]))
    config = config.replace('TEMPLATE_GLOBAL_TAG', context["globaltag"])
    config = config.replace('TEMPLATE_GEOMETRY', context["geometry"])
    era = context.get("era", "Phase2C26I13M9")
    config = config.replace('TEMPLATE_ERA_IMPORT', f'from Configuration.Eras.Era_{era}_cff import {era}')
    config = config.replace('TEMPLATE_ERA', era)
    config = config.replace('TEMPLATE_CALO_TRUTH', str(uses_calo_truth(context)))

    # specific parameter modifiers (and optional extra modifiers)
    modifiers = [val["mod"].replace("VALUE", str(val["value"])) for val in params.values()]
    if extra_modifiers is not None: modifiers.append(extra_modifiers)
    modifiers = '\n'.join(modifiers) if len(modifiers) > 0 else '# (no modifiers added)'
    config = config.replace('TEMPLATE_MOD', modifiers)

    return config


def _run_logged(cmd, cwd, logpath, description, append=False, header=None):
    """
    Run a command with stdout/stderr written to a log file.
    Returns None on success, or an error message on failure.
    note: the output is written directly to a small log file in workdir (not rundir, which may be
    local/scratch storage), rather than captured via a pipe. This makes progress printouts
    (e.g. "Begin processing the Nth record..." from cmsRun, "Reading event N..." from the
    efficiency calculation) visible in near-real-time from the persistent output directory
    while the job is still running (see jobprogress.py), instead of being buffered in memory
    and only surfaced if the call fails.
    """
    with open(logpath, "a" if append else "w") as logfile:
        if header is not None:
            logfile.write(f"\n===== {header} =====\n")
            logfile.flush()
        # note: the return code is stored explicitly, since the exception variable
        #       is no longer defined after the except block.
        returncode = None
        try:
            subprocess.run(cmd, cwd=cwd, check=True, stdout=logfile, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
        if returncode is None: return None
    with open(logpath, "r") as f: logtext = f.read()
    error_msg = f"{description} failed with return code {returncode}"
    error_msg += f"\nLog (last 1000 chars):\n{logtext[-1000:]}"  # avoid huge logs
    print(error_msg, file=sys.stderr)
    return error_msg


def get_efficiency_command(context, inputfile, outputdir):
    """Build the command for the efficiency calculation (see analysis/efficiency/calculate_associations.py)."""
    cmd = ([
        "python3",
        context["efficiency_script"],
        "-i", inputfile,
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
    # truth object types (e.g. cp, truthbranch-signal; see calculate_associations.py)
    gen_levels = context.get("efficiency_gen_level", DEFAULT_GEN_LEVELS)
    cmd += ["--gen_level"] + gen_levels
    # composition of TICLCandidates and truth objects per subdetector (see calculate_associations.py)
    if context.get("efficiency_do_composition", False): cmd.append("--do_composition")
    return cmd


# offset added to the event numbers of the i-th input file when combining the outputs
# of the per-file processing (same convention as in calculate_associations.py for multiple input files)
EVENT_OFFSET_PER_FILE = 1000000


def combine_efficiency_outputs(partdirs, outputdir):
    """
    Combine the efficiency outputs (parquet files) of several input files processed separately
    into one set of output files, with the event numbers of the i-th part offset by
    i * EVENT_OFFSET_PER_FILE (so that they stay unique).
    """
    if not os.path.exists(outputdir): os.makedirs(outputdir)
    names = sorted(set(f for partdir in partdirs for f in os.listdir(partdir) if f.endswith('.parquet')))
    for name in names:
        dfs = []
        for idx, partdir in enumerate(partdirs):
            path = os.path.join(partdir, name)
            if not os.path.exists(path):
                raise Exception(f'Output file {name} is missing for input file {idx} (in {partdir}).')
            df = pd.read_parquet(path)
            if 'event' not in df.columns:
                raise Exception(f'Output file {path} has no event column; cannot combine the per-file outputs.')
            df['event'] = df['event'] + idx * EVENT_OFFSET_PER_FILE
            dfs.append(df)
        pd.concat(dfs, ignore_index=True).to_parquet(os.path.join(outputdir, name))


def run_local_evaluation(params, context,
    dryrun=False,
    use_subdir=False,
    use_tmpdir=False,
    keep_root_output=False):
    """
    Runs a single evaluation locally (re-reco with cmsRun, followed by the efficiency calculation).
    Input arguments:
    - params: dict of the form {parameter name: {"value": parameter value, "mod": modifier string}}.
    - context: dict with extra info.
      If context["process_per_file"] is True and there are multiple input files, the re-reco and
      the efficiency calculation are run separately for each input file, and the efficiency outputs
      are combined at the end (with the event numbers of the i-th file offset by i * EVENT_OFFSET_PER_FILE);
      context["max_events"] then applies per input file.
      Otherwise, a single re-reco runs over all input files, followed by a single efficiency calculation.
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

    # define the processing units: either one per input file, or one for all input files together
    inputfiles = context["inputfiles"]
    per_file = context.get("process_per_file", False) and len(inputfiles) > 1
    units = [[inputfile] for inputfile in inputfiles] if per_file else [inputfiles]

    # build and write config(s)
    # (config.py for the combined processing, config_file<i>.py for the processing per input file)
    config_paths = []
    for idx, unit in enumerate(units):
        config = build_config(template, params, {**context, "inputfiles": unit})
        config_path = os.path.join(workdir, f"config_file{idx}.py" if per_file else "config.py")
        with open(config_path, "w") as f:
            f.write(config)
        config_paths.append(config_path)

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

    # loop over processing units
    # (each one in its own running directory if there are several, since the cmsRun output file name is fixed)
    outputdir = os.path.join(workdir, "efficiency")
    cmsrun_log_path = os.path.join(workdir, "cmsRun.log")
    efficiency_log_path = os.path.join(workdir, "efficiency.log")
    partdirs = []
    output_reco_files = []
    for idx, (unit, config_path) in enumerate(zip(units, config_paths)):
        unit_rundir = os.path.join(rundir, f"file{idx}") if per_file else rundir
        if not os.path.exists(unit_rundir): os.makedirs(unit_rundir)
        header = f"input file {idx+1} / {len(units)}: {unit[0]}" if per_file else None

        # copy the cmsRun config to the running directory (as config.py)
        if os.path.abspath(config_path) != os.path.abspath(os.path.join(unit_rundir, "config.py")):
            shutil.copy(config_path, os.path.join(unit_rundir, "config.py"))

        # run cmsRun
        error = _run_logged(["cmsRun", "config.py"], unit_rundir, cmsrun_log_path, "cmsRun",
            append=(idx > 0), header=header)
        if error is not None:
            return {"loss": 1e6, "status": "fail", "error": error}

        # run efficiency calculation
        # (for the processing per input file: into a temporary output directory, combined below)
        unit_outputdir = os.path.join(unit_rundir, "efficiency") if per_file else outputdir
        cmd = get_efficiency_command(context, "hgcalreco_out.root", unit_outputdir)
        error = _run_logged(cmd, unit_rundir, efficiency_log_path, "Efficiency calculation",
            append=(idx > 0), header=header)
        if error is not None:
            return {"loss": 1e6, "status": "fail", "error": error}
        partdirs.append(unit_outputdir)

        # remove root file (to save disk space when running many trials),
        # or copy it back to workdir if requested and rundir is a separate (temporary)
        # directory, since it would otherwise be lost once that directory is cleaned up.
        reco_name = f"hgcalreco_out_file{idx}.root" if per_file else "hgcalreco_out.root"
        output_reco_files.append(os.path.join(workdir, reco_name))
        reco_path = os.path.join(unit_rundir, "hgcalreco_out.root")
        if keep_root_output:
            if os.path.abspath(reco_path) != os.path.abspath(os.path.join(workdir, reco_name)):
                try: shutil.copy(reco_path, os.path.join(workdir, reco_name))
                except OSError:
                    print(f'WARNING: could not copy {reco_path} back to workdir.')
        else:
            try: os.remove(reco_path)
            except OSError:
                print(f'WARNING: could not remove {reco_path}.')

    # combine the efficiency outputs of the separate input files
    if per_file:
        try: combine_efficiency_outputs(partdirs, outputdir)
        except Exception as e:
            error_msg = f"Combining the per-file efficiency outputs failed: {e}"
            print(error_msg, file=sys.stderr)
            return {"loss": 1e6, "status": "fail", "error": error_msg}

    # clean up the temporary running directory itself (e.g. its copy of config.py).
    # on a condor job this is harmless either way (the whole scratch area is wiped
    # when the job ends), but matters for repeated local/interactive runs.
    if rundir != workdir:
        shutil.rmtree(rundir, ignore_errors=True)
    elif per_file:
        for idx in range(len(units)): shutil.rmtree(os.path.join(rundir, f"file{idx}"), ignore_errors=True)

    # metric extraction
    # (the output files are named metrics_<reco>_<truth>.parquet and metrics_<truth>_<reco>.parquet,
    # with reco = lc or tc and truth = the truth object type, e.g. truthbranch-signal or cp)
    efficiency_level = context.get("efficiency_level", "both")
    gen_levels = context.get("efficiency_gen_level", DEFAULT_GEN_LEVELS)
    gen_levels = [g for gen_level in gen_levels for g in (["cp", "sc"] if gen_level == "both" else [gen_level])]
    reco_levels = {"tc": ["tc"], "lc": ["lc"], "both": ["lc", "tc"]}[efficiency_level]
    def get_metrics_files(reco_level, gen_level):
        return (os.path.join(outputdir, f"metrics_{reco_level}_{gen_level}.parquet"),
                os.path.join(outputdir, f"metrics_{gen_level}_{reco_level}.parquet"))
    output_metrics_files = [f for reco_level in reco_levels for gen_level in gen_levels
                            for f in get_metrics_files(reco_level, gen_level)]

    # main metric: for the first truth object type,
    # at LayerCluster level (if requested), else at TICLCandidate level
    if efficiency_level == "tc":
        metric = extract_tc_metric(*get_metrics_files("tc", gen_levels[0]))
    else:
        metric = extract_metric(*get_metrics_files("lc", gen_levels[0]))

    # TICLCandidate-level metric per truth object type
    metrics = {}
    if efficiency_level in ["tc", "both"]:
        for gen_level in gen_levels:
            metrics[gen_level] = extract_tc_metric(*get_metrics_files("tc", gen_level))
    if context.get("efficiency_do_composition", False):
        output_metrics_files.append(os.path.join(outputdir, "metrics_event_lc.parquet"))

    return {
        "loss": -metric,
        "status": "ok",
        "metric": metric,
        "metrics": metrics,
        "params": params,
        "output_reco_file": output_reco_files[0] if len(output_reco_files) == 1 else output_reco_files,
        "output_metrics_files": output_metrics_files
    }


def extract_metric(results_lc, results_truth):
    """
    Calculate simple scalar metric from dataframes with results
    for LayerClusters and truth objects (e.g. truth Branches or CaloParticles).
    """
    # simple placeholder for now, to extend later

    # read input file(s) if needed
    if isinstance(results_lc, str):
        results_lc = pd.read_parquet(results_lc)
    if isinstance(results_truth, str):
        results_truth = pd.read_parquet(results_truth)

    if len(results_lc) == 0 or len(results_truth) == 0:
        return 0.

    # calculate metrics
    lc_pur_avg = np.mean(results_lc['pur'].values)
    lc_eff_avg = np.mean(results_lc['eff'].values)
    truth_eff_avg = np.mean(results_truth['eff'].values)
    layers = results_lc['layer'].values
    eventids = results_lc['event'].values
    counts_per_layer = get_layer_counts(layers, eventids=eventids, absolute=True)
    counts_per_layer_avg = np.mean(list(counts_per_layer.values())) / 40.

    # combine them into a single metric
    metric = (lc_pur_avg + lc_eff_avg + truth_eff_avg)/3.
    if not np.isfinite(metric):
        return 0.
    #metric = lc_pur_avg * lc_eff_avg * truth_eff_avg
    #metric = (lc_pur_avg + lc_eff_avg + truth_eff_avg + (1-counts_per_layer_avg)) / 4.

    # printouts for testing
    '''print()
    print(lc_pur_avg)
    print(lc_eff_avg)
    print(truth_eff_avg)
    print(counts_per_layer_avg)
    print(metric)
    print()'''

    return metric


def extract_tc_metric(results_tc, results_truth_tc):
    """
    Calculate a scalar metric from TICLCandidate-level association results
    (for TICLCandidates and truth objects, e.g. truth Branches or CaloParticles).
    """

    if isinstance(results_tc, str):
        results_tc = pd.read_parquet(results_tc)
    if isinstance(results_truth_tc, str):
        results_truth_tc = pd.read_parquet(results_truth_tc)

    if len(results_tc) == 0 or len(results_truth_tc) == 0:
        return 0.

    tc_pur_avg = np.mean(results_tc['pur'].values)
    tc_eff_avg = np.mean(results_tc['eff'].values)
    truth_eff_avg = np.mean(results_truth_tc['eff_primary'].values)
    metric = (tc_pur_avg + tc_eff_avg + truth_eff_avg)/3.
    if not np.isfinite(metric):
        return 0.
    return metric
