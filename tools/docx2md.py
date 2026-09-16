import sys, zipfile, re, os
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MONO_RE = re.compile(r'Courier|Consolas|Mono|Menlo|Fira|JetBrains|Source Code', re.I)
CALLOUT_RE = re.compile(u'^\\s*(⚠|ℹ|✅|\U0001F534|\U0001F4CB|⚖|\U0001F527|✔|❗|\U0001F4A1|\U0001F7E0|\U0001F7E1)')


def para_text(p):
    out = []
    for node in p.iter():
        if node.tag == W + 't':
            out.append(node.text or '')
        elif node.tag == W + 'tab':
            out.append('\t')
        elif node.tag == W + 'br':
            out.append('\n')
    return ''.join(out)


def para_style(p):
    ppr = p.find(W + 'pPr')
    if ppr is None:
        return None, None
    ps = ppr.find(W + 'pStyle')
    style = ps.get(W + 'val') if ps is not None else None
    numpr = ppr.find(W + 'numPr')
    ilvl = None
    if numpr is not None:
        lvl = numpr.find(W + 'ilvl')
        ilvl = int(lvl.get(W + 'val')) if lvl is not None else 0
    return style, ilvl


def runs_info(p):
    n = mono = 0
    all_bold = True
    for r in p.findall(W + 'r'):
        t = ''.join((x.text or '') for x in r.iter(W + 't'))
        if not t.strip():
            continue
        n += 1
        rpr = r.find(W + 'rPr')
        rf = rpr.find(W + 'rFonts') if rpr is not None else None
        if rf is not None and any(MONO_RE.search(v or '') for v in rf.attrib.values()):
            mono += 1
        if rpr is None or rpr.find(W + 'b') is None:
            all_bold = False
    return n, mono, (all_bold and n > 0)


def is_mono_para(p, mono_styles):
    style, _ = para_style(p)
    if style in mono_styles:
        return True
    n, mono, _ = runs_info(p)
    return n > 0 and mono / n >= 0.6


def guess_lang(text):
    t = text
    if re.search(r'\b(CREATE TABLE|SELECT |INSERT INTO|UPDATE \w+ SET|ALTER TABLE|CREATE INDEX|CREATE UNIQUE INDEX|BEGIN TRANSACTION|CREATE OR REPLACE FUNCTION)\b', t):
        return 'sql'
    if re.search(r'^\s*(def |import |from \w+ import|class \w+|async def )', t, re.M) or re.search(r'\bredis\.|\blog\.(info|warning|warn)\(', t):
        return 'python'
    if re.search(r'^\s*[\{\[]', t) and re.search(r'"\w+"\s*:', t):
        return 'json'
    if re.search(r'^\s*(local |if .* then|redis\.call)', t, re.M):
        return 'lua'
    if re.search(r'^\s*\w[\w_]*:\s*(\S|$)', t, re.M) and not re.search(r'[;{}]', t):
        return 'yaml'
    return 'text'


def flush_code(buf, out):
    if not buf:
        return
    text = '\n'.join(buf).strip('\n')
    lines = text.split('\n')
    indents = [len(l) - len(l.lstrip(' ')) for l in lines if l.strip()]
    common = min(indents) if indents else 0
    lines = [l[common:] if l.strip() else '' for l in lines]
    text = '\n'.join(lines)
    fence = '````' if '```' in text else '```'
    out.append(fence + guess_lang(text))
    out.append(text)
    out.append(fence)
    out.append('')
    buf.clear()


def render_paragraph(p, out, code_buf, mono_styles, shift):
    style, ilvl = para_style(p)
    text = para_text(p).rstrip()
    m = re.match(r'Heading(\d)', style or '')
    if m:
        flush_code(code_buf, out)
        level = min(int(m.group(1)) + shift, 6)
        out.append('')
        out.append('#' * level + ' ' + text.strip())
        out.append('')
        return
    if style == 'Title':
        flush_code(code_buf, out)
        out.append('# ' + text.strip())
        out.append('')
        return
    if not text.strip():
        if code_buf:
            code_buf.append('')
        else:
            out.append('')
        return
    if is_mono_para(p, mono_styles):
        code_buf.append(text)
        return
    flush_code(code_buf, out)
    if ilvl is not None or (style and 'List' in style):
        indent = ilvl if ilvl is not None else (1 if (style and style.endswith('2')) else 0)
        out.append('  ' * indent + '- ' + text.strip())
        return
    n, mono, all_bold = runs_info(p)
    if style == 'Subtitle':
        out.append('_' + text.strip() + '_')
    elif all_bold and len(text) < 140 and '\n' not in text:
        out.append('**' + text.strip() + '**')
    else:
        out.append(text.replace('\n', '  \n'))


def cell_paras(tc):
    return [p for p in tc.iter(W + 'p')]


def render_table(tbl, out, mono_styles):
    rows = tbl.findall(W + 'tr')
    if not rows:
        return
    ncols = max(len(r.findall(W + 'tc')) for r in rows)
    if len(rows) == 1 and ncols == 1:
        tc = rows[0].findall(W + 'tc')[0]
        paras = cell_paras(tc)
        texts = [para_text(p).rstrip() for p in paras]
        nonempty = [t for t in texts if t.strip()]
        if not nonempty:
            return
        mono_count = sum(1 for p in paras if para_text(p).strip() and is_mono_para(p, mono_styles))
        first = nonempty[0]
        if mono_count / max(1, len(nonempty)) < 0.5:
            out.append('')
            for t in texts:
                if t.strip():
                    for line in t.split('\n'):
                        out.append('> ' + line)
                else:
                    out.append('>')
            while out and out[-1] == '>':
                out.pop()
            out.append('')
        else:
            body = '\n'.join(texts).strip('\n')
            out.append('')
            fence = '````' if '```' in body else '```'
            out.append(fence + guess_lang(body))
            out.append(body)
            out.append(fence)
            out.append('')
        return
    out.append('')
    for i, tr in enumerate(rows):
        cells = []
        for tc in tr.findall(W + 'tc'):
            ps = [para_text(p).strip() for p in cell_paras(tc)]
            ps = [x for x in ps if x]
            ctext = '<br>'.join(ps)
            ctext = ctext.replace('\n', '<br>').replace('|', '\\|')
            cells.append(ctext)
        cells += [''] * (ncols - len(cells))
        out.append('| ' + ' | '.join(cells) + ' |')
        if i == 0:
            out.append('|' + '---|' * ncols)
    out.append('')


def convert(path, shift=0):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read('word/document.xml'))
    body = root.find(W + 'body')
    mono_styles = set()
    try:
        sx = ET.fromstring(z.read('word/styles.xml'))
        for s in sx.iter(W + 'style'):
            rpr = s.find(W + 'rPr')
            rf = rpr.find(W + 'rFonts') if rpr is not None else None
            if rf is not None and any(MONO_RE.search(v or '') for v in rf.attrib.values()):
                mono_styles.add(s.get(W + 'styleId'))
    except KeyError:
        pass
    out, code_buf = [], []
    for el in body:
        if el.tag == W + 'p':
            render_paragraph(el, out, code_buf, mono_styles, shift)
        elif el.tag == W + 'tbl':
            flush_code(code_buf, out)
            render_table(el, out, mono_styles)
        elif el.tag == W + 'sdt':
            content = el.find(W + 'sdtContent')
            if content is not None:
                for child in content:
                    if child.tag == W + 'p':
                        render_paragraph(child, out, code_buf, mono_styles, shift)
                    elif child.tag == W + 'tbl':
                        flush_code(code_buf, out)
                        render_table(child, out, mono_styles)
    flush_code(code_buf, out)
    text = '\n'.join(out)
    text = fix_toc(text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip('\n') + '\n'
    return text


def fix_toc(text):
    """Turn the manual 'Table of Contents' block (bold entry + indented summary lines) into a list."""
    lines = text.split('\n')
    out = []
    i = 0
    in_toc = False
    while i < len(lines):
        line = lines[i]
        if re.match(r'^#{1,6} Table of Contents\s*$', line):
            in_toc = True
            out.append(line)
            i += 1
            continue
        if in_toc:
            if line.startswith('#'):
                in_toc = False
                out.append(line)
                i += 1
                continue
            m = re.match(r'^\*\*\s*(\d+)\.\s*(.+?)\*\*\s*$', line)
            if m:
                entry = '- **%s. %s**' % (m.group(1), m.group(2).strip())
                j = i + 1
                extras = []
                while j < len(lines) and lines[j].strip() and not lines[j].startswith('#') and not re.match(r'^\*\*\s*\d+\.', lines[j]):
                    extras.append(re.sub(r'\s+', ' ', lines[j].strip()))
                    j += 1
                if extras:
                    entry += ' — ' + ' '.join(extras)
                out.append(entry)
                i = j
                continue
        out.append(line)
        i += 1
    return '\n'.join(out)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    shift = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    text = convert(src, shift)
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    h1 = len(re.findall(r'^# ', text, re.M))
    fences = text.count('```') // 2
    quotes = len(re.findall(r'^> ', text, re.M))
    print('%s -> %s: %d chars, H1=%d, code_blocks=%d, quote_lines=%d' % (os.path.basename(src), os.path.basename(dst), len(text), h1, fences, quotes))
