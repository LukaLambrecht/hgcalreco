# Plot LayerCluster barycenters for all clusters in an event

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
from tools.geometrytools import get_layercluster_layer
from tools.geometrytools import get_layercluster_zside
from tools.geometrytools import get_layercluster_subdetid


def make_outputdir(outputdir):
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_plots_layerclusters')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('--input_config', default=None, nargs='+')
    parser.add_argument('--input_config_type', default='centralreco', choices=['centralreco', 'customreco'])
    # By default this script plots layer clusters attached to the CLUE3DHigh
    # Trackster collection. With --from_ticl, it instead follows the final
    # merged Tracksters produced by ticlCandidate, matching the layer clusters
    # reached through TICLCandidate.tracksters() in plot_ticlcandidates.py.
    # These can differ because final TICL candidates may include selected
    # recovery Tracksters in addition to the main CLUE3DHigh output.
    parser.add_argument('--from_ticl', default=False, action='store_true',
        help='Plot layer clusters from final merged TICL candidate tracksters instead of CLUE3DHigh-only tracksters.')
    args = parser.parse_args()

    # set input configs
    input_configs = []
    if args.input_config is not None:
        # if input configs are specified on the command line, they take precedence
        input_configs = args.input_config[:]
    else:
        # else determine input configs automatically
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_baseline.json'))
        if args.from_ticl:
            input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_ticl.json'))
    print('Found following input configs:')
    print(json.dumps(input_configs, indent=2))

    # read events
    events = Events(args.inputfiles)
    reader = Reader(input_configs)
    make_outputdir(args.outputdir)

    # initialize counter
    event_counter = 0

    # loop over events
    for event in events:
        event_counter += 1
        print(f'Now running on event {event_counter}...')

        # initialize plotting data
        xs, ys, zs, es, lcs, trs, lrs, zsides, subdets = [], [], [], [], [], [], [], [], []

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        # "tracksters" is CLUE3DHigh-only. "tracksters_merge" is the final
        # Trackster collection written by ticlCandidate and referenced by
        # TICLCandidate.tracksters(); it includes the subset of recovery
        # Tracksters that survives into final TICL candidates.
        tracksters = collections['tracksters_merge'] if args.from_ticl else collections['tracksters']
        layerclusters = collections['layerclusters']

        # do some event selection
        #if len(caloparticles) != 2: continue
        #if len(tracksters) < 2: continue

        # loop over tracksters
        for tr_idx, tr in enumerate(tracksters):

            # collect layerclusters
            lc_ids = tr.vertices()
            for lc_idx in lc_ids:

                lc = layerclusters[lc_idx]
                energy = lc.energy()
                pos = lc.position()
                layer = get_layercluster_layer(lc, absolute_value=True)
                zside = get_layercluster_zside(lc)
                subdet = get_layercluster_subdetid(lc)
                xs.append(pos.x())
                ys.append(pos.y())
                zs.append(pos.z())
                es.append(energy)
                lcs.append(lc_idx)
                trs.append(tr_idx)
                lrs.append(layer)
                zsides.append(zside)
                subdets.append(subdet)

        xs = np.array(xs)
        ys = np.array(ys)
        zs = np.array(zs)
        es = np.array(es)
        trs = np.array(trs)
        lrs = np.array(lrs)
        zsides = np.array(zsides)
        subdets = np.array(subdets)

        maxx = np.amax(np.abs(xs))
        maxy = np.amax(np.abs(ys))
        maxz = np.amax(np.abs(zs))
        maxxy = max(maxx, maxy)
        maxe = np.amax(es)
        reles = es/maxe

        # make plot coloured by energy
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c = es,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_energy.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c = es,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_energy_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c = es,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_energy_zy.png'))
        plt.close()

        # make similar plot but coloured by trackster index
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=trs,
                    cmap='tab20',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trs.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=trs,
                    cmap='tab20',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trs_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=trs,
                    cmap='tab20',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trs_zy.png'))
        plt.close()

        # make similar plot but coloured by layer
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=lrs,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_lrs.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=lrs,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_lrs_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=lrs,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_lrs_zy.png'))
        plt.close()

        # make similar plot but coloured by zside
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=zsides,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_zsides.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=zsides,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_zsides_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=zsides,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_zsides_zy.png'))
        plt.close()

        # make similar plot but coloured by subdetector
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=subdets,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_subdets.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=subdets,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_subdets_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=subdets,
                    cmap='jet',
                    s = np.clip(30*reles, a_min=3, a_max=None),
                    alpha = np.clip(reles, a_min=0.15, a_max=None)
        )
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_subdets_zy.png'))
        plt.close()

        # break loop after a fixed number of events
        if args.nentries > 0 and event_counter >= args.nentries: break
