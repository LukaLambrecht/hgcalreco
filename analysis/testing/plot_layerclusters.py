# Plot the point cloud of RecHits belonging to all Tracksters in an event

# DOES NOT WORK (YET?), because RecHits are not stored with a position,
# need to somehow load the geometry externally to convert detId into position,
# but not sure if this is possible in FWLite.

# Instead, can plot the LayerCluster barycenters (which are stored) as a proxy.


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
    input_config = os.path.join(topdir, 'configs/input_config.json')
    outputdir = 'plots_layerclusters'

    # read events
    events = Events(inputfile)
    reader = Reader(input_config)

    # initialize counter
    event_counter = 0

    # loop over events
    for event in events:
        event_counter += 1

        # initialize plotting data
        xs, ys, zs, es, lcs, trs, lrs, zsides, subdets = [], [], [], [], [], [], [], [], []

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        tracksters = collections['tracksters']
        layerclusters = collections['layerclusters']

        # do some event selection
        if len(caloparticles) != 2: continue
        if len(tracksters) < 2: continue

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

        # make plot coloured by energy
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c = es,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_energy.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c = es,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_energy_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c = es,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_energy_zy.png'))
        plt.close()

        # make similar plot but coloured by trackster index
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=trs,
                    cmap='tab20',
                    s=30*reles)
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_trs.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=trs,
                    cmap='tab20',
                    s=30*reles)
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_trs_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=trs,
                    cmap='tab20',
                    s=30*reles)
        plt.colorbar(sc, label="Trackster index")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_trs_zy.png'))
        plt.close()

        # make similar plot but coloured by layer
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=lrs,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_lrs.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=lrs,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_lrs_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=lrs,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Layer")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_lrs_zy.png'))
        plt.close()

        # make similar plot but coloured by zside
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=zsides,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_zsides.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=zsides,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_zsides_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=zsides,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Z-side")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_zsides_zy.png'))
        plt.close()

        # make similar plot but coloured by subdetector
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c=subdets,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_subdets.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c=subdets,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy, maxxy))
        ax.set_ylim((-maxxy, maxxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_subdets_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c=subdets,
                    cmap='jet',
                    s=30*reles)
        plt.colorbar(sc, label="Subdetector")
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_subdets_zy.png'))
        plt.close()
