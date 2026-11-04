# Tools for deriving LayerCluster / TICLCandidate - truth Branch association scores,
# with truth Branches of the MC-truth graph (see truth-graph-validation/status.md)
# as truth objects instead of CaloParticles or SimClusters.
#
# Inputs are the flattened reco-to-truth association maps with the "Fixed" working point
# (which list all candidate Branches that share energy with a reco object, with the shared energy),
# produced in the re-reco step, and the truth::Graph itself.
#
# Definitions (chosen to mirror the CaloParticle-based metrics in tcassociationtools.py and lcassociationtools.py,
# so that for a non-interacting particle gun the "signal" level reproduces the CaloParticle-based TICLCandidate metrics):
# - For a given truth level (e.g. "signal" or "caloBoundary"), the truth objects are completed
#   into a partition of all truth energy in the event: the members of the level, plus all
#   caloBoundary particles (of any interaction) that do not descend from a member of the level.
#   E.g. for the "signal" level of a particle gun sample with pileup, this is the gun particles
#   plus the caloBoundary particles of the pileup interactions.
#   This is the analogue of the full CaloParticle collection (including pileup),
#   so that reco objects can be matched to the truth object that explains them best,
#   before selecting only the level members from the signal interaction.
# - Purity-like matrix: entry [truth, reco] is the fraction of the reco object's shared energy
#   with all truth objects of the partition that is shared with this truth object.
#   For LayerClusters instead, as for CaloParticles, the purity is 1 - the (reco-normalized) association score.
# - Efficiency-like matrix: entry [truth, reco] is the fraction of the truth object's shared
#   energy with all reco objects that is shared with this reco object
#   (for LayerClusters, normalized per layer instead; note that this differs from the CaloParticle-based
#   LayerCluster efficiency, which is 1 - the per-layer sim-normalized score,
#   since the truth Branch association only provides a score normalized over the full Branch).
# Both matrices have shape (ntruth, nreco), as for the CaloParticle-based tools.


import math
import numpy as np


# level flag bits (see SimDataFormats/TruthInfo/interface/ParticleData.h)
LEVEL_BITS = {
    'stableLegsFromInitialState': 1 << 0,
    'hardProcess': 1 << 1,
    'stableDecayProducts': 1 << 2,
    'caloBoundary': 1 << 3,
    'signal': 1 << 4,
    'reconstructableFromSignal': 1 << 5,
}


class TruthParticle(object):
    '''
    Lightweight truth object for a truth Branch, identified by its root particle in the truth::Graph.
    Exposes the same kinematic accessors as CaloParticle / SimCluster as used in the efficiency code.
    '''

    def __init__(self, particle):
        p4 = particle.p4()
        self.id = int(particle.id())
        self._pt = p4.pt()
        self._eta = p4.eta() if p4.pt() > 0 else math.copysign(1e6, p4.pz())
        self._phi = p4.phi()
        self._energy = p4.energy()
        self._pdgid = int(particle.pdgId())
        self.is_signal = bool(particle.isSignal())

    def pt(self): return self._pt
    def eta(self): return self._eta
    def phi(self): return self._phi
    def energy(self): return self._energy
    def pdgId(self): return self._pdgid


def get_level_partition(graph, level):
    '''
    Get the truth objects for a given truth level, completed into a partition of all truth energy.
    Returns:
    - truth objects: list of TruthParticle (level members first, then the completion);
    - selected ids: indices (in the above list) of the level members from the signal interaction.
    '''
    levelbit = LEVEL_BITS[level]
    cbbit = LEVEL_BITS['caloBoundary']
    members = []
    calo_boundary = []
    for pid, data in enumerate(graph.particles()):
        flags = data.levelFlags
        if flags & levelbit: members.append(pid)
        if flags & cbbit: calo_boundary.append(pid)
    if level == 'caloBoundary':
        completion = []
    else:
        # caloBoundary particles that are not (descendants of) a member of the level
        covered = set(members)
        for pid in members:
            for descendant in graph.particle(pid).descendants():
                covered.add(int(descendant.id()))
        completion = [pid for pid in calo_boundary if pid not in covered]
    truth = [TruthParticle(graph.particle(pid)) for pid in members + completion]
    selected_ids = np.array([idx for idx in range(len(members)) if truth[idx].is_signal], dtype=int)
    return truth, selected_ids


def prune_truth(truth, selected_ids, *branch_id_arrays):
    '''
    Keep only the truth objects that are selected or that appear in at least one of the given
    flattened maps (i.e. that share energy with at least one reco object);
    the others do not affect the matching but can be very numerous (e.g. with pileup).
    Returns the pruned truth objects and the selected ids re-indexed accordingly.
    '''
    present = set()
    for branch_ids in branch_id_arrays: present.update(int(b) for b in branch_ids)
    selected = set(int(idx) for idx in selected_ids)
    keep = [idx for idx, t in enumerate(truth) if idx in selected or t.id in present]
    new_index = {old: new for new, old in enumerate(keep)}
    return [truth[idx] for idx in keep], np.array([new_index[int(idx)] for idx in selected_ids], dtype=int)


def get_shared_energy_matrix(reco_ids, branch_ids, shared_energies, truth, nreco):
    '''
    Build a (ntruth, nreco) matrix of shared energies from a flattened reco-to-truth Branch map.
    Entries for Branches that are not in the provided truth objects are ignored.
    '''
    index = {t.id: idx for idx, t in enumerate(truth)}
    shared = np.zeros((len(truth), nreco))
    for reco_idx, branch_idx, shared_energy in zip(reco_ids, branch_ids, shared_energies):
        truth_idx = index.get(int(branch_idx))
        if truth_idx is None: continue
        shared[truth_idx, int(reco_idx)] += shared_energy
    return shared


def get_purity_matrix_from_scores(reco_ids, branch_ids, scores, truth, nreco):
    '''
    Build a (ntruth, nreco) purity-like matrix (1 - score) from a flattened reco-to-truth Branch map,
    where the score is the reco-normalized association score (0 = Branch explains all of the reco object).
    Pairs without an entry (no shared energy) get a purity of 0.
    This mirrors the CaloParticle-based LayerCluster purity (see lcassociationtools.py).
    '''
    index = {t.id: idx for idx, t in enumerate(truth)}
    pur = np.zeros((len(truth), nreco))
    for reco_idx, branch_idx, score in zip(reco_ids, branch_ids, scores):
        truth_idx = index.get(int(branch_idx))
        if truth_idx is None: continue
        pur[truth_idx, int(reco_idx)] = 1 - score
    return pur


def get_matrices_from_shared_energy(shared, reco_groups=None):
    '''
    Get purity- and efficiency-like matrices from a (ntruth, nreco) shared energy matrix.
    If reco_groups is provided (array of length nreco, e.g. the layer of each LayerCluster),
    the efficiency is normalized per group instead of over all reco objects.
    '''
    reco_total = np.sum(shared, axis=0)
    pur_matrix = np.divide(shared, reco_total[np.newaxis, :],
        out=np.zeros_like(shared), where=reco_total[np.newaxis, :] > 0)
    if reco_groups is None:
        truth_total = np.sum(shared, axis=1)[:, np.newaxis]
    else:
        reco_groups = np.asarray(reco_groups)
        truth_total = np.zeros_like(shared)
        for group in np.unique(reco_groups):
            mask = (reco_groups == group)
            truth_total[:, mask] = np.sum(shared[:, mask], axis=1)[:, np.newaxis]
    eff_matrix = np.divide(shared, truth_total,
        out=np.zeros_like(shared), where=truth_total > 0)
    return pur_matrix, eff_matrix


def get_ticl_candidate_matrices(ticlcandidates, tc_ts_indices, ts_ids, branch_ids, shared_energies, truth):
    '''
    Build TICLCandidate - truth Branch matrices from the flattened Trackster-to-truth-Branch map
    (for the Trackster collection belonging to the TICLCandidates), summing over the
    constituent Tracksters of each TICLCandidate (as in tcassociationtools.py).
    Returns the purity- and efficiency-like matrices, both of shape (ntruth, ntc).
    '''
    nts = 0 if len(ts_ids) == 0 else int(np.max(ts_ids)) + 1
    nts = max([nts] + [max(indices) + 1 for indices in tc_ts_indices if len(indices) > 0])
    ts_shared = get_shared_energy_matrix(ts_ids, branch_ids, shared_energies, truth, nts)
    tc_shared = np.zeros((len(truth), len(ticlcandidates)))
    for tc_idx, indices in enumerate(tc_ts_indices):
        if len(indices) == 0: continue
        tc_shared[:, tc_idx] = np.sum(ts_shared[:, indices], axis=1)
    return get_matrices_from_shared_energy(tc_shared)
