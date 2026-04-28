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

from tools.hgcalrecotools import extract_metric
from plot_result_lc import get_lc_result_from_df
from plot_result_lc import plot_lc_result
from plot_result_cp import get_cp_result_from_df
from plot_result_cp import plot_cp_result


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
        'ecut_hsi': r'$E_{cut} (HSi)$',
        'kappa_hsi': r'$\rho_{seed} (HSi)$'
    }

    # make output directory
    outputdir = os.path.join(inputdir, 'plots')
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # loop over job directories
    results_lc = {}
    results_cp = {}
    params = {}
    metrics = {}
    jobdirs = [d for d in os.listdir(inputdir) if fnmatch(d, 'job*')]
    for idx, jobdir in enumerate(jobdirs):
        print(f'Retrieving results for {jobdir} ({idx+1} / {len(jobdirs)})', end='\r')

        # load dataframe for layerclusters and get results
        inputfile = os.path.join(inputdir, jobdir, 'efficiency', 'metrics_lc.parquet')
        if not os.path.exists(inputfile):
            msg = f'WARNING: file {inputfile} does not exist, skipping...'
            print(msg)
            continue
        df_lc = pd.read_parquet(inputfile)
        results_lc[jobdir] = get_lc_result_from_df(df_lc)

        # load dataframe for caloparticles and get results
        inputfile = os.path.join(inputdir, jobdir, 'efficiency', 'metrics_cp.parquet')
        if not os.path.exists(inputfile):
            msg = f'WARNING: file {inputfile} does not exist, skipping...'
            print(msg)
            continue
        df_cp = pd.read_parquet(inputfile)
        results_cp[jobdir] = get_cp_result_from_df(df_cp)

        # calculate metric
        metrics[jobdir] = extract_metric(df_lc, df_cp)

        # load parameters
        with open(os.path.join(inputdir, jobdir, 'params_summary.json'), 'r') as f:
            paramdict = json.load(f)
        params[jobdir] = paramdict

    # plot results
    plot_lc_result(results_lc, outputdir, params=params, legend_dict=legend_dict)
    plot_cp_result(results_cp, outputdir, params=params, legend_dict=legend_dict)

    jobdirs = list(params.keys()) # in case some directories got skipped

    # in case only 1 parameter was scanned, can plot metric vs this variable
    nparams = len(params[jobdirs[0]]) # assume it's the same for all job directories
    if nparams == 1:

        # retrieve param values
        param_name = list(params[jobdirs[0]].keys())[0]
        param_values = np.array([params[jobdir][param_name] for jobdir in jobdirs])
        metric_values = np.array([metrics[jobdir] for jobdir in jobdirs])

        # sort
        sorted_ids = np.argsort(param_values)
        param_values = param_values[sorted_ids]
        metric_values_sorted = metric_values[sorted_ids]

        # plot
        fig, ax = plt.subplots()
        ax.scatter(param_values, -metric_values_sorted, c='dodgerblue')
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
