project = 'The Python Tutorial'
extensions = ['sphinx_markdown_builder', 'sphinx.ext.doctest']
master_doc = 'index'
highlight_language = 'python3'

from sphinx_markdown_builder import translator as _t
from sphinx_markdown_builder.contexts import IndentContext, SubContextParams
def _push_box(self, title):
    self._push_context(IndentContext("> ", empty=True, params=SubContextParams(2, 2)))
    self.add(f"**{title.title()}**", prefix_eol=0, suffix_eol=2)
_t.MarkdownTranslator._push_box = _push_box
version = '3.15'
rst_epilog = """
.. |python_version_literal| replace:: ``Python 3.15``
.. |python_x_dot_y_literal| replace:: ``python3.15``
.. |usr_local_bin_python_x_dot_y_literal| replace:: ``/usr/local/bin/python3.15``
"""

# ---- resolve references to the rest of the Python docs to docs.python.org ----
from docutils import nodes as _nodes
_D = 'https://docs.python.org/3/'
_EXT = {
    'bltin-ellipsis-object': ('library/stdtypes.html#bltin-ellipsis-object', 'The Ellipsis Object'),
    'bltin-exceptions': ('library/exceptions.html', 'Built-in Exceptions'),
    'bpo-36817-whatsnew': ('whatsnew/3.8.html#bpo-36817-whatsnew', 'self-documenting expressions'),
    'builtins-index': ('library/functions.html', 'Built-in Functions'),
    'c-api-index': ('c-api/index.html', 'Python/C API Reference Manual'),
    'extending-index': ('extending/index.html', 'Extending and Embedding the Python Interpreter'),
    'f-strings': ('reference/lexical_analysis.html#f-strings', 'f-strings'),
    'faq-index': ('faq/index.html', 'Python Frequently Asked Questions'),
    'faq-programming-raw-string-backslash': ('faq/programming.html#faq-programming-raw-string-backslash', 'the FAQ entry'),
    'formatspec': ('library/string.html#formatspec', 'Format Specification Mini-Language'),
    'formatstrings': ('library/string.html#formatstrings', 'Format String Syntax'),
    'function': ('reference/compound_stmts.html#function', 'Function definitions'),
    'glossary': ('glossary.html', 'Glossary'),
    'installing-index': ('installing/index.html', 'Installing Python Modules'),
    'instance-methods': ('reference/datamodel.html#instance-methods', 'Instance methods'),
    'launcher': ('using/windows.html#launcher', 'Python Launcher for Windows'),
    'library-index': ('library/index.html', 'The Python Standard Library'),
    'multiple-inheritance': ('reference/compound_stmts.html#multiple-inheritance', 'Multiple inheritance'),
    'old-string-formatting': ('library/stdtypes.html#old-string-formatting', 'printf-style String Formatting'),
    'private-name-mangling': ('reference/expressions.html#private-name-mangling', 'Private name mangling'),
    'python_2.3_mro': ('howto/mro.html', 'The Python 2.3 Method Resolution Order'),
    'reference-index': ('reference/index.html', 'The Python Language Reference'),
    'rlcompleter-config': ('library/site.html#rlcompleter-config', 'Readline configuration'),
    'setting-envvars': ('using/windows.html#setting-envvars', 'Excursus: Setting environment variables'),
    'shallow_vs_deep_copy': ('library/copy.html#shallow-vs-deep-copy', 'shallow copy'),
    'string-methods': ('library/stdtypes.html#string-methods', 'String Methods'),
    'sys-path-init': ('library/sys_path_init.html', 'The initialization of the sys.path module search path'),
    'textseq': ('library/stdtypes.html#textseq', 'Text Sequence Type — str'),
    'time-complexity': ('https://wiki.python.org/moin/TimeComplexity', 'TimeComplexity'),
    'types-set': ('library/stdtypes.html#types-set', 'Set Types'),
    'typesmapping': ('library/stdtypes.html#typesmapping', 'Mapping Types — dict'),
    'typesnumeric': ('library/stdtypes.html#typesnumeric', 'Numeric Types'),
    'typesseq': ('library/stdtypes.html#typesseq', 'Sequence Types — list, tuple, range'),
    'typesseq-list': ('library/stdtypes.html#typesseq-list', 'Lists'),
    'user-defined-funcs': ('reference/datamodel.html#user-defined-funcs', 'User-defined functions'),
    'using-on-controlling-color': ('using/cmdline.html#using-on-controlling-color', 'Controlling color'),
    'using-on-general': ('using/cmdline.html#using-on-general', 'Command line'),
    'why-can-t-i-use-an-assignment-in-an-expression': ('faq/design.html#why-can-t-i-use-an-assignment-in-an-expression', 'walrus operator'),
    'windows-store': ('using/windows.html#windows-store', 'The Microsoft Store package'),
}

def _missing_reference(app, env, node, contnode):
    if node.get('reftype') == 'ref':
        target = node.get('reftarget')
        if target in _EXT:
            path, title = _EXT[target]
            url = path if path.startswith('http') else _D + path
            text = contnode.astext()
            if node.get('refexplicit') is not True:
                text = title
            ref = _nodes.reference('', '', internal=False, refuri=url)
            ref += _nodes.inline(text, text)
            return ref
    if node.get('reftype') == 'term':
        target = node.get('reftarget')
        url = _D + 'glossary.html#term-' + target.lower().replace(' ', '-')
        ref = _nodes.reference('', '', internal=False, refuri=url)
        ref += contnode
        return ref
    return None

def setup(app):
    app.connect('missing-reference', _missing_reference)
