"""Build the full static HTML edition with Python's standard library."""
from pathlib import Path
import html
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = json.loads((ROOT / 'report-content.json').read_text(encoding='utf-8'))
SITE = 'https://never-nude.github.io/atrium-technical-report/'
REPO = 'https://github.com/never-nude/atrium-technical-report'


def slug(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


TOKEN = re.compile(r'(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\(https?://[^\s)]+\)|\[R\d+(?:-R?\d+)?(?:,\s*R\d+(?:-R?\d+)?)*\])')


def inline(text, sources=False):
    result = []
    for part in TOKEN.split(text):
        if part.startswith('`') and part.endswith('`'):
            result.append('<code>' + html.escape(part[1:-1]) + '</code>')
        elif part.startswith('**') and part.endswith('**'):
            result.append('<strong>' + html.escape(part[2:-2]) + '</strong>')
        elif match := re.fullmatch(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', part):
            label, url = match.groups()
            reference = re.match(r'R(\d+) - ', label) if sources else None
            anchor = f' id="ref-{reference[1]}"' if reference else ''
            result.append(f'<a{anchor} href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        elif re.fullmatch(r'\[R\d+(?:-R?\d+)?(?:,\s*R\d+(?:-R?\d+)?)*\]', part):
            result.append('[' + re.sub(r'R(\d+)', lambda m: f'<a class="reference" href="#ref-{m[1]}">R{m[1]}</a>', part[1:-1]) + ']')
        else:
            result.append(html.escape(part))
    return ''.join(result)


PIPELINE = '''<figure class="pipeline" aria-labelledby="pipeline-caption">
<ol class="pipeline-main">
<li><h4>Offline ingest</h4><p>Source records + scans<br>Node / Python / glTF tools</p></li>
<li><h4>Static build</h4><p>Catalogue + reviewed overrides<br>Astro → GitHub Pages</p></li>
<li><h4>Browser</h4><p>Three.js + R2 GLBs<br>Load on demand</p></li>
</ol>
<div class="pipeline-branches">
<div><h4>WebXR</h4><p>Same Three renderer<br>AR hit tests / VR room</p></div>
<div><h4>Apple Quick Look</h4><p>Temporary USDZ export<br>Separate native renderer</p></div>
</div>
<figcaption id="pipeline-caption">Source assets become a static website and browser views; immersive viewing branches into WebXR or Apple Quick Look.</figcaption>
</figure>'''


def blocks(body, section_id, sources=False):
    lines = body.strip().splitlines()
    out, i, table_no = [], 0, 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == '{{PIPELINE}}':
            out.append(PIPELINE)
            i += 1
        elif line.startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            out.append('<pre tabindex="0" aria-label="Code or formula"><code>' + html.escape('\n'.join(code)) + '</code></pre>')
            i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', c) for c in cells):
                    rows.append(cells)
                i += 1
            assert all(len(row) == len(rows[0]) for row in rows)
            table_no += 1
            out.append(f'<div class="table-wrap" role="region" aria-label="Table {table_no}: {html.escape(rows[0][0], quote=True)}" tabindex="0"><table>')
            out.append('<thead><tr>' + ''.join('<th scope="col">' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>')
            for row in rows[1:]:
                out.append('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>')
            out.append('</tbody></table></div>')
        elif line.startswith('## '):
            out.append('<h3>' + inline(line[3:]) + '</h3>')
            i += 1
        elif line.startswith('- '):
            out.append('<ul>')
            while i < len(lines) and lines[i].strip().startswith('- '):
                out.append('<li>' + inline(lines[i].strip()[2:]) + '</li>')
                i += 1
            out.append('</ul>')
        elif line.startswith('> '):
            out.append('<blockquote><p>' + inline(line[2:]) + '</p></blockquote>')
            i += 1
        else:
            paragraph = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('## ', '- ', '|', '```', '> ', '{{')):
                paragraph.append(lines[i].strip())
                i += 1
            text = ' '.join(paragraph)
            if sources and text.startswith('[R19 - Embedded report evidence]:'):
                text = text.replace('[R19 - Embedded report evidence]:', '', 1).strip()
                rendered = '<a id="ref-19" href="atrium-report-evidence.json">R19 - Embedded report evidence</a>: ' + inline(text)
            else:
                rendered = inline(text, sources)
            cls = ' class="reference-entry"' if sources else ''
            out.append(f'<p{cls}>' + rendered + '</p>')
    return '\n'.join(out)


toc = '<ol>' + ''.join(f'<li><a href="#{slug(s["title"])}">{html.escape(s["title"])}</a></li>' for s in SECTIONS) + '</ol>'
chapters = []
for index, section in enumerate(SECTIONS, 1):
    key = slug(section['title'])
    chapters.append(f'''<section class="report-section" id="{key}" aria-labelledby="{key}-title">
<header class="section-heading"><p class="section-number">{index:02d} / PDF page {index + 1}</p>
<h2 id="{key}-title">{html.escape(section['title'])}</h2></header>
{blocks(section['body'], key, sources=index == len(SECTIONS))}
</section>''')

document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="The full AI-written Atrium engineering report: architecture, 3D models, AR/VR, physical size, lighting and testing evidence.">
<meta name="theme-color" content="#132438">
<meta name="author" content="OpenAI Codex (AI)">
<title>Atrium technical report — Pipelines, physical size and immersive viewing</title>
<link rel="canonical" href="{SITE}">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="styles.css">
</head>
<body id="top">
<a class="skip-link" href="#report">Skip to report</a>
<header class="site-header"><a class="brand" href="{SITE}">Atrium <span>Technical report</span></a>
<nav class="header-links" aria-label="Related links"><a href="https://atrium.earth/">Visit Atrium ↗</a><a href="{REPO}">GitHub ↗</a></nav></header>
<div class="report-layout">
<aside class="toc"><nav aria-label="Contents"><p class="toc-label">In this report</p>{toc}
<a class="pdf-link" href="atrium-technical-report.pdf" download>Download 14-page PDF ↓</a></nav></aside>
<main id="report">
<header class="report-cover">
<p class="eyebrow">Engineering report · AI-written</p>
<h1>Pipelines, physical size and immersive viewing</h1>
<p class="lede">A source-based technical account of Atrium.Earth: what changed after the 424-work collection, how the implementation works, and where its evidence stops.</p>
<p class="cover-meta"><time datetime="2026-09-13">13 September 2026</time> · Full HTML edition of the 14-page report</p>
<div class="cover-actions"><a class="button button-primary" href="#what-changed-after-424-works">Read the report ↓</a><a class="button button-secondary" href="atrium-technical-report.pdf" download>Download PDF</a></div>
<div class="metrics"><div><strong>1,046</strong><span>Public works</span><small>424 at the comparison baseline</small></div><div><strong>622</strong><span>Net new works</span><small>627 added; 5 withheld later</small></div><div><strong>248</strong><span>Strict size references</span><small>798 unverified default displays</small></div></div>
<p class="disclosure"><strong>Authorship &amp; method.</strong> Written by OpenAI Codex, an AI assistant, at the project creator’s request. This is AI-authored technical documentation, not the creator’s personal account or an independent external audit. It is based on repository inspection, source records, deployment history and recorded automated checks.</p>
<p class="disclosure">The project creator has <strong>not personally tested the VR experience in a headset</strong>. Browser tests and simulated WebXR sessions do not establish headset compatibility, tracking quality or physical placement accuracy.</p>
<p class="cover-meta">Release snapshot: <a href="https://github.com/never-nude/atrium.earth/tree/541669e476adc7e2747b729cc73fd1efe0194b58">541669e</a>, published and checked on atrium.earth. All 1,046 works offer AR/VR: 248 reviewed size references and 798 explicitly unverified default display sizes. Native lighting follows the correction in c66d124.</p>
<p class="cover-meta">Page references in the text refer to the PDF. <a href="atrium-report-evidence.json" download>Download its evidence index (JSON)</a>.</p>
<details class="mobile-contents"><summary>Contents · 13 chapters</summary><nav aria-label="Contents on small screens">{toc}</nav></details>
</header>
<article aria-label="Full technical report">{''.join(chapters)}</article>
<footer class="report-footer"><p>Written by OpenAI Codex (AI) · Snapshot: 13 September 2026</p><p><a href="atrium-technical-report.pdf">14-page PDF</a> · <a href="atrium-report-evidence.json">Evidence index</a> · <a href="{REPO}">Repository</a> · <a href="#top">Back to top ↑</a></p></footer>
</main></div>
</body></html>
'''
(ROOT / 'index.html').write_text(document, encoding='utf-8')
print(f'Wrote index.html: {len(SECTIONS)} chapters, {len(document.encode())} bytes')
