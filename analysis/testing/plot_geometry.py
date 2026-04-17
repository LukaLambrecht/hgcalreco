# Plot the subdetector structure

# This is done by plotting the layer cluster position coloured by subdetector,
# and aggregating many events

# This serves as a check that the subdetector is correctly extracted
# from the detector IDs from the hits belonging to the layerclusters.


import os
import sys
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


if __name__=='__main__':

    # command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile', required=True)
    parser.add_argument('-o', '--outputdir', default='output_plots_geometry')
    parser.add_argument('-c', '--config', default=os.path.join(topdir, 'configs/input_config_centralreco.json'))
    parser.add_argument('-n', '--nevents', type=int, default=-1)
    args = parser.parse_args()

    # read events
    events = Events(args.inputfile)
    reader = Reader(args.config)

    # initialize counter
    event_counter = 0

    # initialize plotting data
    xs, ys, zs, es, lcs, trs, lrs, zsides, subdets = [], [], [], [], [], [], [], [], []

    # loop over events
    for event in events:
        event_counter += 1
        print(f'Now running on event {event_counter}...')

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        tracksters = collections['tracksters']
        layerclusters = collections['layerclusters']

        # do some event selection
        # (probably not needed for this type of plot)
        #if len(caloparticles) != 2: continue
        #if len(tracksters) < 2: continue

        # loop over tracksters
        for tr_idx, tr in enumerate(tracksters):

            # collect hits
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

        if args.nevents > 0 and event_counter >= args.nevents: break

    xs = np.array(xs)
    ys = np.array(ys)
    zs = np.array(zs)
    rs = np.sqrt(np.square(xs) + np.square(ys))
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

    # make output dir
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    # plot layercluster position coloured by layer number
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(xs, ys, zs,
                    c=lrs,
                    cmap='jet',
                    s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_zlabel("z [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_lrs.png'))
    plt.close()

    # same plot in x-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(xs, ys,
            c=lrs,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_lrs_xy.png'))
    plt.close()

    # same plot in z-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(zs, ys,
            c=lrs,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_lrs_zy.png'))
    plt.close()

    # same plot but take absolute value of z coordinate
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(zs), ys,
            c=lrs,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_lrs_zy_abs.png'))
    plt.close()

    # same plot but in z-r projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(zs), rs,
            c=lrs,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("r [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_lrs_zr_abs.png'))
    plt.close()

    # make similar plot but coloured by zside
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(xs, ys, zs,
            c=zsides,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Z-side")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_zlabel("z [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_zsides.png'))
    plt.close()

    # same plot in x-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(xs, ys,
            c=zsides,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Z-side")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_zsides_xy.png'))
    plt.close()

    # same plot in z-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(zs, ys,
            c=zsides,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Z-side")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_zsides_zy.png'))
    plt.close()

    # same plot but take absolute value of z coordinate
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(zs), ys,
            c=zsides,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Z-side")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_zsides_zy_abs.png'))
    plt.close()

    # make similar plot but coloured by subdetector
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(xs, ys, zs,
            c=subdets,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Subdetector")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_zlabel("z [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_subdets.png'))
    plt.close()

    # same plot in x-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(xs, ys,
            c=subdets,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Subdetector")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    fig.savefig(os.path.join(args.outputdir, f'test_subdets_xy.png'))
    plt.close()

    # same plot in z-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(zs, ys,
            c=subdets,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Subdetector")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_subdets_zy.png'))
    plt.close()

    # same plot but take absolute value of z coordinate
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(zs), ys,
            c=subdets,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Subdetector")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("y [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_subdets_zy_abs.png'))
    plt.close()

    # same plot in z-r projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(zs), rs,
            c=subdets,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Subdetector")
    ax.set_xlabel("z [cm]")
    ax.set_ylabel("r [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_subdets_zr_abs.png'))
    plt.close()

    # plot correlation between z coordinate and layer number
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(np.abs(lrs), np.abs(zs),
            c=lrs,
            cmap='jet',
            s=1)
    plt.colorbar(sc, label="Layer")
    ax.set_xlabel("|Layer|")
    ax.set_ylabel("|z| [cm]")
    fig.savefig(os.path.join(args.outputdir, f'test_layer_zcoord.png'))
    plt.close()
