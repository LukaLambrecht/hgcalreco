import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from analysis.efficiency import plot_metrics_tc
from plotutils import save_with_logy


def _format_labels(result, params=None, legend_dict=None):
    if legend_dict is None:
        legend_dict = {}

    labeldict = {key: legend_dict.get(key, key) for key in result.keys()}
    if params is not None:
        for key in params.keys():
            if params[key] is None:
                continue
            this_params = {}
            for p, v in params[key].items():
                param_key = legend_dict.get(p, p)
                value = '{:.2e}'.format(v)
                this_params[param_key] = value
            labeldict[key] = ', '.join([f'{k} = {v}' for k, v in this_params.items()])

    if len(labeldict) > 10:
        for idx, key in enumerate(labeldict.keys()):
            if idx % 2 == 0:
                continue
            labeldict[key] = None

    return labeldict


def _color_dict(result):
    cmap = mpl.colormaps['cool']
    cvals = np.linspace(0, 1, num=len(result))
    colordict = {key: cmap(cval) for key, cval in zip(result.keys(), cvals)}
    if len(result) == 1:
        colordict = {list(result.keys())[0]: 'dodgerblue'}
    return colordict


def _finite_values(dfs, column):
    vals = []
    for df in dfs:
        if column not in df.columns or len(df) == 0:
            continue
        arr = df[column].values
        vals.append(arr[np.isfinite(arr)])
    if len(vals) == 0:
        return np.array([])
    return np.concatenate(vals)


def _integer_bins(dfs, column, default_max):
    vals = _finite_values(dfs, column)
    if len(vals) == 0:
        high = default_max
    else:
        high = max(default_max, int(np.max(vals)) + 1)
    return np.arange(-0.5, high + 0.5, 1)


def _positive_bins(dfs, column, default_max=1., nbins=60):
    vals = _finite_values(dfs, column)
    if len(vals) == 0:
        high = default_max
    else:
        high = max(default_max, float(np.quantile(vals, 0.98)) * 1.1)
    return np.linspace(0, high, nbins + 1)


def plot_tc_result(result, outputdir, params=None, legend_dict=None):
    if len(result) == 0:
        print('No TICLCandidate scan results to plot.')
        return

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    result = {key: df for key, df in result.items() if len(df) > 0}
    if len(result) == 0:
        print('All TICLCandidate scan result dataframes are empty; skipping TICLCandidate plots.')
        return

    colordict = _color_dict(result)
    labeldict = _format_labels(result, params=params, legend_dict=legend_dict)
    dfs = list(result.values())

    histograms = [
        ('pur', np.linspace(0, 1.2, 61), 'TICLCandidate purity', 'TICLCandidates', True),
        ('eff', np.linspace(0, 1.2, 61), 'TICLCandidate efficiency', 'TICLCandidates', True),
        ('ntracksters', _integer_bins(dfs, 'ntracksters', 5), 'Tracksters per TICLCandidate', 'TICLCandidates', False),
        ('nlayerclusters', _integer_bins(dfs, 'nlayerclusters', 10), 'LayerClusters per TICLCandidate', 'TICLCandidates', False),
        ('pt', _positive_bins(dfs, 'pt'), 'TICLCandidate pT', 'TICLCandidates', False),
        ('energy', _positive_bins(dfs, 'energy'), 'TICLCandidate energy', 'TICLCandidates', False),
    ]

    for column, bins, xlabel, ylabel, unit_interval in histograms:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.grid(visible=True, which='both', axis='both')
        for key, df in result.items():
            if column not in df.columns:
                continue
            values = df[column].values
            if unit_interval:
                values = values.copy()
                values[np.isclose(values, 1., rtol=0., atol=1e-12)] = np.nextafter(1., 0.)
            ax.hist(values, bins=bins, histtype='step', linewidth=3,
                    color=colordict[key], label=labeldict[key])
        if unit_interval:
            ax.axvline(x=1, color='grey', linestyle='--')
        ax.set_xlabel(xlabel, fontsize=15)
        ax.set_ylabel(ylabel, fontsize=15)
        ax.tick_params(axis='both', which='both', labelsize=15)
        if len(result) > 1:
            ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1, 1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'tc_{column}.png')
        save_with_logy(fig, ax, figname)
        plt.close(fig)

    for xcolumn, bins, xlabel, suffix in [
            ('caloparticle_eta', np.linspace(-3.2, 3.2, 17), 'Matched CaloParticle eta', 'eta'),
            ('caloparticle_pt', _positive_bins(dfs, 'caloparticle_pt', nbins=14), 'Matched CaloParticle pT', 'pt')]:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.grid(visible=True, which='both', axis='both')
        for key, df in result.items():
            if xcolumn not in df.columns:
                continue
            purity_per_bin = plot_metrics_tc.get_quantity_per_bin(df, xcolumn, 'pur', bins)
            yvals = np.array([val[0] for val in purity_per_bin.values()])
            ax.stairs(yvals, edges=bins, color=colordict[key], linewidth=3,
                      label=labeldict[key])
        ax.axhline(y=1, color='grey', linestyle='--')
        ax.set_ylim((0, 1.2))
        ax.set_xlabel(xlabel, fontsize=15)
        ax.set_ylabel('Mean TICLCandidate purity', fontsize=15)
        ax.tick_params(axis='both', which='both', labelsize=15)
        if len(result) > 1:
            ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1, 1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'tc_purity_vs_{suffix}.png')
        save_with_logy(fig, ax, figname)
        plt.close(fig)


def plot_cp_tc_result(result, outputdir, params=None, legend_dict=None):
    if len(result) == 0:
        print('No CaloParticle TICLCandidate scan results to plot.')
        return

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    result = {key: df for key, df in result.items() if len(df) > 0}
    if len(result) == 0:
        print('All CaloParticle TICLCandidate scan result dataframes are empty; skipping CP-TC plots.')
        return

    colordict = _color_dict(result)
    labeldict = _format_labels(result, params=params, legend_dict=legend_dict)
    dfs = list(result.values())

    histograms = [
        ('eff_primary', np.linspace(0, 1.2, 61), 'Efficiency of primary TICLCandidate', 'CaloParticles', True),
        ('pur_primary', np.linspace(0, 1.2, 61), 'Purity of primary TICLCandidate', 'CaloParticles', True),
        ('eff_sum', _positive_bins(dfs, 'eff_sum', default_max=1.2), 'CaloParticle efficiency (total)', 'CaloParticles', False),
        ('ntc', _integer_bins(dfs, 'ntc', 5), 'TICLCandidates per CaloParticle', 'CaloParticles', False),
    ]

    for column, bins, xlabel, ylabel, unit_interval in histograms:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.grid(visible=True, which='both', axis='both')
        for key, df in result.items():
            if column not in df.columns:
                continue
            values = df[column].values
            if unit_interval:
                values = values.copy()
                values[np.isclose(values, 1., rtol=0., atol=1e-12)] = np.nextafter(1., 0.)
            ax.hist(values, bins=bins, histtype='step', linewidth=3,
                    color=colordict[key], label=labeldict[key])
        if column != 'ntc':
            ax.axvline(x=1, color='grey', linestyle='--')
        ax.set_xlabel(xlabel, fontsize=15)
        ax.set_ylabel(ylabel, fontsize=15)
        ax.tick_params(axis='both', which='both', labelsize=15)
        if len(result) > 1:
            ax.legend(fontsize=15, loc='upper left', bbox_to_anchor=(1, 1))
        fig.tight_layout()
        figname = os.path.join(outputdir, f'cp_tc_{column}.png')
        save_with_logy(fig, ax, figname)
        plt.close(fig)


if __name__ == '__main__':
    inputfile = sys.argv[1]
    paramfile = None if len(sys.argv) == 2 else sys.argv[2]
    outputdir = os.path.splitext(inputfile)[0] + '_plots'

    df = pd.read_parquet(inputfile)
    params = None
    if paramfile is not None:
        with open(paramfile, 'r') as f:
            params = json.load(f)

    result = {'_': df}
    params = {'_': params}
    plot_tc_result(result, outputdir, params=params)

    cp_inputfile = os.path.join(os.path.dirname(inputfile), 'metrics_cp_tc.parquet')
    if os.path.exists(cp_inputfile):
        plot_cp_tc_result({'_': pd.read_parquet(cp_inputfile)}, outputdir, params=params)
