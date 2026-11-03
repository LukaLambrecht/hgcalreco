# Investigate the number of "caloBoundary" truth particles per signal particle,
# i.e. into how many particles a signal particle (e.g. a gun pion) has split up
# (by interactions in the tracker material, decays, ...) by the time it reaches the calorimeter.
#
# This only uses the MC-truth graph (see truth-graph-validation/status.md),
# so it can be run directly on the output of sample-production with --output-mode truth
# (no re-reco or associations needed).
#
# For each signal particle, the caloBoundary particles are counted among its descendants
# in the truth graph (including the signal particle itself, if it reaches the calorimeter unchanged;
# in that case the multiplicity is 1). Note that caloBoundary particles can have very low energy
# (e.g. delta rays or bremsstrahlung photons), so the multiplicity is also counted with a minimum energy.
#
# Note: for speed, the truth::Graph is accessed directly through its C++ interface
# (only the signal particles and their descendants are touched),
# rather than converting the full graph to python (as e.g. PhysicsTools.TruthInfo.graphTools.eventGraphs does),
# which is very slow for pileup samples with O(100k) particles per event.
#
# Output:
# - inclusive distribution of the multiplicity;
# - mean multiplicity as a function of signal particle pT and |eta|;
# - fraction of signal particles with multiplicity > 1 as a function of signal particle pT and |eta|;
# - a parquet file with one row per signal particle, for further studies.


import os
import sys
import math
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from DataFormats.FWLite import Events, Handle
from PhysicsTools.TruthInfo.graphTools import LEVEL_BITS


def plot_hist(values, bins, xlabel, ylabel, color='dodgerblue', logy=False):
    # basic plotting function, styled consistently with analysis/testing/check_simclusters.py
    yvals, edges = np.histogram(values, bins=bins)
    fig, ax = plt.subplots()
    ax.stairs(yvals, edges=edges, color=color, linewidth=3)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    if logy: ax.set_yscale('log')
    fig.tight_layout()
    return fig, ax


def plot_trend(xvals, yvals, bins, xlabel, ylabel, mode='mean', color='dodgerblue'):
    '''
    Plot the mean of yvals (mode "mean", with standard error of the mean as error bars)
    or the fraction of yvals that is True (mode "fraction", with binomial uncertainty),
    in bins of xvals.
    '''
    centers, widths, ys, errs = [], [], [], []
    for low, high in zip(bins[:-1], bins[1:]):
        sel = (xvals >= low) & (xvals < high)
        n = np.sum(sel)
        if n == 0: continue
        centers.append((low + high) / 2)
        widths.append((high - low) / 2)
        if mode == 'mean':
            ys.append(np.mean(yvals[sel]))
            errs.append(np.std(yvals[sel]) / np.sqrt(n) if n > 1 else 0)
        else:
            frac = np.mean(yvals[sel])
            ys.append(frac)
            errs.append(np.sqrt(frac * (1 - frac) / n))
    fig, ax = plt.subplots()
    ax.errorbar(centers, ys, xerr=widths, yerr=errs, color=color, linestyle='', marker='o', markersize=6, linewidth=2)
    ax.set_xlabel(xlabel, fontsize=15)
    ax.set_ylabel(ylabel, fontsize=15)
    ax.tick_params(axis='both', which='both', labelsize=15)
    ax.grid(visible=True, which='both', axis='both')
    if mode == 'fraction': ax.set_ylim((0, 1.05))
    else: ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig, ax


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_plots_caloboundary_multiplicity')
    parser.add_argument('-n', '--nentries', default=-1, type=int,
        help='Maximum number of events to process per input file (default: all).')
    parser.add_argument('--level', default='caloBoundary',
        help='Truth level to count per signal particle (default: caloBoundary).')
    parser.add_argument('--min_energy', default=1., type=float,
        help='Minimum energy (in GeV) for the alternative multiplicity count (default: 1 GeV).')
    parser.add_argument('--pt_bins', default=list(np.linspace(0, 200, 11)), type=float, nargs='+')
    parser.add_argument('--abseta_bins', default=list(np.linspace(1.5, 3.0, 11)), type=float, nargs='+')
    args = parser.parse_args()
    if not os.path.exists(args.outputdir): os.makedirs(args.outputdir)

    # loop over events and signal particles
    levelbit = LEVEL_BITS[args.level]
    handle = Handle('truth::Graph')
    rows = []
    for inputfile in args.inputfiles:
        print(f'Reading {inputfile}...')
        for evidx, event in enumerate(Events(inputfile)):
            if 0 <= args.nentries <= evidx: break
            event.getByLabel('truthLogicalGraphProducer', handle)
            graph = handle.product()
            for particle in graph.signalParticles():
                p4 = particle.p4()
                pt, eta, e = p4.pt(), p4.eta(), p4.energy()
                # level members among the descendants (or the signal particle itself)
                in_level = (particle.data().levelFlags & levelbit) != 0
                energies = [p4.energy()] if in_level else []
                for descendant in particle.descendants():
                    if descendant.data().levelFlags & levelbit:
                        energies.append(descendant.p4().energy())
                energies = sorted(energies, reverse=True)
                rows.append({
                    'file': inputfile, 'event': evidx, 'particle': particle.id(), 'pdgid': particle.pdgId(),
                    'pt': pt, 'eta': eta, 'energy': e,
                    'multiplicity': len(energies),
                    'multiplicity_emin': int(np.sum(np.array(energies) >= args.min_energy)),
                    'leading_energy_fraction': energies[0] / e if len(energies) > 0 and e > 0 else 0.,
                    'reaches_calo_unchanged': in_level,
                })
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(args.outputdir, 'caloboundary_multiplicity.parquet'))
    print(f'Processed {len(df)} signal particles.')
    if len(df) == 0: sys.exit()

    # print summary
    mult = df['multiplicity'].values
    mult_emin = df['multiplicity_emin'].values
    print(f'Fraction of signal particles reaching the calorimeter unchanged: {np.mean(df["reaches_calo_unchanged"]):.3f}')
    print(f'Fraction of signal particles with multiplicity 1: {np.mean(mult == 1):.3f}'
          f' (can be larger than the above, e.g. for an interaction with a single outgoing particle)')
    print(f'Mean multiplicity: {np.mean(mult):.2f} (median {np.median(mult):.0f}, max {np.amax(mult)})')
    print(f'Mean multiplicity with E >= {args.min_energy} GeV: {np.mean(mult_emin):.2f}'
          f' (median {np.median(mult_emin):.0f}, max {np.amax(mult_emin)})')
    print(f'Mean energy fraction carried by the leading {args.level} particle: {np.mean(df["leading_energy_fraction"]):.3f}')

    # inclusive distributions
    abseta = np.abs(df['eta'].values)
    pt = df['pt'].values
    for key, values, label in [
            ('multiplicity', mult, f'Number of {args.level} particles per signal particle'),
            ('multiplicity_emin', mult_emin,
             f'Number of {args.level} particles (E ≥ {args.min_energy:g} GeV)\nper signal particle')]:
        maxval = max(int(np.amax(values)), 1)
        bins = np.arange(-0.5, maxval + 1.5, 1) if maxval <= 50 else np.unique(np.round(np.logspace(0, np.log10(maxval + 1), 40))) - 0.5
        fig, ax = plot_hist(values, bins, label, 'Number of signal particles', logy=True)
        if maxval > 50: ax.set_xscale('log')
        fig.savefig(os.path.join(args.outputdir, f'{key}.png'), dpi=150)
        plt.close(fig)
    fig, ax = plot_hist(df['leading_energy_fraction'].values, np.linspace(0, 1.05, 22),
                        f'Energy fraction of leading {args.level} particle', 'Number of signal particles', logy=True)
    fig.savefig(os.path.join(args.outputdir, 'leading_energy_fraction.png'), dpi=150)
    plt.close(fig)

    # trends as a function of pT and |eta|
    for xkey, xvals, bins, xlabel in [
            ('pt', pt, np.array(args.pt_bins), 'Signal particle $p_T$ [GeV]'),
            ('abseta', abseta, np.array(args.abseta_bins), 'Signal particle |η|')]:
        for ykey, yvals, mode, ylabel in [
                ('multiplicity', mult, 'mean', f'Mean number of {args.level}\nparticles per signal particle'),
                ('multiplicity_emin', mult_emin, 'mean',
                 f'Mean number of {args.level} particles\n(E ≥ {args.min_energy:g} GeV) per signal particle'),
                ('fraction_split', mult > 1, 'fraction', f'Fraction of signal particles\nwith > 1 {args.level} particle'),
                ('leading_energy_fraction', df['leading_energy_fraction'].values, 'mean',
                 f'Mean energy fraction of\nleading {args.level} particle')]:
            fig, ax = plot_trend(xvals, yvals, bins, xlabel, ylabel, mode=mode)
            if ykey == 'leading_energy_fraction': ax.set_ylim((0, 1.05))
            fig.savefig(os.path.join(args.outputdir, f'{ykey}_vs_{xkey}.png'), dpi=150)
            plt.close(fig)
    print(f'Plots written to {args.outputdir}.')
