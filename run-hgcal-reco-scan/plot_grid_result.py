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

from plot_result import get_result_from_df
from plot_result import plot_result


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
        'deltac_hsci': r'$\delta_c (HSci)$'
    }

    # make output directory
    outputdir = os.path.join(inputdir, 'plots')
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # loop over job directories
    results = {}
    params = {}
    jobdirs = [d for d in os.listdir(inputdir) if fnmatch(d, 'job*')]
    for idx, jobdir in enumerate(jobdirs):
        print(f'Now plotting {jobdir} ({idx+1} / {len(jobdirs)})', end='\r')

        # load dataframe
        inputfile = os.path.join(inputdir, jobdir, 'efficiency', 'metrics_lc.parquet')
        if not os.path.exists(inputfile):
            msg = f'WARNING: file {inputfile} does not exist, skipping...'
            print(msg)
            continue
        df = pd.read_parquet(inputfile)

        # load parameters
        with open(os.path.join(inputdir, jobdir, 'params_summary.json'), 'r') as f:
            paramdict = json.load(f)
        params[jobdir] = paramdict

        # gather results
        results[jobdir] = get_result_from_df(df)

    # plot results
    plot_result(results, outputdir, params=params, legend_dict=legend_dict)


if __name__=='__main__':

    # read input directory from command line
    inputdirs = sys.argv[1:]

    for inputdir in inputdirs:
        print(f'Running on {inputdir}')
        main(inputdir)
