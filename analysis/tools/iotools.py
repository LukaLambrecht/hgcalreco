# Tools for reading input files.


import os
import re
import sys
import json
from DataFormats.FWLite import Events, Handle


def _io_versioned_variant(dtype, namespace='io_v1'):
    '''
    Build a variant of a C++ Handle dtype string with a ROOT schema-evolution
    namespace (e.g. "io_v1") inserted in front of the wrapped class name.
    Example: "std::vector<ticl::Trackster>" -> "std::vector<ticl::io_v1::Trackster>"
    '''
    def insert_namespace(match):
        typename = match.group(1)
        parts = typename.rsplit('::', 1)
        if len(parts) == 1:
            new_typename = f'{namespace}::{parts[0]}'
        else:
            new_typename = f'{parts[0]}::{namespace}::{parts[1]}'
        return f'<{new_typename}>'
    return re.sub(r'<([^<>]+)>', insert_namespace, dtype, count=1)


class Reader(object):


    def __init__(self, input_configs, exclude=None):
        '''
        Set labels and handles
        '''

        # initialization
        self.config = {}

        # loop over input configs
        if not isinstance(input_configs, list):
            input_configs = [input_configs]
        for input_config in input_configs:

            # read input config    
            if isinstance(input_config, dict): pass
            elif isinstance(input_config, str):
                with open(input_config, 'r') as f:
                    input_config = json.load(f)

            # loop over collections to set handles and labels for
            for collection_name, input_data in input_config.items():
                dtype = input_data[0]
                label = tuple(input_data[1:])

                # exclude certain collections if requested
                if exclude is not None and collection_name in exclude: continue
                
                # check duplication
                if collection_name in self.config and self.config[collection_name] != label:
                    msg = f'WARNING: in Reader.__init__: found duplicate collection name "{collection_name}";'
                    msg += f' will use latest dtype "{dtype}" and label "{label}".'
                    print(msg)

                # set the handle and label
                # note: some ROOT versions (starting from the one bundled with CMSSW_20)
                #       wrap EDM classes with schema-evolution rules (e.g. CaloParticle,
                #       SimCluster, HGCRecHit, reco::CaloCluster, ticl::Trackster) in an
                #       inline "io_v1" namespace; the plain (unversioned) dtype string
                #       then fails to resolve, so fall back to the versioned variant.
                try:
                    handle = Handle(dtype)
                except TypeError:
                    handle = Handle(_io_versioned_variant(dtype))
                self.config[collection_name] = {'handle': handle, 'label': label}


    def read_event(self, event):
        '''
        Read requested collections from a given event
        '''

        collections = {}
        for collection_name, read_data in self.config.items():
            label = read_data['label']
            handle = read_data['handle']
            if not event.getByLabel(label, handle):
                msg = f"WARNING: Could not find collection '{collection_name}' with label {label}"
                print(msg, file=sys.stderr)
                collections[collection_name] = None
                continue
            product = handle.product()
            if product is None:
                msg = f"WARNING: Collection '{collection_name}' is None after getByLabel"
                print(msg, file=sys.stderr)
            collections[collection_name] = product
        return collections
