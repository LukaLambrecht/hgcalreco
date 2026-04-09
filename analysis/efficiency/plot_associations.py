import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

def plot(xbins, yvals, yerrs=None,
    doerrs=True,
    xlabel=None, ylabel=None,
    color='dodgerblue', label=None,
    cliperrs=None,
    fig=None, ax=None):
    # basic plotting function
    
    if fig is None or ax is None:
        fig, ax = plt.subplots()
        ax.grid()
    ax.stairs(yvals, edges=xbins, linewidth=2, color=color, label=label)
    if yerrs is not None and doerrs:
        upper = yvals + yerrs
        lower = yvals - yerrs
        if cliperrs is not None:
            upper = np.clip(upper, a_min=cliperrs[0], a_max=cliperrs[1])
            lower = np.clip(lower, a_min=cliperrs[0], a_max=cliperrs[1])
        ax.stairs(upper, baseline=lower, edges=xbins, fill=True, color=color, alpha=0.2)
    if xlabel is not None: ax.set_xlabel(xlabel, fontsize=15)
    if ylabel is not None: ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    return (fig, ax)

def add_subdetector_labels(fig, ax):
    ax.axvline(x=26.5, linestyle='--', color='grey')
    ax.axvline(x=33.5, ymax=0.9, linestyle='--', color='grey')
    transform = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    ax.text(13, 0.95, 'EE', ha='center', va='top', transform=transform, fontsize=15, color='grey')
    ax.text(30, 0.95, 'HSi', ha='center', va='top', transform=transform, fontsize=15, color='grey')
    ax.text(40, 0.95, 'HSci', ha='center', va='top', transform=transform, fontsize=15, color='grey')
    ax.set_ylim((ax.get_ylim()[0], ax.get_ylim()[1]*1.3))
    return (fig, ax)

def get_counts_per_layer(df, absolute=False):
    # count instances per layer
    counts_per_layer = {}
    layers = df['layer'].values
    if absolute: layers = np.abs(layers)
    unique_layers = sorted(np.unique(layers))
    for layer in unique_layers:
        mask = (layers == layer).astype(int)
        counts_per_layer[layer] = np.sum(mask)
    return counts_per_layer

def get_quantity_per_layer(df, column, absolute=False):
    # get a quantity vs layer number
    quantity_per_layer = {}
    layers = df['layer'].values
    if absolute: layers = np.abs(layers)
    unique_layers = sorted(np.unique(layers))
    for layer in unique_layers:
        mask = (layers == layer).astype(bool)
        values = df[column].values[mask]
        mean = np.mean(values)
        std = np.std(values)
        #mean = np.median(values)
        #std = np.quantile(values, 0.84) - np.quantile(values, 0.16)
        quantity_per_layer[layer] = (mean, std)
    
    return quantity_per_layer

def get_purity_per_layer(df, **kwargs):
    return get_quantity_per_layer(df, 'pur', **kwargs)

def get_efficiency_per_layer(df, **kwargs):
    return get_quantity_per_layer(df, 'eff', **kwargs)

def plot_counts_per_layer(counts_per_layer, **kwargs):
    # plot counts vs layer number
    xvals = np.array(list(counts_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array(list(counts_per_layer.values()))
    yerrs = np.sqrt(yvals)
    fig, ax = plot(xbins, yvals, yerrs=yerrs,
                xlabel='Layer number', ylabel='Number of reconstructed LayerClusters',
                **kwargs)
    return fig, ax

def plot_purity_per_layer(purity_per_layer, **kwargs):
    # plot purity vs layer number
    xvals = np.array(list(purity_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in purity_per_layer.values()])
    yerrs = np.array([v[1] for v in purity_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs=yerrs, cliperrs=(0,1),
                xlabel='Layer number', ylabel='Average purity',
                **kwargs)
    ax.axhline(y=1, color='grey', linestyle='dashed')
    ax.set_ylim((0, 1.2))
    return fig, ax

def plot_efficiency_per_layer(efficiency_per_layer, **kwargs):
    # plot efficiency vs layer number
    xvals = np.array(list(efficiency_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in efficiency_per_layer.values()])
    yerrs = np.array([v[1] for v in efficiency_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs=yerrs, cliperrs=(0,1),
                xlabel='Layer number', ylabel='Average efficiency',
                **kwargs)
    ax.axhline(y=1, color='grey', linestyle='dashed')
    ax.set_ylim((0, 1.2))
    return fig, ax

def plot_effandpur_per_layer(efficiency_per_layer, purity_per_layer, **kwargs):
    # plot both efficiency and purity vs layer number
    xvals = np.array(list(purity_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in purity_per_layer.values()])
    yerrs = np.array([v[1] for v in purity_per_layer.values()])
    fig, ax = plot(xbins, yvals,
                color='dodgerblue', label='Purity',
                xlabel='Layer number', ylabel='Average efficiency / purity',
                **kwargs)
    xvals = np.array(list(efficiency_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in efficiency_per_layer.values()])
    yerrs = np.array([v[1] for v in efficiency_per_layer.values()])
    fig, ax = plot(xbins, yvals, fig=fig, ax=ax,
                color='darkorchid', label='Efficiency',
                **kwargs)
    ax.axhline(y=1, color='grey', linestyle='dashed')
    ax.set_ylim((0, 1.2))
    ax.legend(fontsize=12)
    return fig, ax


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # load dataframe
    df = pd.read_parquet(inputfile)
    print(df)

    # make plots
    # (todo: make configurable)

    # counts vs layer number
    counts_per_layer = get_counts_per_layer(df)
    fig, ax = plot_counts_per_layer(counts_per_layer)
    fig.savefig('counts_vs_layer.png')

    # purity vs layer number
    purity_per_layer = get_purity_per_layer(df)
    fig, ax = plot_purity_per_layer(purity_per_layer)
    fig.savefig('purity_vs_layer.png')

    # efficiency vs layer number
    efficiency_per_layer = get_efficiency_per_layer(df)
    fig, ax = plot_efficiency_per_layer(efficiency_per_layer)
    fig.savefig('efficiency_vs_layer.png')

    # purity and efficiency together vs layer number
    fig, ax = plot_effandpur_per_layer(efficiency_per_layer, purity_per_layer)
    fig.savefig('effandpur_vs_layer.png')
