# Tools for deriving TICLCandidate - CaloParticle association scores.
#
# The active implementation derives TICLCandidate associations from reco
# Trackster -> CP-SimTrackster shared-energy associations. This is preferable
# to rebuilding TICLCandidate scores from LC-CP associations because LC-CP
# efficiency scores are normalized layer-by-layer and are therefore awkward to
# combine over multi-layer objects.

import numpy as np


def get_ptr_index(obj):
    '''
    Return the collection index for EDM Ptr-like objects.

    TICLCandidate.tracksters() stores edm::Ptr<ticl::Trackster> objects. The
    key of such a pointer is the index of that Trackster inside the event-level
    Trackster collection used to build the TICLCandidate.
    '''
    if hasattr(obj, 'key'):
        return int(obj.key())
    if hasattr(obj, 'index'):
        return int(obj.index())
    msg = 'Cannot retrieve collection index from object; expected an EDM Ptr-like object with key().'
    raise TypeError(msg)


def get_ticl_candidate_trackster_indices(ticlcandidate):
    '''
    Return unique Trackster indices used by a TICLCandidate.

    The same Trackster is not expected to appear twice in one TICLCandidate, but
    the set makes the downstream summing robust against accidental duplicates.
    '''
    ts_indices = set()

    for trackster_ptr in ticlcandidate.tracksters():
        ts_indices.add(get_ptr_index(trackster_ptr))

    return sorted(ts_indices)


def get_all_ticl_candidate_trackster_indices(ticlcandidates):
    '''
    Return unique Trackster indices for each TICLCandidate in a collection.

    The returned list has length ntc. Element i contains the Trackster indices
    belonging to TICLCandidate i, and can be reused by get_mapping(...,
    exclude_empty=True) to distinguish empty candidates from non-empty
    candidates with genuinely zero truth overlap.
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
        ncp,
        tc_ts_indices=None,
        simts_to_cp_indices=None):
    '''
    Build TICLCandidate - CaloParticle matrices from reco Trackster to
    SimTrackster-from-CaloParticle associations.

    Input arguments:
    - ticlcandidates: TICLCandidate collection.
    - tsids, simtsids, shared_energies: flat arrays from the Trackster to
      CP-SimTrackster association product matching the TICLCandidate Trackster
      collection. Each row says how much shared energy a reco Trackster has
      with one CP SimTrackster.
    - ncp: number of CaloParticles.
    - tc_ts_indices: optional precomputed output of
      get_all_ticl_candidate_trackster_indices.
    - simts_to_cp_indices: optional map from SimTrackster-from-CP collection
      index to the original CaloParticle index. This is needed when the stored
      SimTrackster-from-CP collection is compressed by dropping CaloParticles
      without reconstructed content, as happens in CMSSW 17 pileup samples.

    Returns:
    - tc_ts_indices: unique Trackster indices per TICLCandidate.
    - pur_matrix: TICLCandidate -> CaloParticle purity-like matrix. Entry
      [cp, tc] is the fraction of the candidate's Trackster shared energy that
      is shared with the CP SimTrackster.
    - eff_matrix: CaloParticle -> TICLCandidate efficiency-like matrix. Entry
      [cp, tc] is the fraction of the CP's total shared energy with reco
      Tracksters that is contained in the candidate's Tracksters.

    Matrix convention:
    Both output matrices have shape (ncp, ntc). This matches the LC association
    tools and makes the purity-based matching step simply an argmax over CPs for
    each TICLCandidate column.
    '''
    # Step 1: find which reco Tracksters belong to each TICLCandidate.
    if tc_ts_indices is None:
        tc_ts_indices = get_all_ticl_candidate_trackster_indices(ticlcandidates)

    # Step 2: size the event-level reco Trackster axis. It must cover both the
    # indices present in the flat association products and the indices pointed to
    # by TICLCandidates. The latter matters for non-associated Tracksters, which
    # are absent from the flat products but still need to produce zero scores.
    ntc = len(ticlcandidates)
    nts = 0 if len(tsids) == 0 else int(np.max(tsids)) + 1
    if len(tc_ts_indices) > 0:
        max_candidate_ts = max([max(indices) for indices in tc_ts_indices if len(indices) > 0], default=-1)
        nts = max(nts, max_candidate_ts + 1)

    # Step 3: build a CP x Trackster shared-energy matrix from the flattened
    # association products. If a reco Trackster has no entry here, its whole
    # column stays zero, meaning it has no truth overlap with any CP SimTrackster.
    if simts_to_cp_indices is not None:
        simts_to_cp_indices = np.array(simts_to_cp_indices, dtype=int)

    ts_cp_shared = np.zeros((ncp, nts))
    for ts_idx, cp_idx, shared_energy in zip(tsids, simtsids, shared_energies):
        ts_idx = int(ts_idx)
        cp_idx = int(cp_idx)
        if simts_to_cp_indices is not None:
            if cp_idx < 0 or cp_idx >= len(simts_to_cp_indices):
                continue
            cp_idx = int(simts_to_cp_indices[cp_idx])
        if cp_idx < 0 or cp_idx >= ncp:
            continue
        ts_cp_shared[cp_idx, ts_idx] += shared_energy

    # Step 4: sum Trackster shared energies into TICLCandidate shared energies.
    # Each TICLCandidate column is the sum of the columns of its constituent
    # Tracksters.
    tc_cp_shared = np.zeros((ncp, ntc))
    for tc_idx, indices in enumerate(tc_ts_indices):
        if len(indices) == 0:
            continue
        tc_cp_shared[:, tc_idx] = np.sum(ts_cp_shared[:, indices], axis=1)

    # Step 5: purity-like score. For a TICLCandidate, ask which CP explains the
    # candidate's associated shared energy. Candidates with no shared energy with
    # any CP remain exactly zero for all CPs.
    tc_total_shared = np.sum(tc_cp_shared, axis=0)
    pur_matrix = np.divide(
        tc_cp_shared,
        tc_total_shared[np.newaxis, :],
        out=np.zeros_like(tc_cp_shared),
        where=tc_total_shared[np.newaxis, :] > 0)

    # Step 6: efficiency-like score. For a CP, ask what fraction of its total
    # shared energy with reco Tracksters is contained in this TICLCandidate.
    # The denominator is built over all associated reco Tracksters in the event,
    # not layer-by-layer, so this score can be interpreted for multi-layer
    # Tracksters/TICLCandidates.
    cp_total_shared = np.sum(ts_cp_shared, axis=1)
    eff_matrix = np.divide(
        tc_cp_shared,
        cp_total_shared[:, np.newaxis],
        out=np.zeros_like(tc_cp_shared),
        where=cp_total_shared[:, np.newaxis] > 0)

    return tc_ts_indices, pur_matrix, eff_matrix


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
    # Pick the CP with the highest purity-like score for each TICLCandidate.
    # With threshold=None, all-zero columns still map to CP index 0 by argmax;
    # those candidates keep a purity of zero and should be interpreted as having
    # no truth overlap, not as physically matched to CP 0.
    ncp, ntc = association_matrix.shape
    cp_ids = np.argmax(association_matrix, axis=0).astype(int)

    # Optional score threshold. This is intentionally separate from
    # exclude_empty: a non-empty candidate with zero truth overlap can be kept in
    # the output by using threshold=None, while truly empty candidates can still
    # be removed below.
    if threshold is not None:
        scores = association_matrix[cp_ids, range(ntc)]
        mask = (scores < threshold).astype(bool)
        cp_ids[mask] = -1

    # Optional structural filter. Empty TICLCandidates have no Tracksters, so
    # they do not carry association information. Mark them as unmatched without
    # changing how non-empty zero-overlap candidates are treated.
    if exclude_empty:
        if candidate_constituents is None:
            msg = 'candidate_constituents must be provided when exclude_empty=True.'
            raise ValueError(msg)
        if len(candidate_constituents) != ntc:
            msg = f'Expected {ntc} candidate constituent lists, got {len(candidate_constituents)}.'
            raise ValueError(msg)
        empty_mask = np.array([len(indices) == 0 for indices in candidate_constituents], dtype=bool)
        cp_ids[empty_mask] = -1

    # Build the reverse view: for each CP, list all TICLCandidates whose best
    # purity match points to that CP.
    tc_ids = []
    for cp_idx in range(ncp):
        tc_ids.append(np.nonzero(cp_ids == cp_idx)[0])

    return tc_ids, cp_ids
