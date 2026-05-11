# Custom CMSSW packages

This folder contains custom CMSSW packages.
They are kept outside of a specific CMSSW release directory,
but are copied via symbolic linking to the `CMSSW_X_Y_Z/src` directory,
so they are compiled and usable as if they would be located there.

See `make_symlinks.py` for creating the symbolic links.
This needs to be done only once (or every time a new CMSSW version is used or a new package is added).


### How to use

- Write or modify CMSSW packages in this folder (see existing examples for formatting rules/conventions).
- Remake the symbolic links with `make_symlinks.py` (not needed except a new package was added).
- Recompile CMSSW using the auxiliary script `./cmssw_compile.sh` in the top directory (or equivalent).
- Now you can use these packages in cmsRun configs. See examples.
