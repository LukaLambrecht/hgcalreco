#!/usr/bin/bash

# Simple utility to compile currently sourced CMSSW

cd $CMSSW_BASE/src
scram b -j 8
