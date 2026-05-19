"""
Re-export layer utilities from the canonical location in tools/layertools.py
This module maintains backward compatibility but users should import from tools.layertools directly.
"""

import os
import sys

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, topdir)

# Import and re-export from the canonical location
from tools.layertools import get_quantity_per_layer, get_layer_counts

__all__ = ['get_quantity_per_layer', 'get_layer_counts']

