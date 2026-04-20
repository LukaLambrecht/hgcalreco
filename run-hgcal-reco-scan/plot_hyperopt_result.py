import os
import sys
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
    if True:
        sorted_ids = np.argsort(losses)[::-1]
        results = [results[idx] for idx in sorted_ids]
        losses = losses[sorted_ids]

    # make plot
    fig, ax = plt.subplots()
    xax = np.arange(len(results))
    ax.scatter(xax, losses)
    ax.set_xlabel('Trial number', fontsize=12)
    ax.set_ylabel('Loss value', fontsize=12)
    ax.grid()
    fig.savefig('test.png')
