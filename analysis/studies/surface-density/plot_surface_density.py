# Plot the surface density (particles per cm^2 per event) of the caloBoundary particles at each HGCAL layer,
# from the boundary kinematics stored by extract_boundary_particles.py (runs in seconds).
#
# Each selected particle is extrapolated in a straight line from its boundary position along its boundary momentum
# to the z position of each layer (no showering, no magnetic field), see surfacedensitytools.py::get_layer_counts.
# Only particles crossing a layer within its active radial range are counted (see surfacedensitytools.py).
# Density = count in a ring / (2 * active area of the ring) (both endcaps averaged, phi symmetry), averaged over events.
#
# Output (in the output directory):
# - layers/density_layer<i>.png (only with --per_layer): per layer, the density (x-axis, particles per cm^2 per event)
#   vs the distance from the beam line (y-axis), for all, charged and neutral particles,
#   with the statistical uncertainty (std / sqrt(number of events)) as a band;
# - density_all_layers.png: the density of all particles for all layers overlaid
#   (rainbow colours from layer 1 in blue to the last layer in red);
# - density_map.png: the density of all particles vs layer and distance from the beam line;
# - density.csv: the density per layer and radial bin (all, charged, neutral, with uncertainties).
#
# Example: python3 plot_surface_density.py -i <output of extract_boundary_particles.py> -o <output dir>


import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir)

from surfacedensitytools import CATEGORIES, CATEGORY_LABELS, N_EE_LAYERS, LAYERS, LAYER_Z, layer_label, active_ring_areas
from surfacedensitytools import load_particles, get_layer_counts, LAYER_RMIN, LAYER_RMAX

DEFAULT_INPUT = '/eos/home-l/llambrec/hgcalreco-data/surface-density/boundary_particles_SinglePion_201X_D127_PU200_file_0.npz'

COLORS = {'all': 'black', 'charged': '#1f77b4', 'neutral': '#ff7f0e'}


def get_density(counts, r_edges):
    '''
    Mean density per event (per endcap) and its uncertainty (std / sqrt(number of events)), arrays of shape (layers, radial bins),
    from counts of shape (events, layers, radial bins), summed over both endcaps.
    '''
    areas = active_ring_areas(r_edges)
    with np.errstate(divide='ignore', invalid='ignore'):
        per_event = np.where(areas[None] > 0, counts / (2 * areas[None]), np.nan)
    return per_event.mean(axis=0), per_event.std(axis=0) / np.sqrt(len(per_event))


def style_density_axes(ax, xlim=None, rmax=None):
    ax.set_xscale('log')
    if xlim is not None: ax.set_xlim(*xlim)
    if rmax is not None: ax.set_ylim(0, rmax)
    ax.set_xlabel('Particles per cm$^2$ per event', fontsize=14)
    ax.set_ylabel('Distance from the beam line (cm)', fontsize=14)
    ax.tick_params(axis='both', labelsize=12)
    ax.grid(color='#e6e6e6', linewidth=0.8, which='major')
    ax.set_axisbelow(True)


def plot_layer(r_centers, densities, lidx, layer, outputfile, xlim, rmax, nevents):
    fig, ax = plt.subplots(figsize=(6.5, 6))
    for cat in CATEGORIES:
        mean, err = densities[cat][0][lidx], densities[cat][1][lidx]
        valid = mean > 0
        ax.fill_betweenx(r_centers[valid], np.clip(mean - err, 1e-12, None)[valid], (mean + err)[valid],
            color=COLORS[cat], alpha=0.25, linewidth=0)
        ax.plot(np.where(valid, mean, np.nan), r_centers, color=COLORS[cat], linewidth=1.5, label=CATEGORY_LABELS[cat])
    for r in (LAYER_RMIN[layer], LAYER_RMAX[layer]):
        ax.axhline(r, color='grey', linestyle=':', linewidth=1.2)
    ax.plot([], [], color='grey', linestyle=':', linewidth=1.2, label='Active range')
    style_density_axes(ax, xlim=xlim, rmax=rmax)
    ax.set_title(layer_label(layer), fontsize=13)
    ax.legend(fontsize=12, loc='upper right', title=f'{nevents} events', title_fontsize=11)
    fig.tight_layout()
    fig.savefig(outputfile)
    plt.close(fig)


def plot_all_layers(r_centers, density, layers, outputfile, xlim, rmax, nevents):
    fig, ax = plt.subplots(figsize=(7.5, 6))
    # rainbow colours from layer 1 (blue) to the last layer (red)
    cmap = plt.get_cmap('rainbow')
    norm = plt.Normalize(layers[0], layers[-1])
    for lidx, layer in enumerate(layers):
        mean = density[lidx]
        ax.plot(np.where(mean > 0, mean, np.nan), r_centers, color=cmap(norm(layer)), linewidth=1)
    style_density_axes(ax, xlim=xlim, rmax=rmax)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label('Layer', fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    fig.tight_layout()
    fig.savefig(outputfile)
    plt.close(fig)


def plot_map(r_edges, density, layers, outputfile, rmax, nevents):
    fig, ax = plt.subplots(figsize=(9, 6))
    layer_edges = np.arange(layers[0] - 0.5, layers[-1] + 1)
    values = np.where(density > 0, density, np.nan).T
    mesh = ax.pcolormesh(layer_edges, r_edges, values, norm=LogNorm(vmin=np.nanmin(values), vmax=np.nanmax(values)),
        cmap='viridis', shading='flat')
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label('Particles per cm$^2$ per event', fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    ax.axvline(N_EE_LAYERS + 0.5, color='white', linestyle='--', linewidth=1)
    ax.text(N_EE_LAYERS / 2 + 0.5, rmax * 0.95, 'CE-E', color='white', ha='center', va='top', fontsize=13)
    ax.text((N_EE_LAYERS + layers[-1]) / 2 + 0.5, rmax * 0.95, 'CE-H', color='white', ha='center', va='top', fontsize=13)
    ax.set_ylim(0, rmax)
    ax.set_xlabel('Layer', fontsize=14)
    ax.set_ylabel('Distance from the beam line (cm)', fontsize=14)
    ax.tick_params(axis='both', labelsize=12)
    fig.tight_layout()
    fig.savefig(outputfile)
    plt.close(fig)


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Plot the surface density of the caloBoundary particles at each HGCAL layer')
    parser.add_argument('-i', '--inputfile', default=DEFAULT_INPUT, help='Output of extract_boundary_particles.py')
    parser.add_argument('-o', '--outputdir', default=os.path.join(thisdir, 'output'))
    parser.add_argument('--rmax', default=300., type=float, help='Maximum radius in cm (default: 300)')
    parser.add_argument('--rbin', default=2.5, type=float, help='Width of the radial bins in cm (default: 2.5)')
    parser.add_argument('--zmin_boundary', default=290., type=float,
        help='Minimum |z| (cm) of the boundary crossing to consider it at the HGCAL front face (default: 290)')
    parser.add_argument('--per_layer', default=False, action='store_true', help='Also make the plots per layer (slower)')
    parser.add_argument('--min_momentum', default=0., type=float, help='Minimum momentum (GeV) of the particles (default: 0)')
    args = parser.parse_args()
    outputdir = args.outputdir
    rmax = args.rmax

    particles, nevents = load_particles(args.inputfile)
    r_edges = np.arange(0., args.rmax + args.rbin / 2, args.rbin)
    r_centers = (r_edges[1:] + r_edges[:-1]) / 2
    layers = LAYERS
    counts, nselected = get_layer_counts(particles, nevents, r_edges,
        zmin_boundary=args.zmin_boundary, min_momentum=args.min_momentum)
    print(f'{nevents} events, {nselected.mean():.0f} selected particles per event (both endcaps).')
    densities = {cat: get_density(counts[cat], r_edges) for cat in CATEGORIES}

    # common x-axis range for all layers (positive densities only)
    positive = np.concatenate([d[0][d[0] > 0] for d in densities.values()])
    xlim = (positive.min() / 2, positive.max() * 2)

    os.makedirs(outputdir, exist_ok=True)
    if args.per_layer:
        os.makedirs(os.path.join(outputdir, 'layers'), exist_ok=True)
        for lidx, layer in enumerate(layers):
            plot_layer(r_centers, densities, lidx, layer,
                os.path.join(outputdir, 'layers', f'density_layer{layer}.png'), xlim, rmax, nevents)
        print(f'Created {len(layers)} figures in {os.path.join(outputdir, "layers")}')
    plot_all_layers(r_centers, densities['all'][0], layers, os.path.join(outputdir, 'density_all_layers.png'), xlim, rmax, nevents)
    plot_map(r_edges, densities['all'][0], layers, os.path.join(outputdir, 'density_map.png'), rmax, nevents)

    # table
    rows = ['layer,z,r_low,r_high,' + ','.join(f'density_{cat},density_{cat}_err' for cat in CATEGORIES)]
    for lidx, layer in enumerate(layers):
        for ridx in range(len(r_centers)):
            values = ','.join(f'{densities[cat][0][lidx, ridx]:.6g},{densities[cat][1][lidx, ridx]:.3g}' for cat in CATEGORIES)
            rows.append(f'{layer},{LAYER_Z[layer]:.3f},{r_edges[ridx]:g},{r_edges[ridx + 1]:g},{values}')
    with open(os.path.join(outputdir, 'density.csv'), 'w') as f: f.write('\n'.join(rows) + '\n')
    print(f'Created density_all_layers.png, density_map.png and density.csv in {outputdir}')
