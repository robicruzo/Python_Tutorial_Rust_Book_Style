#!/usr/bin/env python3
"""Post-process the Sphinx markdown output of the official tutorial into mdBook chapters.

* cleans up interactive-session code blocks: removes the ``>>>`` / ``...`` prompts,
  turns the interpreter's output into ``#`` comments (so every block can be
  copy-pasted and run), and fixes the language tag so highlight.js picks the
  right grammar;
* restores method signatures that the markdown writer mangled;
* points references to other parts of the Python docs at docs.python.org;
* drops unreferenced index anchors.
"""
import ast
import glob
import os
import re
import sys

SRC_MD = sys.argv[1]      # sphinx markdown output dir
SRC_RST = sys.argv[2]     # rst sources
OUT = sys.argv[3]         # mdBook src dir

DOCS = 'https://docs.python.org/3/'
EXTERNAL_LABELS = {
    'library-index': ('The Python Standard Library', 'library/index.html'),
    'reference-index': ('The Python Language Reference', 'reference/index.html'),
    'installing-index': ('Installing Python Modules', 'installing/index.html'),
    'builtins-index': ('Built-in Functions', 'library/functions.html'),
    'faq-index': ('Python Frequently Asked Questions', 'faq/index.html'),
    'extending-index': ('Extending and Embedding the Python Interpreter', 'extending/index.html'),
    'c-api-index': ('Python/C API Reference Manual', 'c-api/index.html'),
    'using-index': ('Python Setup and Usage', 'using/index.html'),
    'glossary': ('Glossary', 'glossary.html'),
}

INLINE_WIDTH = 72


def is_prompt(line):
    return line.startswith('>>> ') or line.rstrip() == '>>>'


def is_cont(line):
    return line.startswith('... ') or line.rstrip() == '...'


def convert_repl(body):
    """Turn an interactive transcript into plain code with output as comments."""
    lines = body.rstrip('\n').split('\n')
    out = []          # list of (kind, text) ; kind in code/output/blank
    for i, line in enumerate(lines):
        if is_prompt(line):
            out.append(('code', line[4:]))
        elif is_cont(line):
            if line.rstrip() == '...':
                continue                      # end of a compound statement
            out.append(('code', line[4:]))
        elif line.strip() == '':
            nxt = next((l for l in lines[i + 1:] if l.strip()), None)
            prev = out[-1][0] if out else None
            if nxt is None or is_prompt(nxt) or prev in (None, 'blank'):
                out.append(('blank', ''))
            else:
                out.append(('output', ''))
        else:
            out.append(('output', line))

    # group consecutive kinds
    groups = []
    for kind, text in out:
        if groups and groups[-1][0] == kind and kind != 'blank':
            groups[-1][1].append(text)
        else:
            groups.append((kind, [text]))

    result = []
    i = 0
    while i < len(groups):
        kind, texts = groups[i]
        if kind == 'code':
            nxt = groups[i + 1] if i + 1 < len(groups) else None
            if (len(texts) == 1 and nxt and nxt[0] == 'output' and len(nxt[1]) == 1
                    and not texts[0].rstrip().endswith(':')
                    and not texts[0].lstrip().startswith('#')
                    and '#' not in texts[0]
                    and nxt[1][0].strip()
                    and len(texts[0]) + len(nxt[1][0]) + 4 <= INLINE_WIDTH):
                result.append(f'{texts[0]}  # {nxt[1][0]}')
                i += 2
                continue
            result.extend(texts)
        elif kind == 'output':
            result.extend(('# ' + t).rstrip() for t in texts)
        else:
            result.append('')
        i += 1
    # collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(result)).strip('\n')
    return text + '\n'


SHELL_RE = re.compile(r'^(\$ |\(\S+\) \$ |C:\\|PS |%\s)', re.M)


def classify(lang, body):
    """Return (language, new_body)."""
    if lang in ('shell-session', 'console', 'shell', 'sh', 'bash'):
        return 'console', body
    if lang in ('none', 'text'):
        return 'text', body
    if re.search(r'^>>>( |$)', body, re.M):
        return 'python', convert_repl(body)
    if re.match(r'^\.\.\. ', body):
        return 'python', '\n'.join(l[4:] for l in body.split('\n'))
    stripped = body.strip()
    if SHELL_RE.search(body):
        return 'console', body
    if re.match(r'^(python3?(\.\d+)?|pip|py|source|cd|ls|chmod)( |$)', stripped) or \
            re.match(r'^[\w\-]+\\Scripts\\', stripped):
        return 'console', body
    try:
        ast.parse(body)
        return 'python', body
    except SyntaxError:
        pass
    # Python-ish pseudo code (grammar sketches with placeholders) still reads best highlighted
    if re.search(r'^\s*(def|class|case|from|import|for|if|while|match|return|async|\w+\()', body, re.M) \
            and not re.search(r'^\s*[-|+]{3,}', body, re.M):
        return 'python', body
    return 'text', body


FENCE_RE = re.compile(r'^([ \t]*)```(\S*)\n(.*?)^\1```[ \t]*$', re.S | re.M)


def fix_code(md):
    def repl(m):
        indent, lang, body = m.group(1), m.group(2), m.group(3)
        if indent:
            body = '\n'.join(l[len(indent):] if l.startswith(indent) else l.lstrip()
                             for l in body.split('\n'))
        lang, body = classify(lang, body)
        block = f'```{lang}\n{body}```'
        if indent:
            block = '\n'.join((indent + l) if l else l for l in block.split('\n'))
        return block
    return FENCE_RE.sub(repl, md)


def fix_methods(md, rst):
    sigs = re.findall(r'^\.\. method:: (.+)$', rst, re.M)
    by_name = {s.split('(')[0]: s for s in sigs}

    def repl(m):
        name = m.group(1)
        if name in by_name:
            return f'#### `{by_name[name]}`'
        return m.group(0)
    return re.sub(r'^#### ([\w.]+)\(.*\)$', repl, md, flags=re.M)


def fix_external_labels(md):
    for label, (title, path) in EXTERNAL_LABELS.items():
        md = re.sub(rf'(?<![\w/#-]){re.escape(label)}(?![\w-])', f'[{title}]({DOCS}{path})', md)
    return md


def drop_unused_anchors(md, all_md):
    def repl(m):
        anchor = m.group(1)
        if re.match(r'index-\d+$', anchor) and f'#{anchor})' not in all_md:
            return ''
        return m.group(0)
    md = re.sub(r'^<a id="([^"]+)"></a>\n\n?', repl, md, flags=re.M)
    return md


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SRC_MD, '*.md')))
    all_md = ''.join(open(f, encoding='utf-8').read() for f in files)
    for f in files:
        name = os.path.basename(f)
        md = open(f, encoding='utf-8').read()
        rst_path = os.path.join(SRC_RST, name[:-3] + '.rst')
        rst = open(rst_path, encoding='utf-8').read() if os.path.exists(rst_path) else ''
        md = fix_methods(md, rst)
        md = fix_code(md)
        md = fix_external_labels(md)
        md = drop_unused_anchors(md, all_md)
        md = re.sub(r'\n{3,}', '\n\n', md)
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as fh:
            fh.write(md.strip() + '\n')
        print('wrote', name)


if __name__ == '__main__':
    main()


# ---------------------------------------------------------------------------
# Hand-made edits that the code-block clean-up makes necessary
# ---------------------------------------------------------------------------
INTRO_OLD_START = 'In the following examples, input and output are distinguished'
INTRO_NEW = """In the following examples, the code you type is shown just as you would write it
in a file or at the interactive prompt, and the output the interpreter prints in
response is shown as a comment right after it: either at the end of the same
line, as in `2 + 2  # 4`, or on the lines below, each one starting with `#`.
Because output is written as comments, every example can be copied and pasted
into the interpreter (or into a script) as is.  When you type the examples at the
interactive prompt yourself, you will of course see the familiar
[>>>](https://docs.python.org/3/glossary.html#term-0) and
[…](https://docs.python.org/3/glossary.html#term-...) prompts, and you will need
to type a blank line to end a multi-line command such as a `for` loop."""


def patch(out_dir):
    p = os.path.join(out_dir, 'introduction.md')
    md = open(p, encoding='utf-8').read()
    start = md.index(INTRO_OLD_START)
    end = md.index('\n\n', start)
    md = md[:start] + INTRO_NEW + md[end:]
    open(p, 'w', encoding='utf-8').write(md)

    for name in os.listdir(out_dir):
        if not name.endswith('.md'):
            continue
        p = os.path.join(out_dir, name)
        md = open(p, encoding='utf-8').read()
        md = md.replace('glossary.html#term->>>)', 'glossary.html#term-0)')
        if name == 'index.md':
            # the sidebar already shows the table of contents
            md = re.split(r'\n\* \[Whetting Your Appetite\]', md)[0].rstrip() + '\n'
        open(p, 'w', encoding='utf-8').write(md)


patch(OUT)
