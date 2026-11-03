# Local patches to CMSSW

Small modifications to central CMSSW packages that are not (yet) available upstream.
They are applied with `git apply` by `cmssw_setup.sh` in the top directory,
after checking out the corresponding packages with `git cms-addpkg`.

- `skip_zero_simtoreco_denominator.patch`: in `AllTracksterToSimTracksterAssociatorsByLCsProducer`,
skip a SimTrackster with zero sim-to-reco score denominator instead of asserting.
This happens in degenerate reconstruction configurations during parameter scans
(e.g. extreme CLUE distance parameters leading to near-total merging).
