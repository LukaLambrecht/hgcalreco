# Test reading LC - CP association maps with (C++) FWLite

### Conclusion
The association maps seem completely unreliable in FWLite,
regardless of whether it is in python or C++.
Some example issues:
- Segmentation violations (though not seen in C++, only in python).
- Nonsensical values (e.g. eta > 100).
- Internal inconsistencies between linked CPs and LCs.
- Indexing inconsistencies between CPs and LCs separtely.
- Matching inconsistencies between CPs and LCs using indices.

Only use the association map in a "full-framework" environment, not FWLite.

### How to run this test
The script `bin/testHGCalAssociations.cc` should be compiled as a standalone binary
when compiling the CMSSW environment with `scram b`.
Then it can be run with `testHGCalAssociations <input file>`.
