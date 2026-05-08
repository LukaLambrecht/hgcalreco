# Test reading the LC - CP association maps in a full EDAnalyzer environment

### Conclusion
This seems to be the only working way to read the association maps.
All the inconsistencies seen in FWLite (both python and C++) seem to disappear.

### How to run this test
The module is automatically compiled as a plugin using `scram b`.
Run it with `cmsRun run_cfg.py` (in the `python` subfolder).
