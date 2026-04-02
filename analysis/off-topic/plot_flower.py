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
    outputdir = 'output_plots'

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
    mask = (zs > 0)
    sc = ax.scatter(xs[mask], ys[mask], zs[mask],
                    c=lrs[mask],
                    cmap='Reds',
                    s=5)
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    ax.set_zlim((-600, 600))
    ax.axis('off')
    fig.savefig(os.path.join(outputdir, f'flower.png'), dpi=600)
    plt.close()

    # same plot in x-y projection
    fig = plt.figure()
    ax = fig.add_subplot(111)
    sc = ax.scatter(xs, ys,
            c=lrs,
            cmap='RdPu',
            s=5)
    ax.set_xlim((-maxxy, maxxy))
    ax.set_ylim((-maxxy, maxxy))
    ax.axis('off')
    fig.savefig(os.path.join(outputdir, f'flower_xy.png'), dpi=600)
    plt.close()
