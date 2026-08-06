# Plot LayerCluster positions, coloured by the index of the SimCluster with
# which each LayerCluster shares the most DetIds.
#
# Note: this is an approximation. Individual (Sim/Rec)Hits do not carry their
# own x/y/z position (see the conversation this script was introduced in);
# only reconstructed objects like LayerCluster cache a position, computed by
# the clustering algorithm from the real detector geometry. So rather than
# plotting hit positions directly, this plots LayerCluster positions, and
# approximates "which SimCluster does this LayerCluster belong to" by DetId
# overlap: for each LayerCluster, find the SimCluster it shares the most
# DetIds with. The "sharing fraction" (shared DetIds / LayerCluster DetIds)
# is reported as a rough measure of how reliable that approximation is for a
# given LayerCluster - a LayerCluster made up of DetIds from several
# SimClusters in similar proportions will have a low fraction and an
# unreliable/arbitrary "best match".


import os
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


def make_outputdir(outputdir):
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)


def scatter_by_match(ax, xs, ys, is_matched, cs_matched, sizes, zs=None,
        unmatched_color='lightgrey', unmatched_alpha=0.3, unmatched_label='No SimCluster match'):
    '''
    Scatter unmatched LayerClusters (fixed dummy colour, semi-transparent, low
    zorder) and matched LayerClusters (coloured by SimCluster index, fully
    opaque, high zorder) onto the same axes, so matched points visually take
    precedence over unmatched ones wherever they overlap. Returns the
    matched-points scatter handle (for the colorbar), or None if there are no
    matched points to plot.
    '''
    um = ~is_matched
    args3d = (zs[um],) if zs is not None else ()
    if np.any(um):
        ax.scatter(xs[um], ys[um], *args3d, c=unmatched_color, s=sizes[um],
                   alpha=unmatched_alpha, zorder=1, label=unmatched_label)
    scat = None
    m = is_matched
    args3d = (zs[m],) if zs is not None else ()
    if np.any(m):
        scat = ax.scatter(xs[m], ys[m], *args3d, c=cs_matched, cmap='tab20', s=sizes[m], zorder=2)
    return scat


def plot_hist(values, bins, xlabel, ylabel, color='dodgerblue'):
    # basic plotting function, styled consistently with analysis/testing/check_simclusters.py
    yvals, edges = np.histogram(values, bins=bins)
    fig, ax = plt.subplots()
    ax.stairs(yvals, edges=edges, color=color, linewidth=3)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    fig.tight_layout()
    return fig, ax


def get_best_matching_simclusters(layerclusters, simclusters):
    '''
    For each LayerCluster, find the index of the SimCluster it shares the
    most DetIds with, and the corresponding sharing fraction (shared DetIds
    divided by the total number of DetIds in the LayerCluster - i.e. how
    "pure" the LayerCluster is with respect to this one SimCluster).

    Returns:
    - best_sc_idx: array of length nlc; -1 if no SimCluster shares any DetId
      with that LayerCluster.
    - best_sc_fraction: array of length nlc; 0 wherever best_sc_idx is -1.
    '''
    # map each DetId (as a plain rawId int, to compare consistently between
    # SimCluster.hits_and_fractions(), which already returns raw uint32_t ids,
    # and LayerCluster.hitsAndFractions(), which returns DetId objects) to the
    # SimCluster indices that include it.
    detid_to_scs = {}
    for sc_idx, sc in enumerate(simclusters):
        for detid, _ in sc.hits_and_fractions():
            detid_to_scs.setdefault(int(detid), []).append(sc_idx)

    nlc = len(layerclusters)
    best_sc_idx = np.full(nlc, -1, dtype=int)
    best_sc_fraction = np.zeros(nlc)
    for lc_idx, lc in enumerate(layerclusters):
        hits = lc.hitsAndFractions()
        if len(hits) == 0: continue
        counts = {}
        for detid, _ in hits:
            for sc_idx in detid_to_scs.get(detid.rawId(), []):
                counts[sc_idx] = counts.get(sc_idx, 0) + 1
        if len(counts) == 0: continue
        best_idx = max(counts, key=counts.get)
        best_sc_idx[lc_idx] = best_idx
        best_sc_fraction[lc_idx] = counts[best_idx] / len(hits)
    return best_sc_idx, best_sc_fraction


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_plots_layerclusters_by_simcluster')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('--input_config', default=None, nargs='+')
    parser.add_argument('--input_config_type', default='centralreco', choices=['centralreco', 'customreco'])
    parser.add_argument('--min_simclusters', default=None, type=int,
        help='Only process events with at least this many SimClusters.')
    parser.add_argument('--max_simclusters', default=None, type=int,
        help='Only process events with at most this many SimClusters.')
    parser.add_argument('--event_indices', default=None, type=int, nargs='+',
        help='Only process these event indices (1-based, in file order,'
             ' matching the "Now running on event N" printouts and the'
             ' test_N_* output filenames). Combines with --min_simclusters'
             '/--max_simclusters if those are also given.')
    parser.add_argument('--only_matched', default=False, action='store_true',
        help='Only plot LayerClusters matched to a SimCluster (the original'
             ' behavior of this script). By default (this flag unset), all'
             ' LayerClusters are plotted, with those unmatched to any'
             ' SimCluster shown in a fixed dummy colour - this keeps the dot'
             ' count/spread comparable to plot_ticlcandidates.py, which by'
             ' default also only has ticl candidate colouring for a subset'
             ' of LayerClusters.')
    args = parser.parse_args()

    # set input configs
    input_configs = []
    if args.input_config is not None:
        input_configs = args.input_config[:]
    else:
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_baseline.json'))
    print('Found following input configs:')
    print(json.dumps(input_configs, indent=2))

    # read events
    events = Events(args.inputfiles)
    # "caloparticles" and "tracksters" (baseline.json's CLUE3DHigh Trackster
    # collection) are not used here; only SimClusters and LayerClusters are.
    reader = Reader(input_configs, exclude=['caloparticles', 'tracksters'])
    make_outputdir(args.outputdir)

    # initialize counter
    event_counter = 0

    # accumulate sharing fractions across all processed events, to gauge
    # overall how reliable the "best-matching SimCluster" approximation is
    all_fractions = []

    # loop over events
    for event in events:
        event_counter += 1

        # optional event selection on event index, checked before reading the
        # event's collections since that read is the expensive part
        if args.event_indices is not None and event_counter not in args.event_indices:
            continue
        print(f'Now running on event {event_counter}...')

        # get collections
        collections = reader.read_event(event)
        simclusters = collections['simclusters']
        layerclusters = collections['layerclusters']

        # optional event selection on the number of SimClusters
        n_simclusters = len(simclusters)
        if args.min_simclusters is not None and n_simclusters < args.min_simclusters:
            print(f'  Skipping: {n_simclusters} SimClusters < min_simclusters ({args.min_simclusters})')
            continue
        if args.max_simclusters is not None and n_simclusters > args.max_simclusters:
            print(f'  Skipping: {n_simclusters} SimClusters > max_simclusters ({args.max_simclusters})')
            continue

        # match each LayerCluster to its best SimCluster
        best_sc_idx, best_sc_fraction = get_best_matching_simclusters(layerclusters, simclusters)
        matched = best_sc_idx >= 0
        all_fractions.extend(best_sc_fraction[matched].tolist())
        print(f'  {int(np.sum(matched))} / {len(layerclusters)} LayerClusters matched to a SimCluster')
        if np.sum(matched) == 0: continue

        # collect plotting data: by default all LayerClusters (matched ones
        # coloured by SimCluster index, unmatched ones in a fixed dummy colour -
        # see scatter_by_match), or only matched ones with --only_matched.
        # note: indices must be plain Python ints, not numpy ints, for cppyy's
        # vector::operator[] to accept them.
        keep_ids = [int(idx) for idx in np.nonzero(matched)[0]] if args.only_matched \
            else list(range(len(layerclusters)))
        xs = np.array([layerclusters[idx].position().x() for idx in keep_ids])
        ys = np.array([layerclusters[idx].position().y() for idx in keep_ids])
        zs = np.array([layerclusters[idx].position().z() for idx in keep_ids])
        es = np.array([layerclusters[idx].energy() for idx in keep_ids])
        is_matched = matched[keep_ids]
        cs_matched = best_sc_idx[keep_ids][is_matched]

        maxx = np.amax(np.abs(xs))
        maxy = np.amax(np.abs(ys))
        maxxy = max(maxx, maxy)
        maxe = np.amax(es)
        reles = es/maxe
        sizes = np.clip(30*reles, a_min=3, a_max=None)

        # make plot coloured by best-matching SimCluster index
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        scat = scatter_by_match(ax, xs, ys, is_matched, cs_matched, sizes, zs=zs)
        if scat is not None: plt.colorbar(scat, label="Best-matching SimCluster index")
        if not args.only_matched: ax.legend(loc='best')
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_simcluster_idx.png'), dpi=200)
        plt.close(fig)

        # same plot in x-y projection
        fig, ax = plt.subplots()
        scat = scatter_by_match(ax, xs, ys, is_matched, cs_matched, sizes)
        if scat is not None: plt.colorbar(scat, label="Best-matching SimCluster index")
        if not args.only_matched: ax.legend(loc='best')
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_simcluster_idx_xy.png'), dpi=200)
        plt.close(fig)

        # same plot in z-y projection
        fig, ax = plt.subplots()
        scat = scatter_by_match(ax, zs, ys, is_matched, cs_matched, sizes)
        if scat is not None: plt.colorbar(scat, label="Best-matching SimCluster index")
        if not args.only_matched: ax.legend(loc='best')
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_simcluster_idx_zy.png'), dpi=200)
        plt.close(fig)

        # stop processing if sufficient events have been processed
        if args.nentries > 0 and event_counter >= args.nentries: break
        if args.event_indices is not None and event_counter >= max(args.event_indices): break

    # print and plot summary statistics for the sharing fraction, to gauge
    # how reliable the "best-matching SimCluster" assignment above is
    all_fractions = np.array(all_fractions)
    if len(all_fractions) > 0:
        print(f'Sharing fraction (best-matching SimCluster DetIds / LayerCluster DetIds)'
              f' over {len(all_fractions)} matched LayerClusters:')
        print(f'  min:  {np.amin(all_fractions):.3f}')
        print(f'  mean: {np.mean(all_fractions):.3f}')
        print(f'  max:  {np.amax(all_fractions):.3f}')

        fig, ax = plot_hist(all_fractions, 50,
            'LayerCluster / SimCluster DetId sharing fraction', 'Number of LayerClusters')
        fig.savefig(os.path.join(args.outputdir, 'sharing_fraction.png'), bbox_inches='tight', dpi=200)
        plt.close(fig)
    else:
        print('No LayerCluster matched to any SimCluster; nothing to summarize.')
