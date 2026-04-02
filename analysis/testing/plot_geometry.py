# Plot the subdetector structure

# This is done by plotting the layer cluster position coloured by subdetector,
# and aggregating many events

import os
import sys
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

    # read input file from command line
    inputfile = sys.argv[1]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config_centralreco.json')
    outputdir = 'output_plots_geometry'

    # read events
    events = Events(inputfile)
    reader = Reader(input_config)

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

    # make output dir
    if not os.path.exists(outputdir): os.makedirs(outputdir)

    # make similar plot but coloured by layer
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
    fig.savefig(os.path.join(outputdir, f'test_lrs.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_lrs_xy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_lrs_zy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_zsides.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_zsides_xy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_zsides_zy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_subdets.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_subdets_xy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_subdets_zy.png'))
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
    fig.savefig(os.path.join(outputdir, f'test_layer_zcoord.png'))
    plt.close()
