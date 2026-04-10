import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

from plot_metrics_lc import get_quantity_per_layer, plot
from plot_metrics_lc import add_subdetector_labels


def get_response_per_layer(df, **kwargs):
    return get_quantity_per_layer(df, 'res', **kwargs)

def plot_response_per_layer(response_per_layer, **kwargs):
    # plot response vs layer number
    xvals = np.array(list(response_per_layer.keys()))
    xbins = np.concatenate((xvals - 0.5, [xvals[-1]+0.5]))
    yvals = np.array([v[0] for v in response_per_layer.values()])
    yerrs = np.array([v[1] for v in response_per_layer.values()])
    fig, ax = plot(xbins, yvals, yerrs=yerrs,
                xlabel='Layer number', ylabel='Response',
                **kwargs)
    return fig, ax


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # load dataframe
    df = pd.read_parquet(inputfile)
    print(df)

    # make plots
    # (todo: make configurable)

    # response vs layer number
    response_per_layer = get_response_per_layer(df, absolute=True)
    fig, ax = plot_response_per_layer(response_per_layer)
    fig, ax = add_subdetector_labels(fig, ax)
    fig.tight_layout()
    fig.savefig('response_vs_layer.png')
