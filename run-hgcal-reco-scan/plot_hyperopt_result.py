import os
import sys
import json
import pickle
import numpy as np
import matplotlib.pyplot as plt


if __name__=='__main__':

    # read trials input file
    trials_file = sys.argv[1]

    # read trials object
    with open(trials_file, 'rb') as f:
        trials = pickle.load(f)

    # retrieve results
    results = trials.results
    losses = np.array(trials.losses())

    # optional: do sorting
    do_sort = True
    if do_sort:
        sorted_ids = np.argsort(losses)[::-1]
        results = [results[idx] for idx in sorted_ids]
        losses = losses[sorted_ids]

    # find best result
    best_idx = np.argmax(-losses)
    best_result = results[best_idx]

    # printouts
    print('Best result:')
    print(json.dumps(best_result, indent=2))

    # make plot
    fig, ax = plt.subplots()
    xax = np.arange(len(results))
    ax.scatter(xax, losses, c='dodgerblue')
    xaxtitle = 'Trial number'
    if do_sort: xaxtitle += ' (sorted by loss value)'
    ax.set_xlabel(xaxtitle, fontsize=15)
    ax.set_ylabel('Loss value', fontsize=15)
    ax.grid()
    fig.tight_layout()
    fig.savefig('test.png')

    # in case only 1 parameter was scanned, can plot metric vs this variable
    nparams = len(results[0]["params"]) # assume the same for all trials
    if nparams == 1:

        # dict for nicer axis label
        param_dict = {
            'deltac_hsi': r'$\delta_c (HSi)$'
        }

        # retrieve param values
        param_name = list(results[0]["params"].keys())[0]
        param_values = np.array([result["params"][param_name]["value"] for result in results])
        
        # sort
        sorted_ids = np.argsort(param_values)
        param_values = param_values[sorted_ids]
        losses_sorted = losses[sorted_ids]
        
        # plot
        fig, ax = plt.subplots()
        ax.scatter(param_values, losses_sorted, c='dodgerblue')
        ax.set_xlabel(param_dict.get(param_name, param_name), fontsize=15)
        ax.set_ylabel('Loss value', fontsize=15)
        ax.grid()
        fig.tight_layout()
        fig.savefig(f'test_{param_name}.png')

        # temp: print result for min and max values
        print(results[sorted_ids[0]])
        print(results[sorted_ids[-1]])
