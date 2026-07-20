# Custom CMSSW packages

This folder contains custom CMSSW packages.
They are kept outside of a specific CMSSW release directory,
but are copied via symbolic linking to the `CMSSW_X_Y_Z/src` directory,
so they are compiled and usable as if they would be located there.

See `make_symlinks.py` for creating the symbolic links.
This is done automatically by `cmssw_setup.sh` in the top directory when setting up a new CMSSW version,
so normally you do not need to run it yourself.


### How to use

- Write or modify CMSSW packages in this folder (see existing examples for formatting rules/conventions).
- If you added a new package to an already-set-up CMSSW area, re-make the symbolic links by running
`make_symlinks.py` from within this folder (with `cmsenv` sourced for that CMSSW area).
- Recompile CMSSW using the auxiliary script `./cmssw_compile.sh` in the top directory (or equivalent).
- Now you can use these packages in cmsRun configs. See examples.
