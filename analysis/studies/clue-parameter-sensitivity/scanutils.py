# Common tools for the studies on 1D CLUE parameter grid scans.


import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# default grid scan output directory
DEFAULT_INPUT = '/eos/home-l/llambrec/hgcalreco-data/gridscans/output_20261109_201X_D127_PU200'

# default CLUE parameter values (see run-hgcal-reco-scan/grids/clue2d/splitparams)
DEFAULT_PARAMS = {
    'deltac_all': 1.3, 'deltac_hsi': 1.3,
    'deltacold_all': 1.3, 'deltacold_hsi': 1.3,
    'deltas_all': 1.3, 'deltas_hsi': 1.3,
    'deltao_all': 2.6, 'deltao_hsi': 2.6,
    'ecut_all': 3, 'ecut_hsi': 3,
    'kappa_all': 9, 'kappa_hsi': 9,
}


# axis labels for the scanned parameters (same as in run-hgcal-reco-scan/plot_grid_result.py)
PARAM_LABELS = {
    'deltac_hsi': r'$\delta_c$ (HSi)', 'deltac_all': r'$\delta_c$ (all)',
    'deltacold_hsi': r'$\delta_c$ (old, correlated) (HSi)', 'deltacold_all': r'$\delta_c$ (old, correlated) (all)',
    'deltao_hsi': r'$\delta_o$ (HSi)', 'deltao_all': r'$\delta_o$ (all)',
    'deltas_hsi': r'$\delta_s$ (HSi)', 'deltas_all': r'$\delta_s$ (all)',
    'ecut_hsi': r'$E_{cut}$ (HSi)', 'ecut_all': r'$E_{cut}$ (all)',
    'kappa_hsi': r'$\rho_{seed}$ (HSi)', 'kappa_all': r'$\rho_{seed}$ (all)',
}



def get_job_param(jobdir):
    '''Get the (single) scanned parameter name and value of a grid scan job.'''
    with open(os.path.join(jobdir, 'params_summary.json'), 'r') as f:
        params = json.load(f)
    if len(params) != 1: raise Exception(f'Expected 1 parameter in {jobdir}, found {len(params)}.')
    return list(params.items())[0]


def job_is_ok(jobdir):
    '''Check whether a grid scan job finished successfully.'''
    resultfile = os.path.join(jobdir, 'result.json')
    if not os.path.exists(resultfile): return False
    with open(resultfile, 'r') as f:
        return json.load(f).get('status') == 'ok'


def get_grid_jobs(griddir):
    '''
    Get the successful grid points of a grid (with composition output),
    as a list of (job name, parameter name, parameter value, efficiency output directory),
    sorted by parameter value.
    '''
    jobs = []
    for jobdir in sorted([d for d in os.listdir(griddir) if d.startswith('job')]):
        jobpath = os.path.join(griddir, jobdir)
        if not job_is_ok(jobpath): continue
        effdir = os.path.join(jobpath, 'efficiency')
        if not os.path.exists(os.path.join(effdir, 'metrics_event_lc.parquet')): continue
        param_name, param_value = get_job_param(jobpath)
        jobs.append((jobdir, param_name, param_value, effdir))
    return sorted(jobs, key=lambda j: j[2])


def get_grids(inputdir):
    '''Get all grid names in a grid scan output directory.'''
    return sorted([d for d in os.listdir(inputdir) if os.path.isdir(os.path.join(inputdir, d))])


def make_axes(df, ylabel):
    fig, ax = plt.subplots(figsize=(7, 5))
    param_name = df['param_name'].iloc[0]
    ax.set_xscale('log')
    ax.set_xlabel(PARAM_LABELS.get(param_name, param_name), fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    if param_name in DEFAULT_PARAMS:
        ax.axvline(DEFAULT_PARAMS[param_name], color='#6b6b6b', linestyle=':', linewidth=1)
        ax.text(DEFAULT_PARAMS[param_name], 1.01, 'default', transform=ax.get_xaxis_transform(),
            ha='center', va='bottom', fontsize=9, color='#6b6b6b')
    return fig, ax


def savefig(fig, outputdir, name):
    fig.tight_layout()
    path = os.path.join(outputdir, f'{name}.png')
    fig.savefig(path)
    plt.close(fig)
    print(f'Created figure {path}')




def get_window_mask(values, param_name, factor):
    '''
    Mask of the parameter values within a factor of the default value
    (all values if factor is None or the default is unknown).
    '''
    values = np.asarray(values, dtype=float)
    default = DEFAULT_PARAMS.get(param_name)
    if factor is None or default is None: return np.ones(len(values), dtype=bool)
    return (values >= default / factor * (1 - 1e-9)) & (values <= default * factor * (1 + 1e-9))


# a grid point with all CLUE parameters at their default values
# (all grids run on the same events, so it can serve as reference for grids without a default point,
#  e.g. the deltao grids, which do not contain the default value 2.6; verified that all default points
#  in the 2026-11-09 PU200 scan give identical results)
DEFAULT_REFERENCE_JOB = 'kappa_hsi_1d/job10'


def get_default_row(df):
    '''Get the row of a per-grid-point dataframe at the default parameter value (or None).'''
    param_name = df['param_name'].iloc[0]
    if param_name not in DEFAULT_PARAMS: return None
    rows = df[np.isclose(df['param_value'], DEFAULT_PARAMS[param_name])]
    return rows.iloc[0] if len(rows) > 0 else None


def plot_heatmap(table, outputdir, name, title_text=None, cmax=0.5, fmt='{:.0%}'):
    '''
    Plot a table (DataFrame, rows = grids, columns = quantities) of (absolute) changes as an annotated heatmap.
    The colour scale saturates at cmax.
    '''
    fig, ax = plt.subplots(figsize=(1.6 * len(table.columns) + 3, 0.45 * len(table) + 2))
    values = table.values.astype(float)
    im = ax.imshow(np.clip(values, 0, cmax), cmap='Blues', vmin=0, vmax=cmax, aspect='auto')
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if not np.isfinite(values[i, j]): continue
            color = 'white' if values[i, j] > 0.6 * cmax else '#1a1a1a'
            ax.text(j, i, fmt.format(values[i, j]), ha='center', va='center', fontsize=9, color=color)
    ax.set_xticks(np.arange(len(table.columns)))
    ax.set_xticklabels(table.columns, fontsize=9, rotation=20, ha='right')
    ax.set_yticks(np.arange(len(table)))
    ax.set_yticklabels(table.index, fontsize=9)
    fig.colorbar(im, ax=ax, label=f'Maximum change (saturated at {fmt.format(cmax)})')
    if title_text is not None:
        ax.set_title(title_text, fontsize=10, loc='left')
    savefig(fig, outputdir, name)
