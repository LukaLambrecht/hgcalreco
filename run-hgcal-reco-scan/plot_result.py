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

import analysis.efficiency.plot_metrics_lc as plot


def get_result_from_df(df):
        
    # define subdetector masks
    subdet_masks = {
        'all': np.ones(len(df)).astype(bool),
        'EE': (df['subdet'].values==0).astype(bool),
        'HSi': (df['subdet'].values==1).astype(bool),
        'HSci': (df['subdet'].values==2).astype(bool),
    }

    # loop over subdetectors
    result = {}
    for subdet_name, subdet_mask in subdet_masks.items():

        # select data
        thisdf = df[subdet_mask]

        # counts vs layer number
        counts_per_layer = plot.get_counts_per_layer(thisdf, per_event=True, absolute=True)

        # purity and efficiency vs layer number
        purity_per_layer = plot.get_purity_per_layer(thisdf, absolute=True)
        efficiency_per_layer = plot.get_efficiency_per_layer(thisdf, absolute=True)

        # collect results
        result[subdet_name] = {
            'num': counts_per_layer,
            'pur': purity_per_layer,
            'eff': efficiency_per_layer
        }

    return result


def plot_result(result, outputdir, params=None, legend_dict=None):

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

    # loop over subdetectors
    subdet_names = list(list(result.values())[0].keys()) # assume the same for all entries
    for subdet_name in subdet_names:

        # make global plot of counts vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in result.keys():
            fig, ax = plot.plot_counts_per_layer(result[key][subdet_name]['num'],
                        per_event = True,
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key])
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'counts_vs_layer_{subdet_name}.png')
        fig.savefig(figname)
        print(f'Created figure {figname}')

        # make global plot of purity vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in result.keys():
            fig, ax = plot.plot_purity_per_layer(result[key][subdet_name]['pur'],
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key], doerrs=False)
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        ax.set_ylim((0, 1.2))
        if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'purity_vs_layer_{subdet_name}.png')
        fig.savefig(figname)
        print(f'Created figure {figname}')

        # make global plot of efficiency vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in result.keys():
            fig, ax = plot.plot_efficiency_per_layer(result[key][subdet_name]['eff'],
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key], doerrs=False)
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        ax.set_ylim((0, 1.2))
        if len(result) > 1: ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'efficiency_vs_layer_{subdet_name}.png')
        fig.savefig(figname)
        print(f'Created figure {figname}')

        # make global plot of purity and efficiency vs layer number
        # (only when only 1 result is being plotted, not many together)
        if len(result) == 1:
            fig, ax = plt.subplots(figsize=(12,6))
            for key in result.keys():
                fig, ax = plot.plot_efficiency_per_layer(result[key][subdet_name]['pur'],
                        fig=fig, ax=ax,
                        color='dodgerblue', label='Purity', doerrs=False)
                fig, ax = plot.plot_efficiency_per_layer(result[key][subdet_name]['eff'],
                        fig=fig, ax=ax,
                        color='mediumorchid', label='Efficiency', doerrs=False)
            fig, ax = plot.add_subdetector_labels(fig, ax)
            ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
                va='top', transform=ax.transAxes, fontsize=15)
            ax.set_ylim((0, 1.2))
            ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
            fig.tight_layout()
            figname = os.path.join(outputdir, f'effandpur_vs_layer_{subdet_name}.png')
            fig.savefig(figname)
            print(f'Created figure {figname}')

        plt.close()


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
    result = get_result_from_df(df)
    result = {'_': result}
    plot_result(result, outputdir, params=params)
