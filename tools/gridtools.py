import os
import sys
import itertools


def get_grid_points(grid):
    '''
    Get all points in the grid.
    Input arguments: grid of the following form:
        [
            {
                "name": parameter name
                "mod": modifier string for cmsRun config (with template VALUE)
                "values": values that this parameter takes
            },
            ...
        ]
    Returns: list of grid points in the following form:
        [
            {parameter name: {"value": value, "mod": modifier string}}
        ]
    '''

    # loop over all combinations of values
    allvalues = [param["values"] for param in grid]
    paramnames = [param["name"] for param in grid]
    parammods = [param["mod"] for param in grid]
    combinations = itertools.product(*allvalues)
    gridpoints = []
    for valueset in combinations:
        
        # make gridpoint
        modifiers = [mod.replace("VALUE", str(val)) for mod, val in zip(parammods, valueset)]
        gridpoint = {name: {"value": val, "mod": mod} for name, val, mod in zip(paramnames, valueset, modifiers)}
        gridpoints.append(gridpoint)

    return gridpoints
