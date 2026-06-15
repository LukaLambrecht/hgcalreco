# Plot TICL candidates


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


def make_outputdir(outputdir):
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)


def as_array(values):
    return np.array(values, dtype=float)


def relative_marker_sizes(energies, min_size=20., max_size=180.):
    energies = as_array(energies)
    if len(energies) == 0:
        return energies
    max_energy = np.amax(energies)
    if max_energy <= 0:
        return np.full(len(energies), min_size)
    return min_size + (max_size - min_size) * energies / max_energy


def axis_limits(values, margin_fraction=0.08, minimum_span=1.):
    values = as_array(values)
    if len(values) == 0:
        return (-minimum_span, minimum_span)
    vmin = np.amin(values)
    vmax = np.amax(values)
    if vmin == vmax:
        margin = minimum_span
    else:
        margin = (vmax - vmin) * margin_fraction
    return (vmin - margin, vmax + margin)


def symmetric_axis_limits(values, margin_fraction=0.08, minimum_span=1.):
    values = as_array(values)
    if len(values) == 0:
        return (-minimum_span, minimum_span)
    vmax = np.amax(np.abs(values))
    vmax = max(vmax * (1. + margin_fraction), minimum_span)
    return (-vmax, vmax)


def delta_phi(phi1, phi2):
    return np.arctan2(np.sin(phi1 - phi2), np.cos(phi1 - phi2))


def shift_phi_for_plot(*phi_arrays):
    phis = np.concatenate([as_array(phi_array) for phi_array in phi_arrays
                           if len(phi_array) > 0])
    if len(phis) < 2:
        return (*phi_arrays, False)

    naive_span = np.amax(phis) - np.amin(phis)
    phis_mod = np.sort(np.mod(phis, 2. * np.pi))
    gaps = np.diff(np.concatenate([phis_mod, [phis_mod[0] + 2. * np.pi]]))
    largest_gap_idx = np.argmax(gaps)
    circular_span = 2. * np.pi - gaps[largest_gap_idx]
    needs_shift = naive_span > np.pi and circular_span < naive_span

    if not needs_shift:
        return (*phi_arrays, False)

    low_edge = phis_mod[(largest_gap_idx + 1) % len(phis_mod)]
    center = low_edge + 0.5 * circular_span
    shifted_arrays = tuple(center + delta_phi(as_array(phi_array), center)
                           for phi_array in phi_arrays)
    return (*shifted_arrays, True)


def delta_r(eta1, phi1, eta2, phi2):
    return np.hypot(eta1 - eta2, delta_phi(phi1, phi2))


def get_from_ptr(ptr):
    if hasattr(ptr, 'isNull') and ptr.isNull():
        return None
    if hasattr(ptr, 'get'):
        return ptr.get()
    return ptr


def direction_at_z(eta, phi, z):
    theta = 2. * np.arctan(np.exp(-abs(eta)))
    tan_theta = np.tan(theta)
    radius = abs(z) * tan_theta
    return radius * np.cos(phi), radius * np.sin(phi), z


def caloparticle_direction_points(cp_etas, cp_phis, z_reference):
    xs, ys, zs = [], [], []
    if len(cp_etas) == 0 or z_reference == 0:
        return as_array(xs), as_array(ys), as_array(zs)
    for cp_eta, cp_phi in zip(cp_etas, cp_phis):
        z_sign = 1. if cp_eta >= 0. else -1.
        x, y, z = direction_at_z(cp_eta, cp_phi, z_sign * abs(z_reference))
        xs.append(x)
        ys.append(y)
        zs.append(z)
    return as_array(xs), as_array(ys), as_array(zs)


def overlay_caloparticles_etaphi(ax, cp_etas, cp_phis):
    if len(cp_etas) == 0:
        return
    ax.scatter(cp_etas, cp_phis, marker='*', s=220, c='black',
               edgecolors='white', linewidths=0.8, label='CaloParticles')
    ax.legend(loc='best')


def add_ticl_candidate_legend_entry(ax, color, label):
    ax.scatter([], [], marker='o', s=90, c=[color], alpha=0.8, label=label)
    ax.legend(loc='best')


def overlay_caloparticle_directions_xy(ax, cp_etas, cp_phis, z_reference):
    ax.scatter([0.], [0.], marker='x', s=90, c='black',
               linewidths=2.)
    if len(cp_etas) == 0 or z_reference == 0:
        return
    for cp_eta, cp_phi in zip(cp_etas, cp_phis):
        z = np.sign(cp_eta) * abs(z_reference)
        x, y, _ = direction_at_z(cp_eta, cp_phi, z)
        ax.plot([0., x], [0., y], color='black', linestyle='--',
                linewidth=1.3, alpha=0.85)


def overlay_caloparticle_directions_zy(ax, cp_etas, cp_phis, z_reference):
    ax.scatter([0.], [0.], marker='x', s=90, c='black',
               linewidths=2.)
    if len(cp_etas) == 0 or z_reference == 0:
        return
    for cp_eta, cp_phi in zip(cp_etas, cp_phis):
        z = np.sign(cp_eta) * abs(z_reference)
        _, y, _ = direction_at_z(cp_eta, cp_phi, z)
        ax.plot([0., z], [0., y], color='black', linestyle='--',
                linewidth=1.3, alpha=0.85)


def overlay_caloparticle_directions_3d(ax, cp_etas, cp_phis, z_reference):
    ax.scatter([0.], [0.], [0.], marker='x', s=90, c='black',
               linewidths=2.)
    dir_xs, dir_ys, dir_zs = caloparticle_direction_points(cp_etas, cp_phis,
                                                           z_reference)
    for x, y, z in zip(dir_xs, dir_ys, dir_zs):
        ax.plot([0., x], [0., y], [0., z],
                color='black', linestyle='--', linewidth=1.3, alpha=0.85)


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfiles', required=True, nargs='+')
    parser.add_argument('-o', '--outputdir', default='output_plots_ticlcandidates')
    parser.add_argument('-n', '--nentries', default=-1, type=int)
    parser.add_argument('--input_config', default=None, nargs='+')
    parser.add_argument('--input_config_type', default='centralreco', choices=['centralreco', 'customreco'])
    parser.add_argument('--do_caloparticles', default=False, action='store_true')
    parser.add_argument('--do_primary_caloparticles', default=False, action='store_true')
    parser.add_argument('--do_tracksters', default=False, action='store_true')
    parser.add_argument('--do_layerclusters', default=False, action='store_true')
    args = parser.parse_args()

    # set input configs
    input_configs = []
    if args.input_config is not None:
        # if input configs are specified on the command line, they take precedence
        input_configs = args.input_config[:]
    else:
        # else determine input configs automatically
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_baseline.json'))
        input_configs.append(os.path.join(topdir, f'configs/input_config_{args.input_config_type}_ticl.json'))
    print('Found following input configs:')
    print(json.dumps(input_configs, indent=2))

    # read events
    exclude = []
    if not args.do_tracksters: exclude.append('tracksters')
    if not args.do_layerclusters: exclude.append('layerclusters')
    events = Events(args.inputfiles)
    reader = Reader(input_configs, exclude=exclude)
    make_outputdir(args.outputdir)

    # initialize counter
    event_counter = 0

    # loop over events
    for event in events:
        event_counter += 1
        if args.nentries > 0 and event_counter > args.nentries: break
        print(f'Running on event {event_counter}...')

        # initialize plotting data
        xs, ys, zs, es, trs = [], [], [], [], []

        # get collections
        collections = reader.read_event(event)
        caloparticles = collections['caloparticles']
        layerclusters = []
        if args.do_layerclusters: layerclusters = collections['layerclusters']
        tracksters_clue = []
        if args.do_tracksters: tracksters_clue = collections['tracksters']
        tracksters_merged = collections['tracksters_merge']
        ticlcandidates = collections['ticlcandidates_merge']
        pfcands = collections['pfticl']

        # temp printouts for debugging
        print('CaloParticles: ', len(caloparticles))
        print('Tracksters (CLUE3D): ', len(tracksters_clue))
        print('Tracksters (merged): ', len(tracksters_merged))
        print('TICL Candidates: ', len(ticlcandidates))
        print('TICL PF cands: ', len(pfcands))

        # print number of tracksters per ticl candidate
        tr_per_tc = [len(tc.tracksters()) for tc in ticlcandidates]
        tot = sum(tr_per_tc)
        #print('Number of tracksters per ticl candidate: ', tr_per_tc, ' ', tot)    
        #print('---')

        # initializations
        tc_etas, tc_phis, tc_es, tc_raw_es, tc_ids, tc_best_cp_drs = [], [], [], [], [], []
        cp_etas, cp_phis, cp_es = [], [], []
        pcp_etas, pcp_phis, pcp_es = [], [], []
        tr_xs, tr_ys, tr_zs, tr_es, tr_tcs = [], [], [], [], []
        lc_xs, lc_ys, lc_zs, lc_es, lc_tcs = [], [], [], [], []

        # loop over CaloParticles
        for cp in caloparticles:
            # each CaloParticle essentially has a direction and an energy
            cp_etas.append(cp.eta())
            cp_phis.append(cp.phi())
            cp_es.append(cp.energy())
            # make separate collection for caloparticles from primary interaction
            if cp.eventId().event() == 0:
                pcp_etas.append(cp.eta())
                pcp_phis.append(cp.phi())
                pcp_es.append(cp.energy())

        # loop over TICL candidates
        for tc_idx, tc in enumerate(ticlcandidates):
            # each TICL candidate essentially has a direction and an energy;
            # note: no sensible position is stored for a TICL candidate,
            #       for that we need to go down to the associated tracksters or layerclusters.
            energy = tc.energy()
            raw_energy = tc.rawEnergy()
            eta = tc.eta()
            phi = tc.phi()
            tc_etas.append(eta)
            tc_phis.append(phi)
            tc_es.append(energy)
            tc_raw_es.append(raw_energy)
            tc_ids.append(tc_idx)

            # calculate dR to CaloParticles and take minimum
            if len(cp_etas) > 0:
                drs = [delta_r(eta, phi, cp_eta, cp_phi)
                       for cp_eta, cp_phi in zip(cp_etas, cp_phis)]
                tc_best_cp_drs.append(min(drs))
            else:
                tc_best_cp_drs.append(np.nan)

            # loop over tracksters associated with this candidate
            if not args.do_tracksters: continue
            for tr_ptr in tc.tracksters():
                tr = get_from_ptr(tr_ptr)
                if tr is None: continue
                pos = tr.barycenter()
                tr_xs.append(pos.x())
                tr_ys.append(pos.y())
                tr_zs.append(pos.z())
                tr_es.append(tr.raw_energy())
                tr_tcs.append(tc_idx)

                # loop over layerclusters associated with this trackster
                if not args.do_layerclusters: continue
                if layerclusters is None: continue
                for lc_idx in tr.vertices():
                    lc = layerclusters[lc_idx]
                    lc_pos = lc.position()
                    lc_xs.append(lc_pos.x())
                    lc_ys.append(lc_pos.y())
                    lc_zs.append(lc_pos.z())
                    lc_es.append(lc.energy())
                    lc_tcs.append(tc_idx)

        # make arrays
        tc_etas = as_array(tc_etas)
        tc_phis = as_array(tc_phis)
        tc_es = as_array(tc_es)
        tc_raw_es = as_array(tc_raw_es)
        tc_ids = np.array(tc_ids, dtype=int)
        tc_best_cp_drs = as_array(tc_best_cp_drs)
        cp_etas = as_array(cp_etas)
        cp_phis = as_array(cp_phis)
        cp_es = as_array(cp_es)
        pcp_etas = as_array(pcp_etas)
        pcp_phis = as_array(pcp_phis)
        pcp_es = as_array(pcp_es)
        tr_xs = as_array(tr_xs)
        tr_ys = as_array(tr_ys)
        tr_zs = as_array(tr_zs)
        tr_es = as_array(tr_es)
        tr_tcs = np.array(tr_tcs, dtype=int)
        lc_xs = as_array(lc_xs)
        lc_ys = as_array(lc_ys)
        lc_zs = as_array(lc_zs)
        lc_es = as_array(lc_es)
        lc_tcs = np.array(lc_tcs, dtype=int)
        if len(tc_etas) == 0: continue
        tc_phis_plot, cp_phis_plot, phi_shifted = shift_phi_for_plot(tc_phis, cp_phis)
        phi_label = "phi (shifted)" if phi_shifted else "phi"
        phi_limits = axis_limits(np.concatenate([tc_phis_plot, cp_phis_plot]), minimum_span=0.3)

        # TICL candidate direction: eta-phi, coloured by candidate energy.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(tc_etas, tc_phis_plot,
                    c=tc_es,
                    cmap='jet',
                    s=relative_marker_sizes(tc_es),
                    alpha=0.8)
        plt.colorbar(sc, label="TICL candidate energy")
        overlay_caloparticles_etaphi(ax, cp_etas, cp_phis_plot)
        add_ticl_candidate_legend_entry(ax, plt.get_cmap('jet')(0.75),
                                        'TICL candidates (coloured by energy)')
        ax.set_title('TICL candidate direction')
        ax.set_xlabel("eta")
        ax.set_ylabel(phi_label)
        ax.set_xlim(axis_limits(np.concatenate([tc_etas, cp_etas])))
        ax.set_ylim(phi_limits)
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_candidate_etaphi_energy.png'))
        plt.close()

        # TICL candidate direction: eta-phi, coloured by candidate index.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(tc_etas, tc_phis_plot,
                    c=tc_ids,
                    cmap='tab20',
                    s=relative_marker_sizes(tc_es),
                    alpha=0.8)
        plt.colorbar(sc, label="TICL candidate index")
        overlay_caloparticles_etaphi(ax, cp_etas, cp_phis_plot)
        add_ticl_candidate_legend_entry(ax, plt.get_cmap('tab20')(0),
                                        'TICL candidates (coloured by index)')
        ax.set_title('TICL candidate direction')
        ax.set_xlabel("eta")
        ax.set_ylabel(phi_label)
        ax.set_xlim(axis_limits(np.concatenate([tc_etas, cp_etas])))
        ax.set_ylim(phi_limits)
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_candidate_etaphi_index.png'))
        plt.close()

        # Candidate-to-nearest-CaloParticle angular distance.
        finite_drs = tc_best_cp_drs[np.isfinite(tc_best_cp_drs)]
        if len(finite_drs) > 0:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.scatter(finite_drs, tc_es[np.isfinite(tc_best_cp_drs)],
                       c='dodgerblue',
                       s=55,
                       alpha=0.8,
                       label='TICL candidate')
            ax.legend(loc='best')
            ax.set_title('TICL candidate dR to closest CaloParticle')
            ax.set_xlabel("min DeltaR(TICL candidate, CaloParticle)")
            ax.set_ylabel("TICL candidate energy")
            fig.tight_layout()
            fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_candidate_min_dr.png'))
            plt.close()

        # all further plots require tracksters, so skip if none are found
        if len(tr_xs) == 0: continue
        tr_maxxy = max(np.amax(np.abs(tr_xs)), np.amax(np.abs(tr_ys)))
        tr_z_reference = np.median(np.abs(tr_zs))
        tr_sizes = relative_marker_sizes(tr_es, min_size=25., max_size=160.)
        cp_dir_xs, cp_dir_ys, cp_dir_zs = caloparticle_direction_points(cp_etas, cp_phis,
                                                                        tr_z_reference)
        tr_xyz_for_limits = np.concatenate([tr_xs, tr_ys, [0.], cp_dir_xs, cp_dir_ys])
        tr_z_for_limits = np.concatenate([tr_zs, [0.], cp_dir_zs])

        # Trackster barycenters accessed through TICL candidates, coloured by candidate index.
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(tr_xs, tr_ys, tr_zs,
                    c=tr_tcs,
                    cmap='tab20',
                    s=tr_sizes,
                    alpha=0.85)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_3d(ax, cp_etas, cp_phis, tr_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_3d(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim(symmetric_axis_limits(tr_xyz_for_limits))
        ax.set_ylim(symmetric_axis_limits(tr_xyz_for_limits))
        ax.set_zlim(axis_limits(tr_z_for_limits))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trackster_barycenters_by_candidate.png'))
        plt.close()

        # Same Trackster barycenters in x-y projection, with CaloParticle directions.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(tr_xs, tr_ys,
                    c=tr_tcs,
                    cmap='tab20',
                    s=tr_sizes,
                    alpha=0.85)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_xy(ax, cp_etas, cp_phis, tr_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_xy(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-1.08 * tr_maxxy, 1.08 * tr_maxxy))
        ax.set_ylim((-1.08 * tr_maxxy, 1.08 * tr_maxxy))
        ax.set_aspect('equal', adjustable='box')
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trackster_barycenters_xy_by_candidate.png'))
        plt.close()

        # Same Trackster barycenters in z-y projection, with CaloParticle directions.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(tr_zs, tr_ys,
                    c=tr_tcs,
                    cmap='tab20',
                    s=tr_sizes,
                    alpha=0.85)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_zy(ax, cp_etas, cp_phis, tr_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_zy(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim(axis_limits(tr_zs))
        ax.set_ylim(symmetric_axis_limits(tr_ys))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_trackster_barycenters_zy_by_candidate.png'))
        plt.close()

        # all further plots require layerclusters, so skip if none are found
        if len(lc_xs) == 0: continue
        lc_maxxy = max(np.amax(np.abs(lc_xs)), np.amax(np.abs(lc_ys)))
        lc_z_reference = np.median(np.abs(lc_zs))
        lc_sizes = relative_marker_sizes(lc_es, min_size=8., max_size=70.)
        cp_dir_xs, cp_dir_ys, cp_dir_zs = caloparticle_direction_points(cp_etas, cp_phis,
                                                                        lc_z_reference)
        lc_xyz_for_limits = np.concatenate([lc_xs, lc_ys, [0.], cp_dir_xs, cp_dir_ys])
        lc_z_for_limits = np.concatenate([lc_zs, [0.], cp_dir_zs])

        # LayerCluster cloud accessed through TICL candidates.
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(lc_xs, lc_ys, lc_zs,
                    c=lc_tcs,
                    cmap='tab20',
                    s=lc_sizes,
                    alpha=0.65)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_3d(ax, cp_etas, cp_phis, lc_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_3d(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_zlabel("z [cm]")
        ax.set_xlim(symmetric_axis_limits(lc_xyz_for_limits))
        ax.set_ylim(symmetric_axis_limits(lc_xyz_for_limits))
        ax.set_zlim(axis_limits(lc_z_for_limits))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_layerclusters_by_candidate.png'))
        plt.close()

        # Same in x-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(lc_xs, lc_ys,
                    c=lc_tcs,
                    cmap='tab20',
                    s=lc_sizes,
                    alpha=0.65)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_xy(ax, cp_etas, cp_phis, lc_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_xy(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim((-1.08 * lc_maxxy, 1.08 * lc_maxxy))
        ax.set_ylim((-1.08 * lc_maxxy, 1.08 * lc_maxxy))
        ax.set_aspect('equal', adjustable='box')
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_layerclusters_xy_by_candidate.png'))
        plt.close()

        # Same in z-y projection
        fig = plt.figure()
        ax = fig.add_subplot(111)
        sc = ax.scatter(lc_zs, lc_ys,
                    c=lc_tcs,
                    cmap='tab20',
                    s=lc_sizes,
                    alpha=0.65)
        plt.colorbar(sc, label="TICL candidate index")
        if args.do_caloparticles: overlay_caloparticle_directions_zy(ax, cp_etas, cp_phis, lc_z_reference)
        elif args.do_primary_caloparticles: overlay_caloparticle_directions_zy(ax, pcp_etas, pcp_phis, tr_z_reference)
        ax.set_xlabel("z [cm]")
        ax.set_ylabel("y [cm]")
        ax.set_xlim(axis_limits(lc_zs))
        ax.set_ylim(symmetric_axis_limits(lc_ys))
        fig.tight_layout()
        fig.savefig(os.path.join(args.outputdir, f'test_{event_counter}_layerclusters_zy_by_candidate.png'))
        plt.close()
