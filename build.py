#!/usr/bin/env python3
"""Build the Python tutorial site with an mdBook-inspired layout."""
from __future__ import annotations

import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure docutils from the system site-packages is available.
sys.path.append('/usr/lib/python3/dist-packages')  # noqa: E402

from docutils import nodes  # type: ignore  # noqa: E402
from docutils.core import publish_parts  # type: ignore  # noqa: E402
from docutils.parsers.rst import Directive, directives, roles  # type: ignore  # noqa: E402

warnings.filterwarnings('ignore', category=SyntaxWarning)

ROOT = Path(__file__).resolve().parent
TUTORIAL_SRC = ROOT.parent / 'tutorial'
SITE_TITLE = 'The Python Tutorial'
SIDEBAR_KEY = 'python-tutorial-sidebar'


@dataclass
class Page:
    slug: str
    title: str
    body: str


def collect_labels() -> Dict[str, Tuple[str, str]]:
    """Collect reST label targets so :ref: roles can become internal links."""
    labels: Dict[str, Tuple[str, str]] = {}
    label_pattern = re.compile(r'^\.\. _(.+?):\s*$', re.MULTILINE)
    for rst_path in TUTORIAL_SRC.glob('*.rst'):
        text = rst_path.read_text(encoding='utf-8')
        for match in label_pattern.finditer(text):
            label = match.group(1).strip()
            # Labels sometimes encode hierarchy via spaces; convert to dashes for URLs.
            anchor = label.replace(' ', '-')
            labels[label] = (rst_path.stem, anchor)
    return labels


def parse_role_text(text: str) -> Tuple[str, str]:
    """Extract display text and target from an interpreted text role body."""
    display = text
    target = text
    if '<' in text and text.strip().endswith('>'):
        display_part, target_part = text.split('<', 1)
        display = display_part.strip()
        target = target_part[:-1].strip()
    display = display.lstrip('!~')
    target = target.lstrip('!~')
    return display, target or display


def register_roles(labels: Dict[str, Tuple[str, str]]) -> None:
    """Register lightweight replacements for Sphinx-specific roles."""

    def literal_role(name, rawtext, text, lineno, inliner, options=None, content=None):
        display, _ = parse_role_text(text)
        if not display:
            display = text
        node = nodes.literal(display, display)
        return [node], []

    def emphasis_role(name, rawtext, text, lineno, inliner, options=None, content=None):
        display, _ = parse_role_text(text)
        if not display:
            display = text
        node = nodes.emphasis(display, display)
        return [node], []

    def ref_role(name, rawtext, text, lineno, inliner, options=None, content=None):
        display, target = parse_role_text(text)
        slug_anchor = labels.get(target) or labels.get(target.replace(' ', '-'))
        if slug_anchor:
            slug, anchor = slug_anchor
            if not display:
                display = target
            refuri = f"{slug}.html#{anchor}"
            node = nodes.reference(display, display, refuri=refuri)
            node['classes'].append('internal-ref')
            return [node], []
        # Fall back to literal formatting if we cannot resolve the reference.
        if not display:
            display = target
        node = nodes.inline(display, display)
        node['classes'].append('xref')
        return [node], []

    def index_role(name, rawtext, text, lineno, inliner, options=None, content=None):
        # Index roles only affect builders that generate an index; we can drop them.
        return [], []

    literal_roles = [
        'attr', 'class', 'code', 'const', 'data', 'envvar', 'exc', 'file',
        'func', 'kbd', 'keyword', 'meth', 'mod', 'option', 'pep', 'program',
        'rfc',
    ]
    for role_name in literal_roles:
        roles.register_local_role(role_name, literal_role)
    roles.register_local_role('term', emphasis_role)
    roles.register_local_role('dfn', emphasis_role)
    roles.register_local_role('ref', ref_role)
    roles.register_local_role('index', index_role)


def register_directives() -> None:
    """Register directive stubs or replacements for Sphinx-specific directives."""

    class EmptyDirective(Directive):
        has_content = True
        required_arguments = 0
        optional_arguments = 0
        option_spec: Dict[str, object] = {}

        def run(self):
            return []

    class DoctestDirective(Directive):
        has_content = True
        required_arguments = 0
        option_spec: Dict[str, object] = {}

        def run(self):
            text = '\n'.join(self.content)
            block = nodes.literal_block(text, text)
            block['language'] = 'pycon'
            block['classes'].extend(['doctest-block'])
            return [block]

    class OnlyDirective(Directive):
        has_content = True
        required_arguments = 1
        optional_arguments = 0
        option_spec: Dict[str, object] = {}

        def run(self):
            targets = ' '.join(self.arguments).split()
            if 'html' not in targets and 'builder-html' not in targets:
                return []
            container = nodes.container()
            self.state.nested_parse(self.content, self.content_offset, container)
            return list(container.children)

    class MethodDirective(Directive):
        has_content = True
        required_arguments = 1
        optional_arguments = 0
        option_spec = {'noindex': directives.flag}

        def run(self):
            signature = self.arguments[0]
            container = nodes.container(classes=['method'])
            title = nodes.paragraph('', '', nodes.strong(signature, signature))
            title['classes'].append('method-signature')
            container += title
            body = nodes.container()
            self.state.nested_parse(self.content, self.content_offset, body)
            container.extend(body.children)
            return [container]

    directives.register_directive('index', EmptyDirective)
    directives.register_directive('sectionauthor', EmptyDirective)
    directives.register_directive('testsetup', EmptyDirective)
    directives.register_directive('toctree', EmptyDirective)
    directives.register_directive('doctest', DoctestDirective)
    directives.register_directive('only', OnlyDirective)
    directives.register_directive('method', MethodDirective)


def extract_toctree_entries(index_text: str) -> List[str]:
    """Pull the toctree entries from the tutorial index."""
    pattern = re.compile(r'\.\. toctree::.*?(?:\n[ \t]+.*)+', re.DOTALL)
    match = pattern.search(index_text)
    if not match:
        return []
    block = match.group(0)
    entries: List[str] = []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(':'):
            continue
        if stripped.endswith('.rst'):
            stripped = stripped[:-4]
        entries.append(stripped)
    return entries


BASE_TEMPLATE = """<!DOCTYPE HTML>
<html lang=\"en\" class=\"light sidebar-visible\" dir=\"ltr\">
<head>
    <meta charset=\"UTF-8\">
    <title>{head_title}</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <meta name=\"theme-color\" content=\"#ffffff\">
    <script>
        const theme_storage_key = \"mdbook-theme\";
        const default_light_theme = \"light\";
        const default_dark_theme = \"navy\";
        window.theme_storage_key = theme_storage_key;
        window.default_light_theme = default_light_theme;
        window.default_dark_theme = default_dark_theme;
        (function () {{
            const html = document.documentElement;
            let storedTheme = null;
            try {{
                storedTheme = localStorage.getItem(theme_storage_key);
            }} catch (err) {{
                storedTheme = null;
            }}
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            const resolved = (!storedTheme || storedTheme === 'default_theme')
                ? (prefersDark ? default_dark_theme : default_light_theme)
                : storedTheme;
            html.classList.remove('light');
            html.classList.add(resolved);
            window.default_theme = resolved;
        }})();
    </script>
    <link rel=\"icon\" href=\"favicon-de23e50b.svg\">
    <link rel=\"shortcut icon\" href=\"favicon-8114d1fc.png\">
    <link rel=\"stylesheet\" href=\"css/variables-3865ffda.css\">
    <link rel=\"stylesheet\" href=\"css/general-4c35105a.css\">
    <link rel=\"stylesheet\" href=\"css/chrome-c0e702bf.css\">
    <link rel=\"stylesheet\" href=\"css/print-ad67d350.css\" media=\"print\">
    <link rel=\"stylesheet\" href=\"FontAwesome/css/font-awesome-799aeb25.css\">
    <link rel=\"stylesheet\" href=\"fonts/fonts-9644e21d.css\">
    <link rel=\"stylesheet\" id=\"highlight-css\" href=\"highlight-493f70e1.css\">
    <link rel=\"stylesheet\" id=\"tomorrow-night-css\" href=\"tomorrow-night-4c0ae647.css\">
    <link rel=\"stylesheet\" id=\"ayu-highlight-css\" href=\"ayu-highlight-56612340.css\">
    <link rel=\"stylesheet\" href=\"ferris-d33b75bf.css\">
    <link rel=\"stylesheet\" href=\"theme/2018-edition-4e126c62.css\">
    <link rel=\"stylesheet\" href=\"theme/semantic-notes-9b5766c0.css\">
    <link rel=\"stylesheet\" href=\"theme/listing-cab26221.css\">
    <link rel=\"stylesheet\" href=\"site.css\">
</head>
<body>
<div id=\"body-container\">
    <input type=\"checkbox\" id=\"sidebar-toggle-anchor\" class=\"hidden\" checked>
    <nav id=\"sidebar\" class=\"sidebar\" aria-label=\"Table of contents\">
        <div class=\"sidebar-scrollbox\">
            <ol class=\"chapter\">{sidebar}</ol>
        </div>
        <div id=\"sidebar-resize-handle\" class=\"sidebar-resize-handle\">
            <div class=\"sidebar-resize-indicator\"></div>
        </div>
    </nav>
    <div id=\"page-wrapper\" class=\"page-wrapper\">
        <div class=\"page\">
            <div id=\"menu-bar-hover-placeholder\"></div>
            <div id=\"menu-bar\" class=\"menu-bar sticky\">
                <div class=\"left-buttons\">
                    <label id=\"sidebar-toggle\" class=\"icon-button\" for=\"sidebar-toggle-anchor\" title=\"Toggle Table of Contents\" aria-label=\"Toggle Table of Contents\" aria-controls=\"sidebar\">
                        <i class=\"fa fa-bars\"></i>
                    </label>
                    <button id=\"theme-toggle\" class=\"icon-button\" type=\"button\" title=\"Change theme\" aria-label=\"Change theme\" aria-haspopup=\"true\" aria-expanded=\"false\" aria-controls=\"theme-list\">
                        <i class=\"fa fa-paint-brush\"></i>
                    </button>
                    <ul id=\"theme-list\" class=\"theme-popup\" aria-label=\"Themes\" role=\"menu\" style=\"display: none;\">
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"default_theme\">Auto</button></li>
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"light\">Light</button></li>
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"rust\">Rust</button></li>
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"coal\">Coal</button></li>
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"navy\">Navy</button></li>
                        <li role=\"none\"><button role=\"menuitem\" class=\"theme\" id=\"ayu\">Ayu</button></li>
                    </ul>
                </div>
                <h1 class=\"menu-title\">{menu_title}</h1>
                <div class=\"right-buttons\"></div>
            </div>
            <main id=\"content\" class=\"content\">
{body}
            </main>
            <nav class=\"nav-wrapper\" aria-label=\"Page navigation\">
                {mobile_prev}
                {mobile_next}
                <div style=\"clear: both\"></div>
            </nav>
        </div>
        <nav class=\"nav-wide-wrapper\" aria-label=\"Page navigation\">
            {prev_link}
            {next_link}
        </nav>
    </div>
</div>
<script src=\"js/site.js\"></script>
</body>
</html>"""


def render_sidebar(pages: List[Page], current_slug: str) -> str:
    items: List[str] = []
    for index, page in enumerate(pages):
        is_current = page.slug == current_slug
        classes = ['chapter-item', 'expanded']
        if is_current:
            classes.append('active')
        number = '' if index == 0 else f'<strong aria-hidden="true">{index}.</strong> '
        attrs = ''
        if is_current:
            attrs = ' data-current="true"'
        items.append(
            f'<li class="{" ".join(classes)}">'
            f'<a href="{page.slug}.html"{attrs}>{number}{page.title}</a>'
            '</li>'
        )
    return ''.join(items)


def render_nav_link(slug: str, title: str, direction: str) -> str:
    icon = 'fa-angle-left' if direction == 'prev' else 'fa-angle-right'
    rel = 'prev' if direction == 'prev' else 'next'
    return (
        f'<a rel="{rel}" href="{slug}.html" '
        f'class="nav-chapters {direction}" title="{title}" aria-label="{title}">' \
        f'<i class="fa {icon}"></i></a>'
    )


def render_mobile_link(slug: str, title: str, direction: str) -> str:
    icon = 'fa-angle-left' if direction == 'prev' else 'fa-angle-right'
    rel = 'prev' if direction == 'prev' else 'next'
    cls = 'previous' if direction == 'prev' else 'next'
    return (
        f'<a rel="{rel}" href="{slug}.html" class="mobile-nav-chapters {cls}" '
        f'title="{title}" aria-label="{title}">'
        f'<i class="fa {icon}"></i></a>'
    )


def build_pages() -> None:
    labels = collect_labels()
    register_roles(labels)
    register_directives()

    index_text = (TUTORIAL_SRC / 'index.rst').read_text(encoding='utf-8')
    ordered_slugs = ['index'] + extract_toctree_entries(index_text)

    settings = {
        'report_level': 5,
        'halt_level': 6,
        'warning_stream': None,
    }

    pages: List[Page] = []
    for slug in ordered_slugs:
        rst_path = TUTORIAL_SRC / f'{slug}.rst'
        if not rst_path.exists():
            print(f'Warning: missing source for {slug}', file=sys.stderr)
            continue
        parts = publish_parts(source=rst_path.read_text(encoding='utf-8'),
                              source_path=str(rst_path),
                              writer_name='html5',
                              settings_overrides=settings)
        title = parts.get('title', slug.replace('-', ' ').title())
        body = parts['body']
        pages.append(Page(slug=slug, title=title, body=body))

    for idx, page in enumerate(pages):
        prev_html = next_html = ''
        mobile_prev = mobile_next = ''
        if idx > 0:
            prev_page = pages[idx - 1]
            prev_html = render_nav_link(prev_page.slug, prev_page.title, 'prev')
            mobile_prev = render_mobile_link(prev_page.slug, prev_page.title, 'prev')
        if idx < len(pages) - 1:
            next_page = pages[idx + 1]
            next_html = render_nav_link(next_page.slug, next_page.title, 'next')
            mobile_next = render_mobile_link(next_page.slug, next_page.title, 'next')

        sidebar_html = render_sidebar(pages, page.slug)
        html = BASE_TEMPLATE.format(
            head_title=f"{page.title} - {SITE_TITLE}",
            menu_title=SITE_TITLE,
            sidebar=sidebar_html,
            body=indent_html(page.body.strip(), prefix=' ' * 12),
            prev_link=prev_html,
            next_link=next_html,
            mobile_prev=mobile_prev,
            mobile_next=mobile_next,
        )
        output_path = ROOT / f'{page.slug}.html'
        output_path.write_text(html, encoding='utf-8')
        print(f'Built {output_path.relative_to(ROOT)}')


def indent_html(html: str, prefix: str) -> str:
    return '\n'.join(prefix + line if line else '' for line in html.splitlines())


if __name__ == '__main__':
    build_pages()
