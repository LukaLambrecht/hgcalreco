# Common tools for the studies on CLUE parameter grid scans.
# Most plots are made for 1D grids (one scanned parameter, on the x-axis);
# with the "flat" option, any grid (1D or multi-dimensional) can be shown with all grid points
# on a single axis, sorted by a chosen quantity.


import os
import json
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# default grid scan output directory
DEFAULT_INPUT = '/eos/home-l/llambrec/hgcalreco-data/gridscans/output_20261120_201X_D127_PU200'

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



def get_job_params(jobdir):
    '''Get all scanned parameter names and values of a grid scan job (as a dict).'''
    with open(os.path.join(jobdir, 'params_summary.json'), 'r') as f:
        return json.load(f)


def get_job_param(jobdir):
    '''Get the (single) scanned parameter name and value of a grid scan job.'''
    params = get_job_params(jobdir)
    if len(params) != 1:
        raise Exception(f'Expected 1 parameter in {jobdir}, found {len(params)}'
            + ' (use the --flat option for multi-parameter grids).')
    return list(params.items())[0]


def is_default_params(params):
    '''Check whether all parameters (dict of name: value) are at their default values.'''
    return all(name in DEFAULT_PARAMS and np.isclose(value, DEFAULT_PARAMS[name]) for name, value in params.items())


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


def get_grid_jobs_flat(griddir):
    '''
    Get the successful grid points of a grid (with composition output), for any number of parameters,
    as a list of (job name, dict of parameter values, efficiency output directory), sorted by job number.
    '''
    jobdirs = [d for d in os.listdir(griddir) if d.startswith('job')]
    jobdirs = sorted(jobdirs, key=lambda d: int(d[3:]) if d[3:].isdigit() else d)
    def check(jobdir):
        jobpath = os.path.join(griddir, jobdir)
        if not job_is_ok(jobpath): return None
        effdir = os.path.join(jobpath, 'efficiency')
        if not os.path.exists(os.path.join(effdir, 'metrics_event_lc.parquet')): return None
        return (jobdir, get_job_params(jobpath), effdir)
    # (reading many small files from EOS is mostly waiting for I/O, so use parallel threads)
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = list(executor.map(check, jobdirs))
    return [job for job in jobs if job is not None]


def get_job_number(jobdir):
    '''Numeric job index from a job directory name (e.g. "job12" -> 12; -1 if not numeric).'''
    return int(jobdir[3:]) if jobdir.startswith('job') and jobdir[3:].isdigit() else -1


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


def make_flat_axes(ylabel, sortlabel, default_x=None, xlabel='Grid scan point', fontscale=1., figsize=(7, 5)):
    '''
    Axes for a "flat" grid scan plot: all grid points on a single axis (x = position after sorting).
    default_x: position of the default grid point (if any), marked with a vertical line.
    xlabel: name of the points on the x-axis (followed by the sorting label, unless sortlabel is None).
    fontscale: scale factor for the font sizes (axis titles and tick labels).
    '''
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlabel(xlabel if sortlabel is None else f'{xlabel}\n(sorted by {sortlabel})', fontsize=12 * fontscale)
    ax.set_ylabel(ylabel, fontsize=12 * fontscale)
    if fontscale != 1.: ax.tick_params(axis='both', labelsize=10 * fontscale)
    if default_x is not None:
        ax.axvline(default_x, color='#6b6b6b', linestyle=':', linewidth=1)
        ax.text(default_x, 1.01, 'default', transform=ax.get_xaxis_transform(),
            ha='center', va='bottom', fontsize=9, color='#6b6b6b')
    return fig, ax


def flat_style(npoints, linewidth=2, markersize=5):
    '''Line width and marker size for flat plots (smaller for many points).'''
    if npoints <= 30: return linewidth, markersize
    if npoints <= 100: return 1.5, 3
    return 1, 1.5


def savefig(fig, outputdir, name):
    fig.tight_layout()
    path = os.path.join(outputdir, f'{name}.png')
    fig.savefig(path)
    plt.close(fig)
    print(f'Created figure {path}')




def find_default_job(inputdir):
    '''
    Find a grid point with all CLUE parameters at their default values in a grid scan output directory
    (all grids run on the same events, so it can serve as reference for grids without a default point,
    e.g. the deltao grids, which do not contain the default value 2.6).
    Returns the job directory relative to inputdir (e.g. "kappa_hsi_1d/job4"), or None if not found.
    '''
    for grid in get_grids(inputdir):
        griddir = os.path.join(inputdir, grid)
        for jobdir, params, effdir in get_grid_jobs_flat(griddir):
            if is_default_params(params): return os.path.join(grid, jobdir)
    return None


def get_default_row(df):
    '''Get the row of a per-grid-point dataframe at the default parameter value(s) (or None).'''
    if 'is_default' in df.columns:
        rows = df[df['is_default']]
        return rows.iloc[0] if len(rows) > 0 else None
    param_name = df['param_name'].iloc[0]
    if param_name not in DEFAULT_PARAMS: return None
    rows = df[np.isclose(df['param_value'], DEFAULT_PARAMS[param_name])]
    return rows.iloc[0] if len(rows) > 0 else None
