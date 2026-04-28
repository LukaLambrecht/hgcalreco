import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(topdir)

from analysis.efficiency.plot_metrics_lc import get_counts_per_layer
from analysis.efficiency.plot_metrics_lc import get_quantity_per_layer
from analysis.efficiency.plot_metrics_lc import plot, plot_counts_per_layer
from analysis.efficiency.plot_metrics_lc import add_subdetector_labels


def get_response_per_layer(df, **kwargs):
    return get_quantity_per_layer(df, 'res', **kwargs)

def get_efficiency_per_layer(df, **kwargs):
    return get_quantity_per_layer(df, 'eff', **kwargs)

def plot_response_per_layer(response_per_layer, **kwargs):
    # plot response vs layer number
    xvals = np.array(list(response_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in response_per_layer.values()])
    yerrs = np.array([v[1] for v in response_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs=yerrs, cliperrs=(0, 1),
                xlabel='Layer number', ylabel='CaloParticle response',
                **kwargs)
    ax.axhline(y=1, color='grey', linestyle='--')
    ax.set_xlim((0, 47))
    return fig, ax

def plot_efficiency_per_layer(efficiency_per_layer, **kwargs):
    # plot efficiency vs layer number
    xvals = np.array(list(efficiency_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in efficiency_per_layer.values()])
    yerrs = np.array([v[1] for v in efficiency_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs=yerrs, cliperrs=(0, 1),
                xlabel='Layer number', ylabel='CaloParticle efficiency',
                **kwargs)
    ax.axhline(y=1, color='grey', linestyle='--')
    ax.set_xlim((0, 47))
    return fig, ax


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # set output dir
    outputdir = os.path.splitext(inputfile)[0]+'_plots'
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # load dataframe
    df = pd.read_parquet(inputfile)
    print(df)

    # temp: printouts for testing
    '''
    layers = df['layer'].values
    print(layers, len(layers))
    print(np.unique(layers), len(np.unique(layers)))
    for layer in np.unique(np.abs(layers)):
        values = df[np.abs(df['layer'].values)==layer]['eff'].values
        print(layer, values, np.mean(values), np.std(values))
    '''

    # make plots
    # (todo: make configurable)

    # counts vs layer number
    counts_per_layer = get_counts_per_layer(df, per_event=True, absolute=True)
    fig, ax = plot_counts_per_layer(counts_per_layer, per_event=True)
    fig, ax = add_subdetector_labels(fig, ax)
    fig.tight_layout()
    figname = os.path.join(outputdir, 'counts_vs_layer.png')
    fig.savefig(figname)

    # response vs layer number
    response_per_layer = get_response_per_layer(df, absolute=True)
    fig, ax = plot_response_per_layer(response_per_layer, doerrs=False)
    fig, ax = add_subdetector_labels(fig, ax)
    fig.tight_layout()
    figname = os.path.join(outputdir, 'response_vs_layer.png')
    fig.savefig(figname)

    # response vs layer number
    efficiency_per_layer = get_efficiency_per_layer(df, absolute=True)
    fig, ax = plot_efficiency_per_layer(efficiency_per_layer, doerrs=False)
    fig, ax = add_subdetector_labels(fig, ax)
    fig.tight_layout()
    figname = os.path.join(outputdir, 'efficiency_vs_layer.png')
    fig.savefig(figname)
