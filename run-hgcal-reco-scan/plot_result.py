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

import analysis.efficiency.plot_associations as plot


if __name__=='__main__':

    # read input directory from command line
    inputdir = sys.argv[1]

    # check existence
    if not os.path.exists(inputdir):
        raise Exception(f'Input directory {inputdir} does not exist.')

    # make a dict translating param names to legend entries
    # (maybe later put in a json file)
    legend_dict = {
        'critical_density_high': r'$\rho_{c, high}$',
        'critical_density_had': r'$\rho_{c, had}$',
        'critical_distance_high': r'$d_{c, high}$',
        'critical_distance_had': r'$d_{c, had}$',
        'density_distance_high': r'$d_{\rho, high}$',
        'density_distance_had': r'$d_{\rho, had}$',
    }

    # make output directory
    outputdir = os.path.join(inputdir, 'plots')
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # loop over job directories and gather results
    results = {}
    params = {}
    jobdirs = [d for d in os.listdir(inputdir) if fnmatch(d, 'job*')]
    for idx, jobdir in enumerate(jobdirs):
        print(f'Now plotting {jobdir} ({idx+1} / {len(jobdirs)})', end='\r')
        
        # load dataframe
        inputfile = os.path.join(inputdir, jobdir, 'efficiency.parquet')
        df = pd.read_parquet(inputfile)

        # load parameters
        with open(os.path.join(inputdir, jobdir, 'params.json'), 'r') as f:
            paramdict = json.load(f)

        # make plots of individual runs

        # counts vs layer number
        counts_per_layer = plot.get_counts_per_layer(df)
        fig, ax = plot.plot_counts_per_layer(counts_per_layer)
        fig.savefig(os.path.join(outputdir, f'counts_vs_layer_{jobdir}.png'))

        # purity and efficiency vs layer number
        purity_per_layer = plot.get_purity_per_layer(df)
        efficiency_per_layer = plot.get_efficiency_per_layer(df)
        fig, ax = plot.plot_effandpur_per_layer(efficiency_per_layer, purity_per_layer)
        fig.savefig(os.path.join(outputdir, f'effandpur_vs_layer_{jobdir}.png'))

        # close all open plots
        plt.close()

        # collect results
        results[jobdir] = {
            'num': counts_per_layer,
            'pur': purity_per_layer,
            'eff': efficiency_per_layer
        }
        params[jobdir] = paramdict

    # make color dict
    cmap = mpl.colormaps['cool']
    cvals = np.linspace(0, 1, num=len(jobdirs))
    colordict = {jobdir: cmap(cval) for jobdir, cval in zip(jobdirs, cvals)}
    
    # make label dict
    labeldict = {}
    for jobdir in jobdirs:
        this_params = {}
        for p, v in params[jobdir].items():
            key = legend_dict.get(p, p)
            value = '{:.2e}'.format(v)
            this_params[key] = value
        labeldict[jobdir] = ', '.join([f'{k} = {v}' for k, v in this_params.items()])

    # make global plot of counts vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in jobdirs:
        fig, ax = plot.plot_counts_per_layer(results[key]['num'], fig=fig, ax=ax,
                    color=colordict[key], label=labeldict[key])
    ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    fig.savefig(os.path.join(outputdir, f'counts_vs_layer.png'))

    # make global plot of purity vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in jobdirs:
        fig, ax = plot.plot_purity_per_layer(results[key]['pur'], fig=fig, ax=ax,
                    color=colordict[key], label=labeldict[key], doerrs=False)
    ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    fig.savefig(os.path.join(outputdir, f'purity_vs_layer.png'))

    # make global plot of efficiency vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in jobdirs:
        fig, ax = plot.plot_efficiency_per_layer(results[key]['eff'], fig=fig, ax=ax,
                    color=colordict[key], label=labeldict[key], doerrs=False)
    ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    fig.savefig(os.path.join(outputdir, f'efficiency_vs_layer.png'))
