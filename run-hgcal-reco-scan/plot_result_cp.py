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

import analysis.efficiency.plot_metrics_lc as plot_metrics_lc
import analysis.efficiency.plot_metrics_cp as plot_metrics_cp


def get_cp_result_from_df(df):
    '''
    Get CaloParticle results from an appropriate dataframe.
    The dataframe is supposed to contain the keys "layer", "res" and "eff".
    The output is a dict of the following form:
        {
            "num": counts per layer,
            "res": response per layer,
            "eff": efficiency per layer
        }
    '''

    # counts vs layer number
    counts_per_layer = plot_metrics_lc.get_counts_per_layer(df, per_event=True, absolute=True)

    # response and efficiency vs layer number
    response_per_layer = plot_metrics_cp.get_response_per_layer(df, absolute=True)
    efficiency_per_layer = plot_metrics_cp.get_efficiency_per_layer(df, absolute=True)

    # collect results
    result = {
        'num': counts_per_layer,
        'res': response_per_layer,
        'eff': efficiency_per_layer
    }

    return result


def plot_cp_result(result, outputdir, params=None, legend_dict=None):

    # make output directory
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # make color dict
    cmap = mpl.colormaps['cool']
    cvals = np.linspace(0, 1, num=len(result))
    colordict = {key: cmap(cval) for key, cval in zip(result.keys(), cvals)}
    if len(result) == 1: colordict = {list(result.keys())[0]: 'dodgerblue'}
    
    # make label dict
    if legend_dict is None: legend_dict = {}
    labeldict = {key: legend_dict.get(key, key) for key in result.keys()}
    if params is not None:
        for key in params.keys():
            this_params = {}
            for p, v in params[key].items():
                param_key = legend_dict.get(p, p)
                value = '{:.2e}'.format(v)
                this_params[param_key] = value
            labeldict[key] = ', '.join([f'{k} = {v}' for k, v in this_params.items()])

    # optional: limit keys to put in legend
    if len(labeldict) > 10:
        for idx, (key, val) in enumerate(labeldict.items()):
            if idx%2 == 0: continue
            labeldict[key] = None

    # make global plot of counts vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in result.keys():
        fig, ax = plot_metrics_lc.plot_counts_per_layer(result[key]['num'],
                        per_event = True,
                        fig=fig, ax=ax,
                        linewidth=3,
                        color=colordict[key],
                        label=labeldict[key])
    fig, ax = plot_metrics_lc.add_subdetector_labels(fig, ax)
    if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    figname = os.path.join(outputdir, f'cp_counts_vs_layer.png')
    fig.savefig(figname)
    print(f'Created figure {figname}')

    # make global plot of response vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in result.keys():
        fig, ax = plot_metrics_cp.plot_response_per_layer(result[key]['res'],
                        fig=fig, ax=ax,
                        linewidth=3,
                        color=colordict[key],
                        label=labeldict[key],
                        doerrs=False)
    fig, ax = plot_metrics_lc.add_subdetector_labels(fig, ax)
    ax.set_ylim((0, 1.2))
    if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    figname = os.path.join(outputdir, f'cp_response_vs_layer.png')
    fig.savefig(figname)
    print(f'Created figure {figname}')

    # make global plot of efficiency vs layer number
    fig, ax = plt.subplots(figsize=(12,6))
    for key in result.keys():
        fig, ax = plot_metrics_cp.plot_efficiency_per_layer(result[key]['eff'],
                        fig=fig, ax=ax,
                        linewidth=3,
                        color=colordict[key],
                        label=labeldict[key],
                        doerrs=False)
    fig, ax = plot_metrics_lc.add_subdetector_labels(fig, ax) 
    ax.set_ylim((0, 1.2))
    if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
    fig.tight_layout()
    figname = os.path.join(outputdir, f'cp_efficiency_vs_layer.png')
    fig.savefig(figname)
    print(f'Created figure {figname}')


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]
    paramfile = None if len(sys.argv)==2 else sys.argv[2]
    outputdir = os.path.splitext(inputfile)[0] + '_plots'
    
    # read dataframe and parameters
    df = pd.read_parquet(inputfile)
    params = None
    if paramfile is not None:
        with open(paramfile, 'r') as f:
            params = json.load(f)

    # get and plot result
    result = get_cp_result_from_df(df)
    result = {'_': result}
    plot_cp_result(result, outputdir, params=params)
