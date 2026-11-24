# Plot the distributions of the scanned parameter values for a range of grid points,
# after sorting the grid points by a chosen quantity.
#
# Typical use case: in a "flat" plot of a multi-parameter grid scan (see scan_sensitivity.py --flat),
# find the common characteristics of the grid points in some range of the sorted order.
#
# Input: a summary CSV file with one row per grid point, as written by scan_sensitivity.py with --flat
# (<grid>/summary_<truth type>.csv), i.e. with the parameter values in columns param_<name>.
#
# Example:
#   python3 plot_param_distributions.py -i output_scan_sensitivity_5d/all_hsi_5d/summary_truthbranch-signal.csv \
#       -s average -r 485 515
# Without -s, the order of the CSV file is kept; without -r, all grid points are used.
# Instead of a fixed range, --best_percent x selects the best x% (the highest values of the sorting key), e.g.
#   python3 plot_param_distributions.py -i <summary csv> -s average --best_percent 10


import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

from scanutils import DEFAULT_PARAMS, PARAM_LABELS


# predefined sorting keys (same as the flat sortings in scan_sensitivity.py);
# any other column name of the CSV file can be used as well
SORTS = {
    'purity': (lambda d: d['pur_all'], 'mean purity of all matched TICLCandidates'),
    'efficiency': (lambda d: d['eff_all_rechits'], 'mean efficiency'),
    'average': (lambda d: (d['pur_all'] + d['eff_all_rechits']) / 2, 'avg. of purity and efficiency'),
}


def get_sorted(df, sort):
    '''
    Sort the grid points by a predefined sorting key or a column name (ascending, stable).
    If sort is None, the order of the input is kept.
    '''
    if sort is None:
        return df.reset_index(drop=True), None
    if sort in SORTS:
        key, label = SORTS[sort]
        key = key(df)
    elif sort in df.columns:
        key, label = df[sort], sort
    else:
        raise Exception(f'Unknown sorting key {sort} (choose from {list(SORTS.keys())} or a column name).')
    order = np.argsort(key.values, kind='stable')
    return df.iloc[order].reset_index(drop=True), label


def plot_param_distributions(df, selected, outputfile, title=None):
    '''
    One panel per parameter: the number of selected grid points per grid value,
    with a dashed line at the default value.
    df: all grid points (to get all grid values per parameter); selected: the selected grid points.
    '''
    params = [c for c in df.columns if c.startswith('param_') and c not in ['param_name', 'param_value']]
    if len(params) == 0: raise Exception('No parameter columns (param_<name>) found in the input file.')
    fig, axs = plt.subplots(1, len(params), figsize=(3.3 * len(params), 3.6), squeeze=False)
    for ax, column in zip(axs[0], params):
        name = column[len('param_'):]
        values = np.sort(df[column].unique())
        counts = np.array([np.sum(np.isclose(selected[column], v)) for v in values])
        x = np.arange(len(values))
        ax.bar(x, counts, width=0.7, color='#2a78d6')
        ax.set_xticks(x)
        ax.set_xticklabels([f'{v:g}' for v in values], fontsize=9)
        ax.set_xlabel(PARAM_LABELS.get(name, name), fontsize=11)
        ax.set_ylim(0, max(len(selected), 1) * 1.05)
        ax.grid(axis='y', color='#e6e6e6', linewidth=0.8)
        ax.set_axisbelow(True)
        # default value: at its position if it is a grid value, otherwise interpolated (log scale)
        default = DEFAULT_PARAMS.get(name)
        if default is not None:
            if np.any(np.isclose(values, default)):
                xdefault = x[np.isclose(values, default)][0]
            else:
                xdefault = np.interp(np.log(default), np.log(values), x)
            ax.axvline(xdefault, color='#6b6b6b', linestyle='--', linewidth=1.5, label='Default value')
    axs[0][0].set_ylabel('Number of grid points', fontsize=11)
    axs[0][0].legend(fontsize=9, loc='upper left')
    if title is not None: fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(outputfile)
    plt.close(fig)
    print(f'Created figure {outputfile}')


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Plot the parameter distributions for a range of sorted grid points')
    parser.add_argument('-i', '--inputfile', required=True, help='Summary CSV file (one row per grid point)')
    parser.add_argument('-s', '--sort', default=None,
        help=f'Sorting key: one of {list(SORTS.keys())} or a column name'
            + ' (default: none, i.e. keep the order of the input file)')
    parser.add_argument('-r', '--range', default=None, nargs=2, type=int,
        help='First and last index (both included) of the selected grid points in the sorted order'
            + ' (default: all grid points)')
    parser.add_argument('--best_percent', default=None, type=float,
        help='Select the best x%% of the grid points in the sorted order (the last ones, with the highest sorting key)'
            + ' instead of a fixed range (needs -s)')
    parser.add_argument('-o', '--outputfile', default=None,
        help='Output file (default: param_distributions_<sort>_<first>_<last>.png next to the input file,'
            + ' with "unsorted" and/or "all" if no sorting and/or range is given)')
    args = parser.parse_args()

    df = pd.read_csv(args.inputfile)
    df, sortlabel = get_sorted(df, args.sort)
    if args.best_percent is not None:
        if args.sort is None: raise Exception('--best_percent needs a sorting key (-s).')
        if args.range is not None: raise Exception('Use either -r or --best_percent, not both.')
        nselected = max(int(round(len(df) * args.best_percent / 100)), 1)
        selected = df.iloc[len(df) - nselected:]
        rangetag = f'best{args.best_percent:g}'
        title = f'Best {args.best_percent:g}% of the grid points ({nselected} of {len(df)}, sorted by {sortlabel})'
    elif args.range is None:
        selected = df
        rangetag = 'all'
        title = f'All {len(df)} grid points'
    else:
        first, last = args.range
        selected = df.iloc[first:last + 1]
        rangetag = f'{first}_{last}'
        title = f'Grid points {first} to {last} of {len(df)}'
        title += f' (sorted by {sortlabel})' if sortlabel is not None else ' (in the order of the input file)'
    print(f'Selected {len(selected)} of {len(df)} grid points.')

    outputfile = args.outputfile
    if outputfile is None:
        outputfile = os.path.join(os.path.dirname(os.path.abspath(args.inputfile)),
            f'param_distributions_{args.sort if args.sort is not None else "unsorted"}_{rangetag}.png')
    plot_param_distributions(df, selected, outputfile, title=title)
