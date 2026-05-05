# Run full reconstruction chain with TICL customization

### Introduction

To be kept closely in sync with sample production code.
The idea is the following:
- Sample production code runs the full sample production, including also the "central" HGCAL reconstruction.
The outputs are e.g. LayerClusters and Tracksters, typically with the "RECO" process name.
These should be complete and immediately usable, no extra reco step is needed.
- The re-reco code in this folder is only meant to optionally re-run only the reco step,
starting from samples produced earlier,
e.g. with varied parameters or adding extra output,
without the need to re-produce the full sample from scratch.

Note:
It does not seem possible to overwrite the objects with process name "RECO".
So instead the objects produced by this re-reco step are in a process named "HGCALTICL"
(can be modified in the cmsDriver command), and are added to the output
rather than overwriting previous reco objects.
This is similar to the approach in the selective HGCAL re-reco approach.


### Notes on usability
Original use case:
The selective HGCAL re-reco worked well enough so far,
but it seems very hard to add the LayerCluster-CaloParticle associators to the output in that way.
So try if it is easier by running the full (instead of selective) re-reco...

Status: runs correctly, both with and without associators.
But did not try to add TICL parameter modifications yet in this paradigm.

However, in the meantime, the associators are also running correctly in the HGCAL-specific re-reco.
So at the current time of writing, there is no reason to run the full re-reco,
and will switch back to HGCAL-specific re-reco (as it is much faster and disk-space-efficient).
This part of the code may not be maintained anymore (until it is needed again at a later stage...)


### Checks and validations:

- Does the re-reco (without modification) work starting from a sample produced with full output
(all collections stored to the "step2" output file)?
-> YES! Seems to run and produce the expected HGCALTICL collections for RecHits and LayerClusters.

- Does the output from the check above look the same as when using selective re-reco
(instead of full re-reco) on the same input file?
-> Seems to be the case from a quick check, but to be confirmed later in more detail if needed.

- Does the re-reco (without modification) work starting from a sample produced with reduced output
(only HGCAL-related collections stored to the "step2" output file)?
-> No, results in ProductNotFound error, probably some required inputs are not yet stored.
This is fine, as running the full re-reco is only really expected to work on samples produced with full output.
