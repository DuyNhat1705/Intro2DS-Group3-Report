"""Section 2 (hierarchical parsing) tables and charts. Functions return Figure or DataFrame.

Import with ``from src import milestone2_section2 as m2s2`` from the repo root.
"""
import pandas as pd
import matplotlib.pyplot as plt
try:
    from . import _milestone2_data as data
except ImportError:
    import _milestone2_data as data

_GATHER_COLUMNS = ['arxiv_id', 'version', 'status', 'failure_reason', 'n_compile_files',
                   'n_redundant_files', 'n_missing_includes', 'bib_fallback',
                   'reused_from_prev', 'notes']


def _versions(data_dir=None):
    frame = data.parse_status(_GATHER_COLUMNS, data_dir)
    frame['status'] = frame.status.astype(str)
    return frame


def gathering_outcomes_table(data_dir=None):
    """How often each gathering rule was needed, over all versions of the corpus.

    Rules read from ``notes`` use only versions parsed in full: a version whose compiled
    files are identical to the previous version reuses that parse and stores no notes.
    """
    frame = _versions(data_dir)
    tex = frame[frame.status.ne('empty')]
    full = tex[~tex.reused_from_prev.astype(bool)]
    note = lambda key: int(data.has_token(full.notes, key).sum())
    reason = lambda key: int(data.has_token(tex.failure_reason, key).sum())

    several = note('root_candidates')
    fallback = note('root_fallback')
    copies = int((data.has_token(full.notes, 'dup_equal') | data.has_token(full.notes, 'dup_differ')).sum())

    base_all, base_tex, base_full = 'All versions', 'Versions with TeX', 'Versions parsed in full'
    rows = [
        ('Inventory', 'Versions recorded by Milestone 1', len(frame), base_all, len(frame)),
        ('Inventory', 'Versions without any .tex file (recorded as empty)', len(frame) - len(tex), base_all, len(frame)),
        ('Inventory', 'Versions with TeX sources', len(tex), base_all, len(frame)),
        ('Inventory', 'Versions reusing the parse of the previous version', len(tex) - len(full), base_tex, len(tex)),
        ('Root detection', 'Exactly one \\documentclass file', len(full) - several - fallback, base_full, len(full)),
        ('Root detection', 'Several \\documentclass files found', several, base_full, len(full)),
        ('Root detection', 'No \\documentclass file, fallback root', fallback, base_full, len(full)),
        ('Root detection', 'Root moved to the file that inputs the class header', note('root_includes_preamble'), base_full, len(full)),
        ('Includes', 'Compiled from more than one .tex file', int(tex.n_compile_files.gt(1).sum()), base_tex, len(tex)),
        ('Includes', 'Drive "(n)" copies collapsed onto the original', copies, base_full, len(full)),
        ('Includes', 'Included file is a complete document (body only)', note('nested_document'), base_full, len(full)),
        ('Includes', '\\includeonly applied', note('includeonly'), base_full, len(full)),
        ('Includes', 'At least one include target not found', int(tex.n_missing_includes.gt(0).sum()), base_tex, len(tex)),
        ('Includes', 'Missing .tex in the body, version marked partial', reason('missing_include'), base_tex, len(tex)),
        ('Includes', 'No \\begin{document} after gathering, marked partial', reason('no_begin_document'), base_tex, len(tex)),
        ('Conditionals', 'At least one undecidable conditional (first branch kept)', note('undecided_if'), base_full, len(full)),
        ('Bibliography', 'No named .bib resolved, every .bib of the version used', int(tex.bib_fallback.astype(bool).sum()), base_tex, len(tex)),
    ]
    table = pd.DataFrame(rows, columns=['Step', 'Observation', 'Versions', 'Base', 'Base size'])
    table['Share of base (%)'] = table.Versions / table['Base size'] * 100
    return table.drop(columns='Base size')


def file_counts_table(data_dir=None):
    """Compiled and redundant .tex files over the versions with TeX sources."""
    tex = _versions(data_dir).query("status != 'empty'")
    compiled, redundant = int(tex.n_compile_files.sum()), int(tex.n_redundant_files.sum())
    return pd.DataFrame([
        {'Files': 'On the compilation path', 'Count': compiled,
         'Share of .tex files (%)': compiled / (compiled + redundant) * 100,
         'Mean per version': tex.n_compile_files.mean(), 'Max per version': int(tex.n_compile_files.max())},
        {'Files': 'Redundant (unreachable or Drive copy)', 'Count': redundant,
         'Share of .tex files (%)': redundant / (compiled + redundant) * 100,
         'Mean per version': tex.n_redundant_files.mean(), 'Max per version': int(tex.n_redundant_files.max())},
    ])


def compile_files_21(data_dir=None):
    """Versions by number of compiled files, and by number of redundant files."""
    tex = _versions(data_dir).query("status != 'empty'")
    bins, labels = [0, 1, 2, 5, 10, 20, 50, float('inf')], ['1', '2', '3-5', '6-10', '11-20', '21-50', '>50']
    compiled = pd.cut(tex.n_compile_files, bins, labels=labels).value_counts().reindex(labels, fill_value=0)
    rbins, rlabels = [-1, 0, 1, 5, 20, float('inf')], ['0', '1', '2-5', '6-20', '>20']
    redundant = pd.cut(tex.n_redundant_files, rbins, labels=rlabels).value_counts().reindex(rlabels, fill_value=0)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    axes[0].bar(compiled.index.astype(str), compiled.to_numpy(), color='#3b6ea5')
    axes[0].set(title='Files on the compilation path', xlabel='.tex files compiled per version', ylabel='Versions')
    data.annotate(axes[0], len(tex))
    axes[1].bar(redundant.index.astype(str), redundant.to_numpy(), color='#c07a2c')
    axes[1].set(title='Redundant files left out', xlabel='Redundant .tex files per version', ylabel='Versions')
    data.annotate(axes[1], len(tex))
    fig.suptitle(f'Figure 2.1. Multi-file structure of the {len(tex):,} versions with TeX sources')
    return fig
