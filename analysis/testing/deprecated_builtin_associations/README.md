# Deprecated testing scripts for builtin association maps

Conclusion: reading the association maps directly does not work in FWLite,
gives segmentation violations, nonsensical values, and wrong mappings.

Instead need to flatten the maps after production and use the flat maps as input.
