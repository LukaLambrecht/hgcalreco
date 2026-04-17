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
        inputfile = os.path.join(inputdir, jobdir, 'metrics_lc.parquet')
        if not os.path.exists(inputfile):
            msg = f'WARNING: file {inputfile} does not exist, skipping...'
            print(msg)
            continue
        df = pd.read_parquet(inputfile)

        # define subdetector masks
        subdet_masks = {
            'all': np.ones(len(df)).astype(bool),
            'EE': (df['subdet'].values==0).astype(bool),
            'HSi': (df['subdet'].values==1).astype(bool),
            'HSci': (df['subdet'].values==2).astype(bool),
        }

        # load parameters
        with open(os.path.join(inputdir, jobdir, 'params.json'), 'r') as f:
            paramdict = json.load(f)
        params[jobdir] = paramdict

        # loop over subdetectors
        results[jobdir] = {}
        for subdet_name, subdet_mask in subdet_masks.items():

            # select data
            thisdf = df[subdet_mask]

            # counts vs layer number
            counts_per_layer = plot.get_counts_per_layer(thisdf, per_event=True, absolute=True)

            # purity and efficiency vs layer number
            purity_per_layer = plot.get_purity_per_layer(thisdf, absolute=True)
            efficiency_per_layer = plot.get_efficiency_per_layer(thisdf, absolute=True)

            # collect results
            results[jobdir][subdet_name] = {
                'num': counts_per_layer,
                'pur': purity_per_layer,
                'eff': efficiency_per_layer
            }

    # make color dict
    cmap = mpl.colormaps['cool']
    cvals = np.linspace(0, 1, num=len(jobdirs))
    colordict = {jobdir: cmap(cval) for jobdir, cval in zip(jobdirs, cvals)}
    
    # make label dict
    labeldict = {}
    for jobdir in params.keys():
        this_params = {}
        for p, v in params[jobdir].items():
            key = legend_dict.get(p, p)
            value = '{:.2e}'.format(v)
            this_params[key] = value
        labeldict[jobdir] = ', '.join([f'{k} = {v}' for k, v in this_params.items()])

    # loop over subdetectors
    for subdet_name in subdet_masks.keys():

        # make global plot of counts vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in results.keys():
            fig, ax = plot.plot_counts_per_layer(results[key][subdet_name]['num'],
                        per_event = True,
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key])
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        fig.savefig(os.path.join(outputdir, f'counts_vs_layer_{subdet_name}.png'))

        # make global plot of purity vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in results.keys():
            fig, ax = plot.plot_purity_per_layer(results[key][subdet_name]['pur'],
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key], doerrs=False)
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        ax.set_ylim((0, 1.2))
        ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        fig.savefig(os.path.join(outputdir, f'purity_vs_layer_{subdet_name}.png'))

        # make global plot of efficiency vs layer number
        fig, ax = plt.subplots(figsize=(12,6))
        for key in results.keys():
            fig, ax = plot.plot_efficiency_per_layer(results[key][subdet_name]['eff'],
                        fig=fig, ax=ax,
                        color=colordict[key], label=labeldict[key], doerrs=False)
        fig, ax = plot.add_subdetector_labels(fig, ax)
        ax.text(0.05, 0.8, f'Subdetector:\n{subdet_name}',
            va='top', transform=ax.transAxes, fontsize=15)
        ax.set_ylim((0, 1.2))
        ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1,1))
        fig.tight_layout()
        fig.savefig(os.path.join(outputdir, f'efficiency_vs_layer_{subdet_name}.png'))

        plt.close()


if __name__=='__main__':

    # read input directory from command line
    inputdirs = sys.argv[1:]

    for inputdir in inputdirs:
        print(f'Running on {inputdir}')
        main(inputdir)
