# Tools for deriving TICLCandidate - CaloParticle association scores.

import numpy as np


def get_from_ptr(obj):
    '''
    Return the pointed-to object for EDM Ptr-like objects, or the object itself.
    '''
    if hasattr(obj, 'get'):
        return obj.get()
    return obj


def get_ptr_index(obj):
    '''
    Return the collection index for EDM Ptr-like objects.
    '''
    if hasattr(obj, 'key'):
        return int(obj.key())
    if hasattr(obj, 'index'):
        return int(obj.index())
    msg = 'Cannot retrieve collection index from object; expected an EDM Ptr-like object with key().'
    raise TypeError(msg)


def get_ticl_candidate_layercluster_indices(ticlcandidate):
    '''
    Return unique LayerCluster indices used by a TICLCandidate.

    The indices are obtained from the vertices of the Tracksters contained in the
    candidate. They are indices into the event-level LayerCluster collection used
    to build those Tracksters.
    '''
    lc_indices = set()

    for trackster_ptr in ticlcandidate.tracksters():
        trackster = get_from_ptr(trackster_ptr)
        if trackster is None:
            continue
        for lc_idx in trackster.vertices():
            lc_indices.add(int(lc_idx))

    return sorted(lc_indices)


def get_ticl_candidate_trackster_indices(ticlcandidate):
    '''
    Return unique Trackster indices used by a TICLCandidate.

    The TICLCandidate stores edm::Ptr<ticl::Trackster> objects. Their key() is
    the index into the Trackster collection used to build the candidate.
    '''
    ts_indices = set()

    for trackster_ptr in ticlcandidate.tracksters():
        ts_indices.add(get_ptr_index(trackster_ptr))

    return sorted(ts_indices)


def get_all_ticl_candidate_layercluster_indices(ticlcandidates):
    '''
    Return unique LayerCluster indices for each TICLCandidate in a collection.
    '''
    return [
        get_ticl_candidate_layercluster_indices(ticlcandidate)
        for ticlcandidate in ticlcandidates
    ]


def get_all_ticl_candidate_trackster_indices(ticlcandidates):
    '''
    Return unique Trackster indices for each TICLCandidate in a collection.
    '''
    return [
        get_ticl_candidate_trackster_indices(ticlcandidate)
        for ticlcandidate in ticlcandidates
    ]


def get_ticl_candidate_matrices_from_trackster_associations(
        ticlcandidates,
        tsids,
        simtsids,
        shared_energies,
        scores,
        ncp,
        tc_ts_indices=None):
    '''
    Build TICLCandidate - CaloParticle matrices from reco Trackster to
    SimTrackster-from-CaloParticle associations.

    Input arguments:
    - ticlcandidates: TICLCandidate collection.
    - tsids, simtsids, shared_energies, scores: flat arrays from
      flattenMergeTracksterToCPSimTrackster.
    - ncp: number of CaloParticles. The SimTrackster-from-CP collection is
      produced with indices corresponding to CaloParticle indices.
    - tc_ts_indices: optional precomputed output of
      get_all_ticl_candidate_trackster_indices.

    Returns:
    - tc_ts_indices: unique Trackster indices per TICLCandidate.
    - pur_matrix: TICLCandidate -> CaloParticle purity-like matrix. Entry
      [cp, tc] is the fraction of the candidate's Trackster shared energy that
      is shared with the CP SimTrackster.
    - eff_matrix: CaloParticle -> TICLCandidate efficiency-like matrix. Entry
      [cp, tc] is the fraction of the CP's total shared energy with reco
      Tracksters that is contained in the candidate's Tracksters.
    '''
    if tc_ts_indices is None:
        tc_ts_indices = get_all_ticl_candidate_trackster_indices(ticlcandidates)

    ntc = len(ticlcandidates)
    nts = 0 if len(tsids) == 0 else int(np.max(tsids)) + 1
    if len(tc_ts_indices) > 0:
        max_candidate_ts = max([max(indices) for indices in tc_ts_indices if len(indices) > 0], default=-1)
        nts = max(nts, max_candidate_ts + 1)

    ts_cp_shared = np.zeros((ncp, nts))
    for ts_idx, cp_idx, shared_energy in zip(tsids, simtsids, shared_energies):
        cp_idx = int(cp_idx)
        ts_idx = int(ts_idx)
        if cp_idx < 0 or cp_idx >= ncp:
            continue
        ts_cp_shared[cp_idx, ts_idx] += shared_energy

    tc_cp_shared = np.zeros((ncp, ntc))
    for tc_idx, indices in enumerate(tc_ts_indices):
        if len(indices) == 0:
            continue
        tc_cp_shared[:, tc_idx] = np.sum(ts_cp_shared[:, indices], axis=1)

    tc_total_shared = np.sum(tc_cp_shared, axis=0)
    pur_matrix = np.divide(
        tc_cp_shared,
        tc_total_shared[np.newaxis, :],
        out=np.zeros_like(tc_cp_shared),
        where=tc_total_shared[np.newaxis, :] > 0)

    cp_total_shared = np.sum(ts_cp_shared, axis=1)
    eff_matrix = np.divide(
        tc_cp_shared,
        cp_total_shared[:, np.newaxis],
        out=np.zeros_like(tc_cp_shared),
        where=cp_total_shared[:, np.newaxis] > 0)

    return tc_ts_indices, pur_matrix, eff_matrix


def get_tctocp_matrix(ticlcandidates, layerclusters, lctocp_matrix, tc_lc_indices=None):
    '''
    Build a TICLCandidate -> CaloParticle purity matrix.

    Input arguments:
    - ticlcandidates: TICLCandidate collection.
    - layerclusters: LayerCluster collection.
    - lctocp_matrix: matrix with shape (ncp, nlc), where larger values mean a
      better LC -> CP association. This is the convention returned by
      lcassociationtools.get_lctocp_matrix_from_builtin(..., invert=True).
    - tc_lc_indices: optional precomputed output of
      get_all_ticl_candidate_layercluster_indices.

    Returns:
    - A 2D numpy array with shape (ncp, ntc). Entry [cp, tc] is the
      energy-weighted average LC -> CP score for the unique LayerClusters in the
      TICLCandidate. This is a TICLCandidate purity-like score.
    '''
    if tc_lc_indices is None:
        tc_lc_indices = get_all_ticl_candidate_layercluster_indices(ticlcandidates)

    ncp = lctocp_matrix.shape[0]
    ntc = len(ticlcandidates)
    res = np.zeros((ncp, ntc))

    for tc_idx, lc_indices in enumerate(tc_lc_indices):
        if len(lc_indices) == 0:
            continue

        weights = np.array([layerclusters[lc_idx].energy() for lc_idx in lc_indices])
        denom = np.sum(weights)
        if denom <= 0:
            continue

        res[:, tc_idx] = np.sum(lctocp_matrix[:, lc_indices] * weights, axis=1) / denom

    return res


def get_cptotc_matrix(ticlcandidates, cptolc_matrix, tc_lc_indices=None, clip=True):
    '''
    Build a CaloParticle -> TICLCandidate efficiency matrix.

    Input arguments:
    - ticlcandidates: TICLCandidate collection.
    - cptolc_matrix: matrix with shape (ncp, nlc), where larger values mean a
      better CP -> LC association. For the built-in flattened maps this should
      preferably be made from the SharedEnergyFraction branch.
    - tc_lc_indices: optional precomputed output of
      get_all_ticl_candidate_layercluster_indices.
    - clip: if True, clip the summed efficiency to [0, 1].

    Returns:
    - A 2D numpy array with shape (ncp, ntc). Entry [cp, tc] is the sum of the
      CP -> LC fractions captured by the unique LayerClusters in the
      TICLCandidate. This is a CaloParticle efficiency-like score.
    '''
    if tc_lc_indices is None:
        tc_lc_indices = get_all_ticl_candidate_layercluster_indices(ticlcandidates)

    ncp = cptolc_matrix.shape[0]
    ntc = len(ticlcandidates)
    res = np.zeros((ncp, ntc))

    for tc_idx, lc_indices in enumerate(tc_lc_indices):
        if len(lc_indices) == 0:
            continue
        res[:, tc_idx] = np.sum(cptolc_matrix[:, lc_indices], axis=1)

    if clip:
        res = np.clip(res, 0, 1)

    return res


def get_ticl_candidate_matrices(
        ticlcandidates,
        layerclusters,
        lctocp_matrix,
        cptolc_matrix,
        clip_efficiency=True):
    '''
    Convenience wrapper returning both TICLCandidate - CaloParticle matrices.

    Returns:
    - tc_lc_indices: unique LayerCluster indices per TICLCandidate.
    - pur_matrix: TICLCandidate -> CaloParticle purity-like matrix.
    - eff_matrix: CaloParticle -> TICLCandidate efficiency-like matrix.
    '''
    tc_lc_indices = get_all_ticl_candidate_layercluster_indices(ticlcandidates)
    pur_matrix = get_tctocp_matrix(
        ticlcandidates,
        layerclusters,
        lctocp_matrix,
        tc_lc_indices=tc_lc_indices)
    eff_matrix = get_cptotc_matrix(
        ticlcandidates,
        cptolc_matrix,
        tc_lc_indices=tc_lc_indices,
        clip=clip_efficiency)

    return tc_lc_indices, pur_matrix, eff_matrix


def get_ticl_candidate_matrices_from_builtin(
        ticlcandidates,
        layerclusters,
        lctocp_lcids,
        lctocp_cpids,
        lctocp_scores,
        cptolc_cpids,
        cptolc_lcids,
        cptolc_scores,
        ncp,
        lctocp_invert=True,
        cptolc_invert=False,
        clip_efficiency=True):
    '''
    Build TICLCandidate - CaloParticle matrices directly from flattened LC-CP
    association products.

    For cptolc_scores, prefer the CP -> LC SharedEnergyFraction branch if it is
    available. That makes the CP -> TICLCandidate matrix an additive efficiency
    proxy over the candidate's unique LayerClusters. The default
    cptolc_invert=False assumes that branch is used.
    '''
    try:
        from tools.lcassociationtools import get_cptolc_matrix_from_builtin
        from tools.lcassociationtools import get_lctocp_matrix_from_builtin
    except ImportError:
        from .lcassociationtools import get_cptolc_matrix_from_builtin
        from .lcassociationtools import get_lctocp_matrix_from_builtin

    nlc = len(layerclusters)

    lctocp_matrix = get_lctocp_matrix_from_builtin(
        lctocp_lcids,
        lctocp_cpids,
        lctocp_scores,
        nlc,
        ncp,
        invert=lctocp_invert)

    cptolc_matrix = get_cptolc_matrix_from_builtin(
        cptolc_cpids,
        cptolc_lcids,
        cptolc_scores,
        ncp,
        nlc,
        invert=cptolc_invert)

    return get_ticl_candidate_matrices(
        ticlcandidates,
        layerclusters,
        lctocp_matrix,
        cptolc_matrix,
        clip_efficiency=clip_efficiency)


def get_mapping(association_matrix, threshold=None, exclude_empty=False, candidate_constituents=None):
    '''
    Calculate a unique mapping between CaloParticles and TICLCandidates.

    The association matrix is expected to have shape (ncp, ntc). Returns:
    - tc_ids: list of length ncp, each element containing TICLCandidate indices
      mapped to that CaloParticle.
    - cp_ids: array of length ntc containing the mapped CaloParticle index for
      each TICLCandidate, or -1 if no score passes threshold.

    Optional arguments:
    - exclude_empty: if True, mark candidates with no constituents as unmatched
      independently of the association score threshold.
    - candidate_constituents: list of constituent-index lists, one per
      TICLCandidate. Required when exclude_empty is True.
    '''
    ncp, ntc = association_matrix.shape
    cp_ids = np.argmax(association_matrix, axis=0).astype(int)

    if threshold is not None:
        scores = association_matrix[cp_ids, range(ntc)]
        mask = (scores < threshold).astype(bool)
        cp_ids[mask] = -1

    if exclude_empty:
        if candidate_constituents is None:
            msg = 'candidate_constituents must be provided when exclude_empty=True.'
            raise ValueError(msg)
        if len(candidate_constituents) != ntc:
            msg = f'Expected {ntc} candidate constituent lists, got {len(candidate_constituents)}.'
            raise ValueError(msg)
        empty_mask = np.array([len(indices) == 0 for indices in candidate_constituents], dtype=bool)
        cp_ids[empty_mask] = -1

    tc_ids = []
    for cp_idx in range(ncp):
        tc_ids.append(np.nonzero(cp_ids == cp_idx)[0])

    return tc_ids, cp_ids
