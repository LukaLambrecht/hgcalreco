import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(topdir)

from analysis.efficiency.plot_metrics_lc import plot


def get_quantity_per_bin(df, xcolumn, ycolumn, bins):
    quantity_per_bin = {}
    xvals = df[xcolumn].values
    yvals = df[ycolumn].values

    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (xvals >= lo) & (xvals < hi)
        values = yvals[mask]
        if len(values) == 0:
            quantity_per_bin[(lo, hi)] = (np.nan, np.nan)
        else:
            quantity_per_bin[(lo, hi)] = (np.mean(values), np.std(values))

    return quantity_per_bin


def plot_hist(df, column, bins, xlabel, ylabel, color='dodgerblue', unit_interval=False):
    fig, ax = plt.subplots()
    ax.grid(visible=True, which='both', axis='both')
    values = df[column].values
    if unit_interval:
        values = values.copy()
        values[np.isclose(values, 1., rtol=0., atol=1e-12)] = np.nextafter(1., 0.)
    ax.hist(values, bins=bins, histtype='step', linewidth=3, color=color)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    return fig, ax


def plot_quantity_per_bin(quantity_per_bin, xlabel, ylabel, color='dodgerblue', **kwargs):
    xbins = np.array([key[0] for key in quantity_per_bin.keys()] + [list(quantity_per_bin.keys())[-1][1]])
    yvals = np.array([val[0] for val in quantity_per_bin.values()])
    yerrs = np.array([val[1] for val in quantity_per_bin.values()])
    fig, ax = plot(
        xbins,
        yvals,
        yerrs=yerrs,
        color=color,
        xlabel=xlabel,
        ylabel=ylabel,
        cliperrs=(0, 1),
        **kwargs)
    ax.axhline(y=1, color='grey', linestyle='--')
    return fig, ax


def plot_effandpur_vs(df, xcolumn, bins, xlabel, outputdir, suffix):
    purity_per_bin = get_quantity_per_bin(df, xcolumn, 'pur', bins)
    efficiency_per_bin = get_quantity_per_bin(df, xcolumn, 'eff', bins)

    fig, ax = plot_quantity_per_bin(
        purity_per_bin,
        xlabel=xlabel,
        ylabel='TICLCandidate efficiency / purity',
        color='dodgerblue',
        label='Purity',
        doerrs=False,
        linewidth=3)
    fig, ax = plot(
        bins,
        np.array([val[0] for val in efficiency_per_bin.values()]),
        color='darkorchid',
        label='Efficiency',
        fig=fig,
        ax=ax,
        doerrs=False,
        linewidth=3)
    ax.set_ylim((0, 1.2))
    ax.legend(fontsize=12)
    fig.tight_layout()
    figname = os.path.join(outputdir, f'tc_effandpur_vs_{suffix}.png')
    fig.savefig(figname)
    print(f'Saved figure {figname}.')


def plot_cp_tc_metrics(df, outputdir, truth_label='CaloParticle', file_prefix='cp'):
    if len(df) == 0:
        return

    truth_label_plural = truth_label + 's'
    eff_sum_max = max(1.2, np.quantile(df['eff_sum'].values, 0.98) * 1.1)
    plots = [
        ('eff_primary', np.linspace(0, 1.2, 61), 'Efficiency of primary TICLCandidate', truth_label_plural),
        ('eff_sum', np.linspace(0, eff_sum_max, 61), f'{truth_label} efficiency (total)', truth_label_plural),
        ('pur_primary', np.linspace(0, 1.2, 61), 'Purity of primary TICLCandidate', truth_label_plural),
        ('ntc', np.arange(-0.5, max(5, int(np.max(df['ntc'].values)) + 1.5), 1), f'TICLCandidates per {truth_label}', truth_label_plural),
    ]

    for column, bins, xlabel, ylabel in plots:
        fig, ax = plot_hist(df, column, bins, xlabel, ylabel,
                            color='darkorchid', unit_interval=(column in ['eff_primary', 'pur_primary']))
        if column != 'ntc':
            ax.axvline(x=1, color='grey', linestyle='--')
        fig.tight_layout()
        figname = os.path.join(outputdir, f'{file_prefix}_{column}.png')
        fig.savefig(figname)
        print(f'Saved figure {figname}.')

    eta_bins = np.linspace(-3.2, 3.2, 17)
    pt_max = max(1., np.quantile(df['pt'].values, 0.98))
    pt_bins = np.linspace(0, pt_max, 15)
    for column, ylabel in [
            ('eff_primary', 'Efficiency of primary TICLCandidate'),
            ('eff_sum', f'{truth_label} efficiency (total)'),
            ('ntc', f'TICLCandidates per {truth_label}')]:
        for xcolumn, bins, xlabel, suffix in [
                ('eta', eta_bins, f'{truth_label} eta', f'{column}_vs_eta'),
                ('pt', pt_bins, f'{truth_label} pT', f'{column}_vs_pt')]:
            quantity_per_bin = get_quantity_per_bin(df, xcolumn, column, bins)
            fig, ax = plot_quantity_per_bin(
                quantity_per_bin,
                xlabel=xlabel,
                ylabel=ylabel,
                color='darkorchid',
                doerrs=False,
                linewidth=3)
            if column == 'ntc':
                ax.lines[-1].remove()
            fig.tight_layout()
            figname = os.path.join(outputdir, f'{file_prefix}_{suffix}.png')
            fig.savefig(figname)
            print(f'Saved figure {figname}.')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('inputfile')
    parser.add_argument('--cp-inputfile', default=None,
        help='Per-truth-object TICLCandidate metrics file (defaults to'
             ' metrics_cp_tc.parquet next to inputfile; pass'
             ' metrics_sc_tc.parquet here when plotting SimCluster-based'
             ' metrics_tc_sc.parquet).')
    parser.add_argument('-o', '--outputdir', default=None)
    parser.add_argument('--truth_label', default='CaloParticle',
        help='Truth object name used in axis labels (e.g. "SimCluster" when'
             ' plotting SimCluster-based metrics).')
    parser.add_argument('--file_prefix', default='cp',
        help='Filename prefix for the per-truth-object plots (e.g. "sc" when'
             ' plotting SimCluster-based metrics, to avoid overwriting the'
             ' CaloParticle-based cp_*.png files if writing to the same'
             ' output directory).')
    args = parser.parse_args()

    inputfile = args.inputfile
    outputdir = args.outputdir
    if outputdir is None:
        outputdir = os.path.splitext(inputfile)[0] + '_plots'
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    df = pd.read_parquet(inputfile)
    print(df)

    if len(df) == 0:
        print('No TICLCandidate rows to plot.')
        sys.exit(0)

    # Candidate-level distributions.
    histograms = [
        ('pur', np.linspace(0, 1.2, 61), 'TICLCandidate purity', 'TICLCandidates'),
        ('eff', np.linspace(0, 1.2, 61), 'TICLCandidate efficiency', 'TICLCandidates'),
        ('ntracksters', np.arange(-0.5, max(5, int(np.max(df['ntracksters'].values)) + 1.5), 1), 'Tracksters per TICLCandidate', 'TICLCandidates'),
        ('nlayerclusters', np.arange(-0.5, max(10, int(np.max(df['nlayerclusters'].values)) + 1.5), 1), 'LayerClusters per TICLCandidate', 'TICLCandidates'),
    ]
    for column, bins, xlabel, ylabel in histograms:
        fig, ax = plot_hist(df, column, bins, xlabel, ylabel,
                            unit_interval=(column in ['pur', 'eff']))
        if column in ['pur', 'eff']:
            ax.axvline(x=1, color='grey', linestyle='--')
        fig.tight_layout()
        figname = os.path.join(outputdir, f'tc_{column}.png')
        fig.savefig(figname)
        print(f'Saved figure {figname}.')

    eta_bins = np.linspace(-3.2, 3.2, 17)
    pt_max = max(1., np.quantile(df['pt'].values, 0.98))
    pt_bins = np.linspace(0, pt_max, 15)
    plot_effandpur_vs(df, 'caloparticle_eta', eta_bins, f'Matched {args.truth_label} eta', outputdir, 'eta')
    plot_effandpur_vs(df, 'caloparticle_pt', pt_bins, f'Matched {args.truth_label} pT', outputdir, 'pt')

    # Truth-object-level TICLCandidate metrics, if present.
    cp_inputfile = args.cp_inputfile
    if cp_inputfile is None:
        cp_inputfile = os.path.join(os.path.dirname(inputfile), 'metrics_cp_tc.parquet')
    if os.path.exists(cp_inputfile):
        df_cp = pd.read_parquet(cp_inputfile)
        print(df_cp)
        plot_cp_tc_metrics(df_cp, outputdir, truth_label=args.truth_label, file_prefix=args.file_prefix)
