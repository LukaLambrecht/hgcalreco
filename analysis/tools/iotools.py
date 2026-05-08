# Tools for reading input files.


import os
import sys
import json
from DataFormats.FWLite import Events, Handle


class Reader(object):


    def __init__(self, input_configs):
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
                
                # check duplication
                if collection_name in self.config and self.config[collection_name] != label:
                    msg = f'WARNING: in Reader.__init__: found duplicate collection name "{collection_name}";'
                    msg += ' will use latest dtype "{dtype}" and label "{label}".'
                    print(msg)

                # set the handle and label
                handle = Handle(dtype)
                self.config[collection_name] = {'handle': handle, 'label': label}


    def read_event(self, event):
        '''
        Read requested collections from a given event
        '''

        collections = {}
        for collection_name, read_data in self.config.items():
            label = read_data['label']
            handle = read_data['handle']
            event.getByLabel(label, handle)
            collections[collection_name] = handle.product()
        return collections
