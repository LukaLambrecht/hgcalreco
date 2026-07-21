import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from fnmatch import fnmatch

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from plot_result_lc import get_lc_result_from_df
from plot_result_lc import plot_lc_result
from plot_result_cp import get_cp_result_from_df
from plot_result_cp import plot_cp_result
from plot_result_tc import plot_tc_result
from plot_result_tc import plot_cp_tc_result


def read_nonempty_parquet(path):
    if not os.path.exists(path):
        print(f'WARNING: file {path} does not exist, skipping...')
        return None
    df = pd.read_parquet(path)
    if len(df) == 0:
        print(f'WARNING: file {path} is empty, skipping...')
        return None
    return df


def load_metric(jobdir):
    resultfile = os.path.join(jobdir, 'result.json')
    if not os.path.exists(resultfile):
        return np.nan
    with open(resultfile, 'r') as f:
        result = json.load(f)
    if result.get('status') != 'ok':
        return np.nan
    if 'loss' in result:
        return result['loss']
    if 'metric' in result:
        return -result['metric']
    return np.nan


def main(inputdir):

    # check existence
    if not os.path.exists(inputdir):
        raise Exception(f'Input directory {inputdir} does not exist.')

    # make a dict translating param names to legend entries
    # (maybe later put in a json file)
    legend_dict = {
        'critical_density': r'$\rho_{c}$',
        'critical_distance': r'$d_{c}$',
        'density_distance': r'$d_{\rho}$',
        'kernel_density': r'$\rho_{kernel}$',
        'deltac_ee': r'$\delta_c (EE)$',
        'deltac_hsi': r'$\delta_c (HSi)$',
        'deltac_hsci': r'$\delta_c (HSci)$',
        'deltac_all': r'$\delta_c (all)$',
        'ecut_hsi': r'$E_{cut} (HSi)$',
        'kappa_hsi': r'$\rho_{seed} (HSi)$'
    }

    # make output directory
    outputdir = os.path.join(inputdir, 'plots')
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # loop over job directories
    results_lc = {}
    results_cp_lc = {}
    results_tc = {}
    results_cp_tc = {}
    params = {}
    losses = {}
    jobdirs = [d for d in os.listdir(inputdir) if fnmatch(d, 'job*')]
    jobdirs = sorted(jobdirs, key=lambda d: int(d.replace('job', '')) if d.replace('job', '').isdigit() else d)
    for idx, jobdir in enumerate(jobdirs):
        print(f'Retrieving results for {jobdir} ({idx+1} / {len(jobdirs)})', end='\r')
        jobpath = os.path.join(inputdir, jobdir)

        paramfile = os.path.join(jobpath, 'params_summary.json')
        if not os.path.exists(paramfile):
            print(f'WARNING: file {paramfile} does not exist, skipping job...')
            continue
        with open(paramfile, 'r') as f:
            paramdict = json.load(f)
        params[jobdir] = paramdict
        losses[jobdir] = load_metric(jobpath)

        # load dataframe for layerclusters and get results, if available
        df_lc = read_nonempty_parquet(os.path.join(jobpath, 'efficiency', 'metrics_lc.parquet'))
        if df_lc is not None:
            results_lc[jobdir] = get_lc_result_from_df(df_lc)

        # load dataframe for caloparticle-vs-layercluster metrics, if available
        df_cp_lc = read_nonempty_parquet(os.path.join(jobpath, 'efficiency', 'metrics_cp_lc.parquet'))
        if df_cp_lc is not None:
            if 'res' not in df_cp_lc.columns:
                df_cp_lc['res'] = 0
            results_cp_lc[jobdir] = get_cp_result_from_df(df_cp_lc)

        # TICLCandidate metrics are stored directly as dataframes, because the
        # scan-level plotter overlays their distributions across grid points.
        df_tc = read_nonempty_parquet(os.path.join(jobpath, 'efficiency', 'metrics_tc.parquet'))
        if df_tc is not None:
            results_tc[jobdir] = df_tc

        df_cp_tc = read_nonempty_parquet(os.path.join(jobpath, 'efficiency', 'metrics_cp_tc.parquet'))
        if df_cp_tc is not None:
            results_cp_tc[jobdir] = df_cp_tc

    # plot results
    if len(results_lc) > 0:
        plot_lc_result(results_lc, outputdir, params=params, legend_dict=legend_dict)
    else:
        print('No non-empty LayerCluster metric files found; skipping LayerCluster plots.')

    if len(results_cp_lc) > 0:
        plot_cp_result(results_cp_lc, outputdir, params=params, legend_dict=legend_dict)
    else:
        print('No non-empty CaloParticle-LayerCluster metric files found; skipping CaloParticle-LC plots.')

    if len(results_tc) > 0:
        plot_tc_result(results_tc, outputdir, params=params, legend_dict=legend_dict)
    else:
        print('No non-empty TICLCandidate metric files found; skipping TICLCandidate plots.')

    if len(results_cp_tc) > 0:
        plot_cp_tc_result(results_cp_tc, outputdir, params=params, legend_dict=legend_dict)
    else:
        print('No non-empty CaloParticle-TICLCandidate metric files found; skipping CP-TC plots.')

    jobdirs = list(params.keys()) # in case some directories got skipped
    if len(jobdirs) == 0:
        print('No jobs with parameter summaries found; skipping metric scan plot.')
        return

    # in case only 1 parameter was scanned, can plot metric vs this variable
    nparams = len(params[jobdirs[0]]) # assume it's the same for all job directories
    if nparams == 1:

        # retrieve param values
        param_name = list(params[jobdirs[0]].keys())[0]
        param_values = np.array([params[jobdir][param_name] for jobdir in jobdirs])
        loss_values = np.array([losses[jobdir] for jobdir in jobdirs])
        finite_mask = np.isfinite(param_values) & np.isfinite(loss_values)
        param_values = param_values[finite_mask]
        loss_values = loss_values[finite_mask]
        if len(param_values) == 0:
            print('No finite metric values found; skipping metric scan plot.')
            return

        # sort
        sorted_ids = np.argsort(param_values)
        param_values = param_values[sorted_ids]
        loss_values = loss_values[sorted_ids]

        # plot
        fig, ax = plt.subplots()
        ax.scatter(param_values, loss_values, c='dodgerblue')
        ax.set_xlabel(legend_dict.get(param_name, param_name), fontsize=15)
        ax.set_ylabel('Loss value', fontsize=15)
        ax.grid()
        fig.tight_layout()
        figname = os.path.join(outputdir, f'metric_vs_{param_name}.png')
        fig.savefig(figname)
        print(f'Created figure {figname}.')

        # same with x-axis in log scale
        ax.set_xscale('log')
        fig.tight_layout()
        figname = os.path.join(outputdir, f'metric_vs_{param_name}_log.png')
        fig.savefig(figname)
        print(f'Created figure {figname}.')
        plt.close()


if __name__=='__main__':

    # read input directory from command line
    inputdirs = sys.argv[1:]

    for inputdir in inputdirs:
        print(f'Running on {inputdir}')
        main(inputdir)
