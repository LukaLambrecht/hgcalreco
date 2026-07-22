import os


def save_with_logy(fig, ax, figname):
    '''
    Save a figure as-is, and again with the y-axis on a log scale.
    The log-scale variant is saved next to the original, with "_logy"
    inserted before the file extension (e.g. "foo.png" -> "foo_logy.png").
    Note: figures with a y-axis lower bound of 0 (e.g. via set_ylim) are fine;
    matplotlib silently omits non-positive values on a log-scaled axis.
    '''
    fig.savefig(figname)
    print(f'Created figure {figname}')
    ax.set_yscale('log')
    fig.tight_layout()
    base, ext = os.path.splitext(figname)
    logy_figname = f'{base}_logy{ext}'
    fig.savefig(logy_figname)
    print(f'Created figure {logy_figname}')
