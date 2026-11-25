# Surface density of particles entering HGCAL

Rough, gen-level estimate of the number of particles per cm² per event crossing each HGCAL layer,
as a function of the distance from the beam line (assuming phi symmetry).
Uses only the MC-truth graph (`truth::Graph`) of the production files; no reconstruction is needed.

## Method

- Particles: the `caloBoundary` particles of the truth graph, of all interactions (signal and pileup),
  with their position and momentum where they cross the calorimeter boundary (trajectory checkpoint 0).
- Only particles crossing the boundary at the HGCAL front face (|z| = 293.5 cm, for r up to ~123 cm),
  or at the inner boundary cylinder (r ≈ 7.5 cm) before the first layer, and moving away from the
  interaction point are kept. Particles crossing into the barrel or beyond HGCAL are not counted.
- Each particle is extrapolated in a straight line to the z position of each layer (`LAYER_Z` in
  `surfacedensitytools.py`, from reconstructed LayerClusters in the D127 geometry).
  Showering and the magnetic field are ignored, so the numbers describe the incoming particles only,
  and low-pT charged particles that would curl in the field are spread out too much.
- Only particles crossing a layer within its active radial range are counted: from the inner edge of the silicon
  to the outer edge of the silicon or scintillator, from the HGCAL geometry parameters (`rMinLayHex`, `rMaxLayHex`
  of HGCalParameters for the D127 geometry, dumped with `dump_layer_radii_cfg.py` and hard-coded in
  `surfacedensitytools.py`). The active area is approximated by a full ring (its real edges follow the wafers and tiles).
- Density = number of particles in a ring / (2 × active area of the ring), averaged over both endcaps and over events;
  the uncertainty is std / sqrt(number of events).
  Separately for all, charged and neutral particles.

## Scripts

Two steps, so that the plots can be iterated on quickly:

- `extract_boundary_particles.py` (slow, run once): reads the truth graph and stores the boundary position, momentum
  and PDG id of the caloBoundary particles crossing the boundary at |z| >= 250 cm
  (`-i <files>`, default file_0 of the PU200 single-pion sample; `-n <events>`;
  `-o <npz file>`, default on EOS in `hgcalreco-data/surface-density/`).
  About 1 s per PU200 event: the truth graph is stored as one unsplit object (~12 MB per event compressed),
  which has to be read in full; only that branch is read.
- `plot_surface_density.py` (seconds): selection, extrapolation and binning (`--rbin`, `--rmax`, `--zmin_boundary`,
  `--min_momentum`), and the plots, in `output/` by default: per-layer plots of the density (x-axis) vs the distance
  from the beam line (y-axis) (`layers/density_layer<i>.png`, only with `--per_layer`), all layers overlaid
  (`density_all_layers.png`, rainbow colours from layer 1 in blue to the last layer in red), a layer vs radius map
  (`density_map.png`), and a table (`density.csv`).
- `surfacedensitytools.py`: common definitions (layer positions and active ranges, particle categories, loading,
  extrapolation and counting).
- `dump_layer_radii_cfg.py`: cmsRun config to dump the layer parameters from the geometry (see above).
