import os
import sys
import numpy as np


def get_quantity_per_layer(quantity, layers, keys=None, absolute=False):
    '''
    Partition a collection of values per layer number
    Input arguments:
    - quantity: 1D array of values to partition
    - layers: 1D array of layer numbers
    - keys: keys to put in the output dict
      (default: determine automatically from provided layer numbers)
    - absolute: use absolute layer number
      (default: use signed layer number)
    Returns
    - dict of the form {layer number: array of values in this layer}
    '''
    quantity_per_layer = {}
    if absolute: layers = np.abs(layers)
    unique_layers = keys if keys is not None else sorted(np.unique(layers))
    for layer in unique_layers:
        mask = (layers == layer).astype(bool)
        values = quantity[mask]
        quantity_per_layer[layer] = values
    return quantity_per_layer


def get_layer_counts(layers, **kwargs):
    '''
    Get a layer count.
    Input arguments:
    - layers: 1D array of layer numbers
    Returns:
    - dict of the form {layer number: number of instances}
    '''
    counts_per_layer = get_quantity_per_layer(np.ones(len(layers)), layers, **kwargs)
    for layer, values in counts_per_layer.items():
        counts_per_layer[layer] = len(values)
    return counts_per_layer
