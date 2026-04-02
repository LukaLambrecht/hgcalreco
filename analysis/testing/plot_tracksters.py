# Plot the point cloud of RecHits belonging to all Tracksters in an event

# DOES NOT WORK (YET?), because RecHits are not stored with a position,
# need to somehow load the geometry externally to convert detId into position,
# but not sure if this is possible in FWLite.

# Instead, can plot the Trackster barycenters (which are stored) as a proxy.


import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


if __name__=='__main__':

    # read input file from command line
    inputfile = sys.argv[1]

    # other settings (hard-coded for now)
    input_config = os.path.join(topdir, 'configs/input_config_centralreco.json')
    outputdir = 'output_plots_tracksters'

    # read events
    events = Events(inputfile)
    reader = Reader(input_config)

    # initialize counter
    event_counter = 0

    # loop over events
    for event in events:
        event_counter += 1
        print(f'Running on event {event_counter}...')

        # initialize plotting data
        xs, ys, zs, es, trs = [], [], [], [], []

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        tracksters = collections['tracksters']

        # do some event selection
        if len(caloparticles) != 2: continue
        if len(tracksters) < 2: continue

        # temp printouts for debugging
        #print(event_counter)
        #print(len(tracksters))
        #for tr in tracksters:
        #    pos = tr.barycenter()
        #    print(f'- {tr.eigenvalues()} | {pos.x()} {pos.y()} {pos.z()} | {tr.raw_energy()}')

        # loop over tracksters
        for tr_idx, tr in enumerate(tracksters):

            energy = tr.raw_energy()
            pos = tr.barycenter()
            xs.append(pos.x())
            ys.append(pos.y())
            zs.append(pos.z())
            es.append(energy)
            trs.append(tr_idx)

        xs = np.array(xs)
        ys = np.array(ys)
        zs = np.array(zs)
        es = np.array(es)
        trs = np.array(trs)

        maxx = np.amax(np.abs(xs))
        marginx = maxx*0.05
        maxy = np.amax(np.abs(ys))
        marginy = maxy*0.05
        maxz = np.amax(np.abs(zs))
        marginz = maxz*0.05
        maxxy = max(maxx, maxy)
        marginxy = maxxy*0.05
        maxe = np.amax(es)
        reles = es/maxe

        # make output directory
        if not os.path.exists(outputdir): os.makedirs(outputdir)

        # make plot coloured by energy
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(xs, ys, zs,
                    c = es,
                    cmap='jet',
                    #s=30*reles,
                    s=1,
        )
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim((-maxxy-marginxy, maxxy+marginxy))
        ax.set_ylim((-maxxy-marginxy, maxxy+marginxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_energy.png'))
        plt.close()

        # same plot in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(xs, ys,
                    c = es,
                    cmap='jet',
                    #s=30*reles,
                    s=1,
        )
        plt.colorbar(sc, label="Energy")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-maxxy-marginxy, maxxy+marginxy))
        ax.set_ylim((-maxxy-marginxy, maxxy+marginxy))
        fig.savefig(os.path.join(outputdir, f'test_{event_counter}_energy_xy.png'))
        plt.close()

        # same plot in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(zs, ys,
                    c = es,
                    cmap='jet',
                    #s=30*reles,
                    s=1,
        )
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
        ax.set_xlim((-maxxy-marginxy, maxxy+marginxy))
        ax.set_ylim((-maxxy-marginxy, maxxy+marginxy))
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
        ax.set_xlim((-maxxy-marginxy, maxxy+marginxy))
        ax.set_ylim((-maxxy-marginxy, maxxy+marginxy))
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
