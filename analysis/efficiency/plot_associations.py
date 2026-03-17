import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot(xbins, yvals, yerrs,
    xlabel=None, ylabel=None):
    
    fig, ax = plt.subplots()
    ax.stairs(yvals, edges=xbins, linewidth=2, color='dodgerblue')
    upper = np.minimum(1, yvals + yerrs)
    lower = np.maximum(0, yvals - yerrs)
    ax.stairs(upper, baseline=lower, edges=xbins, fill=True, color='dodgerblue', alpha=0.2)
    ax.grid()
    if xlabel is not None: ax.set_xlabel(xlabel, fontsize=12)
    if ylabel is not None: ax.set_ylabel(ylabel, fontsize=12)
    return (fig, ax)


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # load dataframe
    df = pd.read_parquet(inputfile)
    print(df)

    # extract common info
    layers = df['layer'].values
    unique_layers = sorted(np.unique(layers))

    # make plots
    # (todo: make configurable)
    
    # purity vs layer number
    purity_per_layer = {}
    for layer in unique_layers:
        ids = (layers == layer).astype(bool)
        values = df['pur'].values[ids]
        mean = np.mean(values)
        std = np.std(values)
        #mean = np.median(values)
        #std = np.quantile(values, 0.84) - np.quantile(values, 0.16)
        purity_per_layer[layer] = (mean, std)
    xvals = np.array(list(purity_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in purity_per_layer.values()])
    yerrs = np.array([v[1] for v in purity_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs,
                xlabel='Layer number', ylabel='Average purity')
    fig.savefig('purity_vs_layer.png')

    # efficiency vs layer number
    efficiency_per_layer = {}
    for layer in unique_layers:
        ids = (layers == layer).astype(bool)
        values = df['eff'].values[ids]
        mean = np.mean(values)
        std = np.std(values)
        #mean = np.median(values)
        #std = np.quantile(values, 0.84) - np.quantile(values, 0.16)
        efficiency_per_layer[layer] = (mean, std)
    xvals = np.array(list(efficiency_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in efficiency_per_layer.values()])
    yerrs = np.array([v[1] for v in efficiency_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs,
                xlabel='Layer number', ylabel='Average efficiency')
    fig.savefig('efficiency_vs_layer.png')
