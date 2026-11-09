# Plot the composition of TICLCandidates and their matched truth objects per HGCAL subdetector,
# for a single re-reco (e.g. the default parameter point of a grid scan).
#
# Input: an efficiency output directory of analysis/efficiency/calculate_associations.py,
# run with --do_composition (e.g. <grid scan output>/<grid>/<job>/efficiency).
#
# Covers:
# - TICLCandidate composition (LayerCluster count and energy per subdetector);
# - truth composition (truth energy in LayerClusters per subdetector),
#   and how it compares to the composition of the primary TICLCandidate;
# - all LayerClusters per subdetector, and which part of them ends up in TICLCandidates;
# - purity and efficiency per truth category (CE-E dominated, mixed, CE-H dominated).


import os
import sys
import json
import argparse
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

thisdir = os.path.dirname(os.path.abspath(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../..'))
sys.path.append(topdir)

from tools.compositiontools import SUBDETS, SUBDET_LABELS, SUBDET_COLORS
from tools.compositiontools import TRUTH_TYPES, TRUTH_CATEGORIES
from tools.compositiontools import load_composition, load_event_lc


DEFAULT_INPUT = ('/eos/home-l/llambrec/hgcalreco-data/gridscans/output_20261109_201X_D127_PU200/'
    'kappa_hsi_1d/job10/efficiency')


def savefig(fig, outputdir, name):
    fig.tight_layout()
    path = os.path.join(outputdir, f'{name}.png')
    fig.savefig(path)
    plt.close(fig)
    print(f'Created figure {path}')


def binned_mean(x, y, bins):
    '''Mean and uncertainty on the mean of y in bins of x.'''
    idx = np.digitize(x, bins) - 1
    means = np.full(len(bins) - 1, np.nan)
    errors = np.full(len(bins) - 1, np.nan)
    for b in range(len(bins) - 1):
        values = y[(idx == b) & np.isfinite(y)]
        if len(values) == 0: continue
        means[b] = np.mean(values)
        errors[b] = np.std(values) / np.sqrt(len(values)) if len(values) > 1 else 0
    return means, errors


def add_textbox(ax, text, width=32, fontsize=10):
    '''Add extra information in a box in the upper left corner (wrapped to a limited width).'''
    text = '\n'.join(textwrap.fill(line, width=width) for line in text.split('\n'))
    ax.text(0.03, 0.97, text, transform=ax.transAxes, va='top', ha='left', fontsize=fontsize,
        bbox=dict(boxstyle='round', facecolor='white', edgecolor='#c8c8c8'))


def plot_fraction_histograms(df, prefix, xlabel, outputdir, name, text=None):
    '''Histogram of the fraction per subdetector (one line per subdetector).'''
    fig, ax = plt.subplots(figsize=(7, 5))
    bins = np.linspace(0, 1, 26)
    for s in SUBDETS:
        values = df[f'{prefix}{s}'].values
        values = values[np.isfinite(values)]
        ax.hist(values, bins=bins, histtype='step', linewidth=2, color=SUBDET_COLORS[s],
            label=f'{SUBDET_LABELS[s]} (mean {np.mean(values):.2f})')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.5)
    ax.legend(fontsize=10, loc='upper right')
    if text is not None: add_textbox(ax, text)
    savefig(fig, outputdir, name)


def plot_fraction_vs(x, curves, bins, xlabel, ylabel, outputdir, name):
    '''
    Mean fraction per subdetector vs a variable.
    curves: list of (dataframe column prefix, dataframe, linestyle, label suffix).
    '''
    fig, ax = plt.subplots(figsize=(7, 5))
    centers = (bins[1:] + bins[:-1]) / 2
    for prefix, df, linestyle, suffix in curves:
        for s in SUBDETS:
            means, errors = binned_mean(x(df), df[f'{prefix}{s}'].values, bins)
            ax.errorbar(centers, means, yerr=errors, color=SUBDET_COLORS[s], linestyle=linestyle,
                linewidth=2, marker='o', markersize=4, label=f'{SUBDET_LABELS[s]} ({suffix})')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_ylim(0, 1.3)
    ax.legend(fontsize=9, ncol=2, loc='upper center')
    savefig(fig, outputdir, name)


# TICLCandidate selections w.r.t. a truth object:
# - primary: the primary TICLCandidate (columns with prefix "primary_" in df_truth);
# - all: all matched TICLCandidates combined (columns with prefix "all_" in df_truth).
TC_SELECTIONS = {
    'primary': {'label': 'primary TICLCandidate', 'Label': 'Primary TICLCandidate'},
    'all': {'label': 'all matched TICLCandidates', 'Label': 'All matched TICLCandidates'},
}


def plot_tc_composition(df_tc, df_truth, truth_type, outputdir):
    '''TICLCandidate composition and comparison with the truth composition.'''
    tlabel = TRUTH_TYPES[truth_type]
    tshort = tlabel.split(' ')[0]
    prefix = f'tc_{truth_type}'

    # per-TICLCandidate composition
    primary = df_tc[df_tc['is_primary']]
    selections = {
        'all': (df_tc, f'All TICLCandidates matched to a {tlabel} (each TICLCandidate separately)'),
        'primary': (primary, f'Primary TICLCandidates of a {tlabel}'),
    }
    for selname, (df, text) in selections.items():
        plot_fraction_histograms(df, 'fe_', 'Fraction of TICLCandidate energy', outputdir,
            f'{prefix}_composition_energy_{selname}', text=text)
        plot_fraction_histograms(df, 'fn_', 'Fraction of TICLCandidate LayerClusters', outputdir,
            f'{prefix}_composition_nlc_{selname}', text=text)

    for selname, sel in TC_SELECTIONS.items():
        p = f'{selname}_'

        # composition vs truth |eta| and energy, TICLCandidate(s) vs truth
        curves = [
            (f'{p}fe_', df_truth, '-', sel['label']),
            ('ftruth_', df_truth, '--', tshort),
        ]
        plot_fraction_vs(lambda df: np.abs(df['eta'].values), curves, np.linspace(1.5, 3.0, 11),
            rf'{tlabel} $|\eta|$', 'Mean energy fraction', outputdir,
            f'{prefix}_composition_energy_vs_eta_{selname}')
        emax = np.quantile(df_truth['energy'], 0.99)
        plot_fraction_vs(lambda df: df['energy'].values, curves, np.linspace(0, emax, 11),
            f'{tlabel} energy (GeV)', 'Mean energy fraction', outputdir,
            f'{prefix}_composition_energy_vs_energy_{selname}')
        curves = [(f'{p}fn_', df_truth, '-', sel['label'])]
        plot_fraction_vs(lambda df: np.abs(df['eta'].values), curves, np.linspace(1.5, 3.0, 11),
            rf'{tlabel} $|\eta|$', 'Mean LayerCluster fraction', outputdir,
            f'{prefix}_composition_nlc_vs_eta_{selname}')

        # TICLCandidate(s) vs truth energy fraction per subdetector (2D)
        for s in SUBDETS:
            df = df_truth[np.isfinite(df_truth[f'{p}fe_{s}']) & np.isfinite(df_truth[f'ftruth_{s}'])]
            fig, ax = plt.subplots(figsize=(6.5, 5.5))
            h = ax.hist2d(df[f'ftruth_{s}'], df[f'{p}fe_{s}'], bins=np.linspace(0, 1, 21), cmap='Blues', cmin=1)
            fig.colorbar(h[3], ax=ax, label='Count')
            ax.plot([0, 1], [0, 1], color='#6b6b6b', linestyle='--', linewidth=1)
            ax.set_xlabel(f'Fraction of {tlabel} energy in {SUBDET_LABELS[s]}', fontsize=11)
            ax.set_ylabel(f'Fraction of energy in {SUBDET_LABELS[s]}\n({sel["label"]})', fontsize=11)
            savefig(fig, outputdir, f'{prefix}_composition_{s}_vs_truth_{selname}')

        # ratio of TICLCandidate energy to truth energy per subdetector
        # (only for truth objects with at least 5% of their energy in that subdetector)
        fig, ax = plt.subplots(figsize=(7, 5))
        bins = np.linspace(0, 2, 41)
        for s in SUBDETS:
            mask = (df_truth[f'ftruth_{s}'] >= 0.05) & np.isfinite(df_truth[f'{p}e_{s}'])
            ratio = (df_truth[f'{p}e_{s}'] / df_truth[f'truthe_{s}'])[mask].values
            ax.hist(np.clip(ratio, 0, bins[-1] - 1e-6), bins=bins, histtype='step', linewidth=2,
                color=SUBDET_COLORS[s], label=f'{SUBDET_LABELS[s]}\n(median {np.median(ratio):.2f}, n={len(ratio)})')
        ax.set_xlabel(f'Energy of {sel["label"]} / {tshort} energy,\nper subdetector', fontsize=11)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.5)
        ax.legend(fontsize=9, loc='upper right')
        add_textbox(ax, f'{tlabel}s with at least 5% of their energy in the subdetector'
            + ' (last bin includes overflow)')
        savefig(fig, outputdir, f'{prefix}_energy_ratio_per_subdet_{selname}')


def plot_truth_composition(df_truth, truth_type, outputdir):
    '''Truth composition.'''
    tlabel = TRUTH_TYPES[truth_type]
    plot_fraction_histograms(df_truth, 'ftruth_', f'Fraction of {tlabel} energy (in LayerClusters)',
        outputdir, f'{truth_type}_composition_energy', text=f'Selected {tlabel}s')


def plot_metrics_by_category(df_tc, df_truth, truth_type, outputdir):
    '''
    Efficiency and purity per truth category, and vs the truth CE-E energy fraction.
    Efficiency: w.r.t. the primary TICLCandidate (eff_primary) and w.r.t. all matched TICLCandidates (eff_sum),
    one entry per truth object.
    Purity: of the primary TICLCandidate (pur_primary, one entry per truth object),
    and of all matched TICLCandidates (pur, one entry per TICLCandidate).
    '''
    tlabel = TRUTH_TYPES[truth_type]
    metrics = {
        # name: (dataframe, column, x-axis label, y-axis label for means, figure name)
        'eff_primary': (df_truth, 'eff_primary',
            f'{tlabel} efficiency w.r.t. primary TICLCandidate',
            f'Mean {tlabel} efficiency\nw.r.t. primary TICLCandidate',
            f'{truth_type}_tc_eff_primary'),
        'eff_all': (df_truth, 'eff_sum',
            f'{tlabel} efficiency w.r.t. all matched TICLCandidates',
            f'Mean {tlabel} efficiency\nw.r.t. all matched TICLCandidates',
            f'{truth_type}_tc_eff_all'),
        'pur_primary': (df_truth, 'pur_primary',
            f'Primary TICLCandidate purity w.r.t. {tlabel}',
            f'Mean primary TICLCandidate purity\nw.r.t. {tlabel}',
            f'{truth_type}_tc_pur_primary'),
        'pur_all': (df_tc, 'pur',
            f'TICLCandidate purity w.r.t. matched {tlabel}',
            f'Mean TICLCandidate purity\nw.r.t. matched {tlabel}',
            f'tc_{truth_type}_pur_all'),
    }
    for metric, (df, column, xlabel, ylabel, figname) in metrics.items():
        entries = 'TICLCandidates' if df is df_tc else f'{tlabel}s'
        fig, ax = plt.subplots(figsize=(7, 5))
        bins = np.linspace(0, 1, 26)
        for key, info in TRUTH_CATEGORIES.items():
            values = df[df['category'] == key][column].values
            if len(values) == 0: continue
            ax.hist(values, bins=bins, histtype='step', linewidth=2, color=info['color'], density=True,
                label=f'{info["label"]}\n(n={len(values)}, mean {np.mean(values):.3f})')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(f'Normalized number of {entries}', fontsize=11)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
        ax.legend(fontsize=9, loc='upper left')
        savefig(fig, outputdir, f'{figname}_by_category')

        # vs truth CE-E energy fraction (of the matched truth object for TICLCandidates)
        if df is df_tc:
            ftruth = df_tc.merge(df_truth[['event', 'truth_index', 'ftruth_ee']],
                on=['event', 'truth_index'], how='left')['ftruth_ee'].values
        else: ftruth = df['ftruth_ee'].values
        fig, ax = plt.subplots(figsize=(7, 5))
        bins = np.linspace(0, 1, 11)
        centers = (bins[1:] + bins[:-1]) / 2
        means, errors = binned_mean(ftruth, df[column].values, bins)
        counts = np.histogram(ftruth, bins=bins)[0]
        ax.errorbar(centers, means, yerr=errors, color='#2a78d6', linewidth=2, marker='o', markersize=5)
        ax.set_xlabel(f'Fraction of {tlabel} energy in CE-E', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_ylim(0, 1.05)
        for c, n in zip(centers, counts): # number of entries per bin, for context
            if n > 0: ax.text(c, 0.02, f'n={n}', ha='center', va='bottom', fontsize=8, color='#6b6b6b')
        savefig(fig, outputdir, f'{figname}_vs_truth_ee_fraction')


def plot_event_layerclusters(df_event, outputdir, df_tc=None, truth_type=None):
    '''
    LayerClusters per subdetector per event: all, used in any TICLCandidate,
    and (if df_tc is provided) used in TICLCandidates matched to a selected truth object.
    Bars: mean over events; hatched band: 16th to 84th percentile over events.
    Note: for the matched TICLCandidates, the numbers are sums over TICLCandidates
          (a LayerCluster shared between matched TICLCandidates is counted in each of them,
          and its energy is counted with its share in each of them).
    '''
    df_event = df_event.copy()
    if df_tc is not None:
        columns = [f'{q}_{s}' for q in ['nlc', 'e'] for s in SUBDETS]
        matched = df_tc.groupby('event')[columns].sum()
        matched = matched.reindex(df_event['event'].values, fill_value=0) # events without matched TICLCandidates
        for c in columns:
            df_event[c.replace('_', '_tcmatched_', 1)] = matched[c].values
    quantities = [
        ('nlc', 'Number of LayerClusters per event', '{:.0f}'),
        ('e', 'Sum of LayerCluster energy per event (GeV)', '{:.0f}'),
    ]
    bars = [
        ('{q}_{s}', '#c6dcf5', 'All LayerClusters'),
        ('{q}_tc_{s}', '#5f9be3', 'In any TICLCandidate'),
    ]
    if df_tc is not None:
        bars.append(('{q}_tcmatched_{s}', '#174a87',
            f'In TICLCandidates matched to a\n{TRUTH_TYPES[truth_type]}'))
    width = 0.8 / len(bars)
    for quantity, ylabel, fmt in quantities:
        fig, ax = plt.subplots(figsize=(7, 5))
        x = np.arange(len(SUBDETS))
        for bar_idx, (column, color, label) in enumerate(bars):
            offset = (bar_idx - (len(bars) - 1) / 2) * (width + 0.01)
            values = [df_event[column.format(q=quantity, s=s)].values for s in SUBDETS]
            means = np.array([np.mean(v) for v in values])
            low = np.array([np.quantile(v, 0.16) for v in values])
            high = np.array([np.quantile(v, 0.84) for v in values])
            ax.bar(x + offset, means, width=width, color=color, label=label)
            for idx in range(len(SUBDETS)):
                # hatched (unfilled) band on top of the bar, so the top of the bar (the mean) remains visible
                ax.fill_between([x[idx] + offset - width/2, x[idx] + offset + width/2], low[idx], high[idx],
                    facecolor='none', edgecolor='#1a1a1a', hatch='////', linewidth=0, zorder=3)
                ax.text(x[idx] + offset, max(means[idx], high[idx]) * 1.08, fmt.format(means[idx]),
                    ha='center', va='bottom', fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([SUBDET_LABELS[s] for s in SUBDETS], fontsize=11)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_yscale('log')
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1] * 10)
        ax.legend(fontsize=9, loc='upper right')
        savefig(fig, outputdir, f'event_lc_{quantity}_per_subdet')


def plot_event_truth(df_truth, truth_type, outputdir):
    '''
    Sum of the energy of the selected truth objects per subdetector per event.
    The truth energy per subdetector is the shared energy of the truth object with all LayerClusters
    in that subdetector (i.e. the rechit energy, weighted by the truth object's fraction of each cell,
    for cells in any LayerCluster).
    Bars: mean over events; hatched band: 16th to 84th percentile over events.
    '''
    tlabel = TRUTH_TYPES[truth_type]
    per_event = df_truth.groupby('event')[[f'truthe_{s}' for s in SUBDETS]].sum()
    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(len(SUBDETS))
    width = 0.5
    values = [per_event[f'truthe_{s}'].values for s in SUBDETS]
    means = np.array([np.mean(v) for v in values])
    low = np.array([np.quantile(v, 0.16) for v in values])
    high = np.array([np.quantile(v, 0.84) for v in values])
    ax.bar(x, means, width=width, color='#174a87')
    for idx in range(len(SUBDETS)):
        ax.fill_between([x[idx] - width/2, x[idx] + width/2], low[idx], high[idx],
            facecolor='none', edgecolor='#1a1a1a', hatch='////', linewidth=0, zorder=3)
        ax.text(x[idx], max(means[idx], high[idx]) * 1.08, f'{means[idx]:.0f}',
            ha='center', va='bottom', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([SUBDET_LABELS[s] for s in SUBDETS], fontsize=11)
    ax.set_ylabel(f'Sum of {tlabel}\nenergy deposits per event (GeV)', fontsize=12)
    ax.set_yscale('log')
    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1] * 5)
    add_textbox(ax, 'Sum over cells in LayerClusters of\nRecHit energy x signal particle energy fraction',
        width=48, fontsize=9)
    savefig(fig, outputdir, f'event_{truth_type}_e_per_subdet')


def get_summary(df_tc, df_truth, df_event):
    '''Summary numbers (also printed).'''
    summary = {}
    primary = df_tc[df_tc['is_primary']]
    for name, df in [('tc_all', df_tc), ('tc_primary', primary)]:
        etot = sum(df[f'e_{s}'].sum() for s in SUBDETS)
        ntot = sum(df[f'nlc_{s}'].sum() for s in SUBDETS)
        summary[name] = {
            'n': int(len(df)),
            'energy_fraction': {s: float(df[f'e_{s}'].sum() / etot) for s in SUBDETS},
            'nlc_fraction': {s: float(df[f'nlc_{s}'].sum() / ntot) for s in SUBDETS},
        }
    etot = sum(df_truth[f'truthe_{s}'].sum() for s in SUBDETS)
    summary['truth'] = {
        'n': int(len(df_truth)),
        'energy_fraction': {s: float(df_truth[f'truthe_{s}'].sum() / etot) for s in SUBDETS},
        'category_fraction': {k: float(np.mean(df_truth['category'] == k)) for k in TRUTH_CATEGORIES},
        'eff_primary_by_category': {k: float(df_truth[df_truth['category'] == k]['eff_primary'].mean())
            for k in TRUTH_CATEGORIES},
        'pur_primary_by_category': {k: float(df_truth[df_truth['category'] == k]['pur_primary'].mean())
            for k in TRUTH_CATEGORIES},
        'eff_all_by_category': {k: float(df_truth[df_truth['category'] == k]['eff_sum'].mean())
            for k in TRUTH_CATEGORIES},
        'pur_all_by_category': {k: float(df_tc[df_tc['category'] == k]['pur'].mean())
            for k in TRUTH_CATEGORIES},
    }
    if df_event is not None:
        summary['event_lc'] = {s: {
            'nlc': float(df_event[f'nlc_{s}'].mean()),
            'nlc_in_tc_fraction': float(df_event[f'nlc_tc_{s}'].sum() / df_event[f'nlc_{s}'].sum()),
            'energy': float(df_event[f'e_{s}'].mean()),
            'energy_in_tc_fraction': float(df_event[f'e_tc_{s}'].sum() / df_event[f'e_{s}'].sum()),
        } for s in SUBDETS}
    return summary


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Plot TICLCandidate and truth composition per subdetector')
    parser.add_argument('-i', '--inputdir', default=DEFAULT_INPUT,
        help='Efficiency output directory (default: default parameter point of the latest PU200 grid scan)')
    parser.add_argument('-t', '--truth_types', default=['truthbranch-signal'], nargs='+',
        choices=list(TRUTH_TYPES.keys()))
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output_default'))
    args = parser.parse_args()

    os.makedirs(args.outputdir, exist_ok=True)

    # per-event LayerCluster summary (independent of the truth type)
    df_event = None
    if os.path.exists(os.path.join(args.inputdir, 'metrics_event_lc.parquet')):
        df_event = load_event_lc(args.inputdir)

    summaries = {}
    for truth_type in args.truth_types:
        print(f'Making plots for truth type {truth_type}...')
        df_tc, df_truth = load_composition(args.inputdir, truth_type=truth_type)
        if df_event is not None and truth_type == args.truth_types[0]:
            plot_event_layerclusters(df_event, args.outputdir, df_tc=df_tc, truth_type=truth_type)
        plot_tc_composition(df_tc, df_truth, truth_type, args.outputdir)
        plot_truth_composition(df_truth, truth_type, args.outputdir)
        plot_event_truth(df_truth, truth_type, args.outputdir)
        plot_metrics_by_category(df_tc, df_truth, truth_type, args.outputdir)
        summaries[truth_type] = get_summary(df_tc, df_truth, df_event)

    summaryfile = os.path.join(args.outputdir, 'summary.json')
    with open(summaryfile, 'w') as f:
        json.dump({'inputdir': args.inputdir, 'summary': summaries}, f, indent=2)
    print(f'Written summary to {summaryfile}')
    print(json.dumps(summaries, indent=2))
