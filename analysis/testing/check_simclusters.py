# Do some sanity checks.
# In particular, check simcluster hits and fractions and their energy.

# Conclusions so far:
# - CaloParticle energy matches sum of SimCluster energies.
# - The fractions per SimCluster do not add up to 1;
#   they are probably not the faction of SimCluster energy in that hit,
#   but the fraction of energy in that hit coming from this SimCluster.
# - In the overwhelming majority of cases, the fractions are 1.
#   (But maybe this changes with more crowded events and/or pileup.)


import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

from tools.iotools import Reader


def deltaR(p1, p2):
    delta_eta = p1.eta() - p2.eta()
    delta_phi = p1.phi() - p2.phi()
    delta_phi = (delta_phi + np.pi) % (2*np.pi) - np.pi
    return np.sqrt(delta_eta**2 + delta_phi**2)


def plot_hist(values, bins, xlabel, ylabel, color='dodgerblue'):
    # basic plotting function, styled consistently with analysis/efficiency/plot_metrics_lc.py::plot
    yvals, edges = np.histogram(values, bins=bins)
    fig, ax = plt.subplots()
    ax.stairs(yvals, edges=edges, color=color, linewidth=3)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    fig.tight_layout()
    return fig, ax


def plot_scatter(xvals, yvals, xlabel, ylabel, color='dodgerblue'):
    # basic 2D scatter, styled consistently with plot_hist above
    fig, ax = plt.subplots()
    ax.scatter(xvals, yvals, color=color, s=10, alpha=0.3)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    fig.tight_layout()
    return fig, ax


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_check_simclusters')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    args = parser.parse_args()
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    # other settings (hard-coded for now)
    # note: input_config_centralreco.json was later split into per-purpose files;
    # this script only needs CaloParticles and SimClusters, both in the baseline
    # config; the hits/tracksters/layerclusters collections are excluded below
    # since nothing here reads them.
    input_config = os.path.join(topdir, 'configs/input_config_centralreco_baseline.json')

    # read events
    events = Events(args.inputfiles)
    reader = Reader(input_config, exclude=['tracksters', 'layerclusters'])

    # initialize counters
    nevents = 0

    # initialize accumulators for the summary plots below
    n_simclusters_per_cp = []
    sc_to_cp_energy_ratio = []
    cp_sc_deltar = []
    # paired versions of the two lists above, for the 2D scatter plot: appended
    # together so they stay aligned entry-for-entry, unlike the two lists above
    # (sc_to_cp_energy_ratio skips entries with cp.energy() <= 0, cp_sc_deltar
    # does not, so their indices are not guaranteed to line up with each other).
    sc_to_cp_energy_ratio_paired = []
    cp_sc_deltar_paired = []

    # loop over event
    for event in events:
        nevents += 1
        print(f'--- Event {nevents} ---')

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']

        # loop over simclusters
        for cp in caloparticles:
            print('--- calo particle ---')
            print(cp.energy())
            sc_energy_sum = 0
            for sc_ref in cp.simClusters():
                sc = sc_ref.get()
                sc_energy_sum += sc.energy()
            print(len(cp.simClusters()), sc_energy_sum)
            n_simclusters_per_cp.append(len(cp.simClusters()))
            for sc_ref in cp.simClusters():
                sc = sc_ref.get()
                fractions = []

                # loop over hits per simcluster
                hits = sc.hits_and_fractions()
                for hit in hits:
                    detid = hit.first
                    fraction = hit.second
                    fractions.append(fraction)
                #print(fractions)
                print(sum(fractions))

                # accumulate quantities for the summary plots below
                dr = deltaR(cp, sc)
                cp_sc_deltar.append(dr)
                if cp.energy() > 0:
                    ratio = sc.energy() / cp.energy()
                    sc_to_cp_energy_ratio.append(ratio)
                    sc_to_cp_energy_ratio_paired.append(ratio)
                    cp_sc_deltar_paired.append(dr)

        # stop processing if sufficient events have been processed
        if args.nentries > 0 and nevents >= args.nentries: break

    # make summary plots
    # note: CaloParticle.eta()/phi() and SimCluster.eta()/phi() are both derived
    # from the object's four-momentum (i.e. flight direction), not a shower
    # position; deltaR below compares those directions, not detector positions.

    n_simclusters_per_cp = np.array(n_simclusters_per_cp)
    maxval = max(int(np.amax(n_simclusters_per_cp)), 1) if len(n_simclusters_per_cp) > 0 else 1
    fig, ax = plot_hist(n_simclusters_per_cp, np.arange(-0.5, maxval+1.5, 1),
        'Number of SimClusters per CaloParticle', 'Number of CaloParticles')
    fig.savefig(os.path.join(args.outputdir, 'n_simclusters_per_caloparticle.png'), bbox_inches='tight')
    plt.close(fig)

    sc_to_cp_energy_ratio = np.array(sc_to_cp_energy_ratio)
    fig, ax = plot_hist(sc_to_cp_energy_ratio, 50,
        'SimCluster / parent CaloParticle energy', 'Number of SimClusters')
    fig.savefig(os.path.join(args.outputdir, 'sc_to_cp_energy_ratio.png'), bbox_inches='tight')
    plt.close(fig)

    cp_sc_deltar = np.array(cp_sc_deltar)
    fig, ax = plot_hist(cp_sc_deltar, 50,
        r'Flight direction $\Delta R$', 'Number of SimClusters')
    fig.savefig(os.path.join(args.outputdir, 'cp_sc_deltar.png'), bbox_inches='tight')
    plt.close(fig)

    sc_to_cp_energy_ratio_paired = np.array(sc_to_cp_energy_ratio_paired)
    cp_sc_deltar_paired = np.array(cp_sc_deltar_paired)
    fig, ax = plot_scatter(cp_sc_deltar_paired, sc_to_cp_energy_ratio_paired,
        r'Flight direction $\Delta R$', 'SimCluster / parent CaloParticle energy')
    fig.savefig(os.path.join(args.outputdir, 'cp_sc_deltar_vs_energy_ratio.png'), bbox_inches='tight')
    plt.close(fig)

    # same scatter, with the y-axis (energy ratio) in log scale: the linear version
    # above squashes almost everything near y=0, since most SimClusters carry only
    # a small fraction of their parent CaloParticle's energy.
    fig, ax = plot_scatter(cp_sc_deltar_paired, sc_to_cp_energy_ratio_paired,
        r'Flight direction $\Delta R$', 'SimCluster / parent CaloParticle energy')
    ax.set_yscale('log')
    fig.savefig(os.path.join(args.outputdir, 'cp_sc_deltar_vs_energy_ratio_logy.png'), bbox_inches='tight')
    plt.close(fig)

    print(f'Wrote summary plots to {args.outputdir}')
