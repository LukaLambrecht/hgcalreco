# Tools for reading input files.


import os
import sys
import json
from DataFormats.FWLite import Events, Handle


class Reader(object):


    def __init__(self, input_config):
        '''
        Set labels and handles
        '''

        # read input config    
        if isinstance(input_config, dict): pass
        elif isinstance(input_config, str):
            with open(input_config, 'r') as f:
                input_config = json.load(f)

        # parse handles and labels
        self.config = {}
        for collection_name, input_data in input_config.items():
            dtype = input_data[0]
            label = tuple(input_data[1:])
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
