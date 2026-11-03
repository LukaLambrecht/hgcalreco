# Plot LayerCluster positions, coloured by the truth Branch (of the MC-truth graph)
# they are assigned to, for different truth levels side by side (e.g. "signal" vs "caloBoundary").
#
# The input is the output of the re-reco (see run-hgcal-reco) on a sample produced with
# sample-production's --output-mode truth, which contains the flattened LayerCluster to
# truth Branch association (see truth-graph-validation/status.md).
#
# For a given truth level, each LayerCluster is assigned to the member of that level
# with the best (i.e. lowest) score in the reco-to-truth association with the "Fixed" working point
# (which lists all candidate Branches that share energy with the LayerCluster;
# a score of 0 means that the Branch explains all of the LayerCluster energy).
# LayerClusters that do not share energy with any member of the level
# ("no associated truth particle at this level") are shown in light grey (if any). Plots are made for both endcaps.
# Level membership is taken from the truth graph itself; the printed summary also indicates
# whether each member is in the corresponding list of truth targets (truthBranchTargets:truthToRecoTargets*
# or truthBranchTargets:signalSeeds) used as efficiency denominator in the analysis.


import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from DataFormats.FWLite import Events, Handle
from PhysicsTools.TruthInfo.graphTools import eventGraphs


# categorical colours (fixed order, assigned per truth particle, never cycled)
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6']
OTHER_COLOR = '#6b6b6b' # level members beyond the number of available colours
UNASSIGNED_COLOR = '#d4d4d4' # no member of the level shares energy with the LayerCluster

# product name of the efficiency denominator per level
# (the "signal" level corresponds to the signal seeds)
TARGETS = {
    'signal': 'signalSeeds',
    'caloBoundary': 'truthToRecoTargetsCaloBoundary',
    'reconstructableFinalState': 'truthToRecoTargetsReconstructableFinalState',
    'stableDecayProducts': 'truthToRecoTargetsStableDecayProducts',
}

PDG_NAMES = {211: 'π+', -211: 'π−', 111: 'π0', 22: 'γ', 11: 'e−', -11: 'e+', 13: 'μ−', -13: 'μ+',
    2112: 'n', -2112: 'n̄', 2212: 'p', -2212: 'p̄', 321: 'K+', -321: 'K−', 130: 'K0L', 310: 'K0S'}


def get(event, typ, label, instance, process='HGCALTICL'):
    handle = Handle(typ)
    event.getByLabel(label, instance, process, handle)
    return list(handle.product()) if handle.isValid() else None


def get_layerclusters(event):
    for typ in ['std::vector<reco::CaloCluster>', 'std::vector<reco::io_v1::CaloCluster>']:
        try:
            lcs = get(event, typ, 'hgcalMergeLayerClusters', '')
            if lcs is not None: return lcs
        except Exception: continue
    raise Exception('Could not read LayerClusters.')


def get_lc_assignment(lc_ids, branch_ids, scores, nlc, members):
    '''
    Assign each LayerCluster to the member of a truth level with the lowest score.
    Returns an array of length nlc with the particle id of the assigned member (-1 if none),
    and an array with the corresponding score (nan if none).
    '''
    members = set(members)
    assigned = np.full(nlc, -1, dtype=int)
    best = np.full(nlc, np.inf)
    for lc, branch, score in zip(lc_ids, branch_ids, scores):
        if branch in members and score < best[lc]:
            best[lc] = score
            assigned[lc] = branch
    best[assigned < 0] = np.nan
    return assigned, best


def particle_name(graph, pid):
    pdg = graph.pdgId(pid)
    return PDG_NAMES.get(pdg, str(pdg))


def particle_label(graph, pid):
    return f'{particle_name(graph, pid)} (id {pid})'


def signal_ancestor(graph, pid, signal):
    '''Return the signal particle that pid descends from (or pid itself), or -1.'''
    seen, todo = set(), [pid]
    while todo:
        p = todo.pop()
        if p in signal: return p
        if p in seen: continue
        seen.add(p)
        todo += list(graph.parents(p))
    return -1


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-o', '--outputdir', default='output_plots_layerclusters_by_branch')
    parser.add_argument('--levels', default=['signal', 'caloBoundary'], nargs='+', choices=list(TARGETS.keys()))
    parser.add_argument('--event_indices', default=None, type=int, nargs='+',
        help='Event indices (0-based, in file order) to plot; default: the event where the levels'
             ' differ most, among events where all level members fit in the colour palette.')
    parser.add_argument('--max_rows', default=15, type=int,
        help='Maximum number of level members to print per level in the summary.')
    args = parser.parse_args()
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    # read all events
    U, F = 'std::vector<unsigned int>', 'std::vector<float>'
    mapname = 'hgcalMergeLayerClustersRecoToTruthFixed'
    graphs = list(eventGraphs(args.inputfile))
    events = []
    for idx, event in enumerate(Events(args.inputfile)):
        lcs = get_layerclusters(event)
        aux = event.eventAuxiliary()
        data = {
            'eventid': f'{aux.run()}:{aux.luminosityBlock()}:{aux.event()}',
            'x': np.array([lc.position().x() for lc in lcs]),
            'y': np.array([lc.position().y() for lc in lcs]),
            'z': np.array([lc.position().z() for lc in lcs]),
            'e': np.array([lc.energy() for lc in lcs]),
            'lc_ids': get(event, U, f'flatten{mapname[0].upper()}{mapname[1:]}', f'{mapname}FlatLCIdx'),
            'branch_ids': get(event, U, f'flatten{mapname[0].upper()}{mapname[1:]}', f'{mapname}FlatBranchIdx'),
            'scores': get(event, F, f'flatten{mapname[0].upper()}{mapname[1:]}', f'{mapname}FlatScore'),
            'targets': {level: set(get(event, U, 'truthBranchTargets', TARGETS[level])) for level in args.levels},
        }
        if data['lc_ids'] is None:
            raise Exception('LayerCluster to truth Branch association not found in input;'
                            ' was the re-reco run on a sample with the truth graph?')
        graph = graphs[idx]
        data['graph'] = graph
        data['signal'] = list(graph.signalParticles())
        data['members'] = {level: list(graph.particlesOfLevel(level)) for level in args.levels}
        data['assignment'] = {level: get_lc_assignment(data['lc_ids'], data['branch_ids'], data['scores'],
                                                       len(lcs), data['members'][level])[0] for level in args.levels}
        events.append(data)

    # print an overview of all events
    def ediff(data):
        a = data['assignment']
        return np.sum(data['e'][a[args.levels[0]] != a[args.levels[-1]]])
    def nassigned(data, level):
        return len(set(data['assignment'][level][data['assignment'][level] >= 0]))
    print('Overview (index, event id, number of level members with assigned LayerClusters,'
          ' LayerCluster energy assigned differently between levels):')
    for idx, data in enumerate(events):
        counts = ', '.join(f'{level}: {nassigned(data, level)}' for level in args.levels)
        print(f'  {idx:3d}  {data["eventid"]:12s}  {counts}  {ediff(data):7.1f} GeV')

    # choose events to plot: by default the one where the levels assign the most LayerCluster energy
    # differently, among events where all level members fit in the colour palette
    if args.event_indices is None:
        candidates = [idx for idx, data in enumerate(events)
                      if all(nassigned(data, level) <= len(COLORS) for level in args.levels)]
        if len(candidates) == 0: candidates = list(range(len(events)))
        args.event_indices = [max(candidates, key=lambda idx: ediff(events[idx]))]
        print(f'Selected event index {args.event_indices[0]}')

    for idx in args.event_indices:
        data = events[idx]
        graph, signal = data['graph'], data['signal']

        # make plots for both endcaps (that contain LayerClusters)
        for side in [1, -1]:
            onside = (data['z'] * side) > 0
            if not np.any(onside): continue
            sidestr = 'zpos' if side > 0 else 'zneg'

            # assign colours per truth particle (consistent across levels):
            # signal particles first, then other level members by assigned LayerCluster energy
            energy_per_member = {}
            for level in args.levels:
                a = data['assignment'][level]
                for pid in set(a[onside & (a >= 0)]):
                    energy_per_member[pid] = max(energy_per_member.get(pid, 0), np.sum(data['e'][onside & (a == pid)]))
            order = [p for p in signal if p in energy_per_member]
            order += sorted([p for p in energy_per_member if p not in signal], key=lambda p: -energy_per_member[p])
            colors = {pid: COLORS[i] for i, pid in enumerate(order[:len(COLORS)])}

            # print summary
            print(f'Event {idx} ({data["eventid"]}): {len(data["e"])} LayerClusters'
                  f' ({np.sum(onside)} in the {"+" if side > 0 else "-"}z endcap)')
            for level in args.levels:
                a = data['assignment'][level]
                print(f'  level {level}: {len(data["members"][level])} members in the event')
                rows = []
                pids = sorted(set(a[onside & (a >= 0)]), key=lambda p: -np.sum(data['e'][onside & (a == p)]))
                for pid in pids[:args.max_rows]:
                    sel = onside & (a == pid)
                    anc = signal_ancestor(graph, pid, set(signal))
                    rows.append(f'    {particle_label(graph, pid):18s} from signal {anc:3d}'
                                f'   {np.sum(sel):5d} LCs   {np.sum(data["e"][sel]):7.2f} GeV'
                                f'   in targets: {"yes" if pid in data["targets"][level] else "no"}')
                if len(pids) > args.max_rows: rows.append(f'    ... and {len(pids) - args.max_rows} more')
                print('\n'.join(rows))
                sel = onside & (a < 0)
                print(f'    {"no associated truth particle at this level":18s} {"":16s} {np.sum(sel):5d} LCs   {np.sum(data["e"][sel]):7.2f} GeV')

            # make the plot: one row per level, columns: x vs z and y vs z
            sizes = np.clip(80 * np.sqrt(data['e'] / np.amax(data['e'][onside])), a_min=3, a_max=None)
            fig, axs = plt.subplots(len(args.levels), 2, figsize=(12, 4.6 * len(args.levels)),
                                    sharex=True, sharey=True, squeeze=False)
            for row, level in enumerate(args.levels):
                a = data['assignment'][level]
                pointcolors = np.array([colors.get(pid, OTHER_COLOR) if pid >= 0 else UNASSIGNED_COLOR for pid in a])
                for col, coord in enumerate(['x', 'y']):
                    ax = axs[row, col]
                    # not associated first (behind), then associated, larger LayerClusters on top
                    for mask, zorder, alpha in [(onside & (a < 0), 1, 0.6), (onside & (a >= 0), 2, 0.9)]:
                        ids = np.nonzero(mask)[0]
                        ids = ids[np.argsort(data['e'][ids])]
                        ax.scatter(data['z'][ids], data[coord][ids], s=sizes[ids], c=pointcolors[ids],
                                   alpha=alpha, zorder=zorder, linewidths=0)
                    ax.set_ylabel(f'{coord} [cm]', fontsize=12)
                    ax.grid(visible=True, color='#e8e8e8', linewidth=0.6, zorder=0)
                    ax.set_axisbelow(True)
                    if row == len(args.levels) - 1: ax.set_xlabel('z [cm]', fontsize=12)
                # legend with direct labels per level member (plus associated energy)
                handles = []
                for pid in order:
                    sel = onside & (a == pid)
                    if not np.any(sel): continue
                    if pid not in colors: continue
                    handles.append(Line2D([], [], marker='o', linestyle='', color=colors[pid], markersize=8,
                        label=f'{particle_name(graph, pid)}: {np.sum(data["e"][sel]):.1f} GeV'))
                nother = len([p for p in set(a[onside & (a >= 0)]) if p not in colors])
                if nother > 0:
                    sel = onside & (a >= 0) & np.array([p not in colors for p in a])
                    handles.append(Line2D([], [], marker='o', linestyle='', color=OTHER_COLOR, markersize=8,
                        label=f'{nother} other truth particles: {np.sum(data["e"][sel]):.1f} GeV'))
                # LayerClusters that share no energy with any truth particle of this level (if any)
                sel = onside & (a < 0)
                if np.any(sel):
                    handles.append(Line2D([], [], marker='o', linestyle='', color=UNASSIGNED_COLOR, markersize=8,
                        label=f'no associated truth particle\nat this level: {np.sum(data["e"][sel]):.1f} GeV'))
                axs[row, 1].legend(handles=handles, loc='center left', bbox_to_anchor=(1.02, 0.5),
                                   frameon=False, fontsize=10)
                axs[row, 0].set_title(f'LayerClusters coloured by associated truth particle (truth level "{level}")',
                                      loc='left', fontsize=13)
            fig.tight_layout()
            outfile = os.path.join(args.outputdir, f'event_{idx}_{sidestr}_layerclusters_by_branch.png')
            fig.savefig(outfile, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f'Saved {outfile}')
