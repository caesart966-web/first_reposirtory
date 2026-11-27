"""Очистка служебных свойств выдаваемых файлов от следов библиотек, которыми они собраны
(python-pptx, python-docx, openpyxl, ezdxf, matplotlib): свойства документа Office, метаданные PDF,
текстовые блоки PNG, служебные записи DXF. Содержимое файлов не меняется.

    python3 clean_meta.py <файл или папка> [...]

В архивах .zip очищаются документы (pptx, docx, xlsx, pdf, dxf); вложенные архивы, модели и текстуры
не трогаются — их подписывает ЭП заявитель.
"""
import datetime as dt
import io
import os
import re
import sys
import tempfile
import zipfile

LIBS = re.compile(r'(?i)python-pptx|python-docx|openpyxl|ezdxf|matplotlib|steve canny|generated (using|by)')
NOW = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _core(xml, title=None):
    def sub(tag, val, s):
        return re.sub(r'<%s(\s[^>]*)?>.*?</%s>|<%s(\s[^>]*)?/>' % (tag, tag, tag),
                      lambda m: '<%s%s>%s</%s>' % (tag, (m.group(1) or m.group(2) or ''), val, tag), s, flags=re.S)
    for tag in ('dc:creator', 'cp:lastModifiedBy', 'dc:description'):
        m = re.search(r'<%s(?:\s[^>]*)?>(.*?)</%s>' % (tag, tag), xml, flags=re.S)
        if m and LIBS.search(m.group(1)):
            xml = sub(tag, '', xml)
    if re.search(r'<dcterms:created[^>]*>2013-', xml):        # дата шаблона библиотеки
        xml = re.sub(r'(<dcterms:created[^>]*>)[^<]*', r'\g<1>' + NOW, xml)
        xml = re.sub(r'(<dcterms:modified[^>]*>)[^<]*', r'\g<1>' + NOW, xml)
    if title and re.search(r'<dc:title\s*/>|<dc:title>\s*</dc:title>', xml):
        xml = re.sub(r'<dc:title\s*/>|<dc:title>\s*</dc:title>', '<dc:title>%s</dc:title>' % title, xml)
    return xml


def _app(xml, n_slides=None):
    xml = re.sub(r'<Application>[^<]*(Openpyxl|Macintosh)[^<]*</Application>', '<Application></Application>', xml,
                 flags=re.I)
    xml = re.sub(r'<AppVersion>[^<]*</AppVersion>', '', xml) if 'Openpyxl' in xml else xml
    if n_slides is not None:
        xml = re.sub(r'<Slides>\d+</Slides>', '<Slides>%d</Slides>' % n_slides, xml)
        xml = xml.replace('On-screen Show (4:3)', 'Произвольный')
    return xml


def clean_office(path, title=None):
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    n_slides = len([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)]) if path.endswith('.pptx') \
        else None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'docProps/core.xml':
                data = _core(data.decode('utf-8'), title).encode('utf-8')
            elif it.filename == 'docProps/app.xml':
                data = _app(data.decode('utf-8'), n_slides).encode('utf-8')
            zout.writestr(it, data)
    zin.close()
    open(path, 'wb').write(buf.getvalue())


def clean_pdf(path):
    import pikepdf
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        changed = False
        for k in list(pdf.docinfo.keys()):
            if LIBS.search(str(pdf.docinfo[k])):
                del pdf.docinfo[k]
                changed = True
        if '/Metadata' in pdf.Root:
            raw = pdf.Root.Metadata.read_bytes().decode('utf-8', 'replace')
            if LIBS.search(raw):
                raw = re.sub(r'<([\w:]+)>[^<]*(python-docx|python-pptx|openpyxl|ezdxf|matplotlib)[^<]*</\1>',
                             r'<\1></\1>', raw, flags=re.I)
                raw = re.sub(r'<rdf:li[^>]*>[^<]*(python-docx|python-pptx|openpyxl)[^<]*</rdf:li>', '', raw,
                             flags=re.I)
                pdf.Root.Metadata = pdf.make_stream(raw.encode('utf-8'))
                changed = True
        if changed:
            pdf.save(path)


def clean_png(path):
    from PIL import Image
    im = Image.open(path)
    if any(LIBS.search(str(v)) for v in im.info.values() if isinstance(v, (str, bytes))) or 'Software' in im.info:
        im.load()
        kw = {'dpi': im.info['dpi']} if 'dpi' in im.info else {}
        im.save(path, **kw)


def clean_dxf_doc(doc):
    """Убрать служебные записи ezdxf из документа перед сохранением."""
    doc._update_ezdxf_metadata = lambda: None
    doc._create_appids = lambda: None
    meta = doc.rootdict.get('EZDXF_META')
    if meta is not None:
        doc.rootdict.discard('EZDXF_META')
        doc.objects.delete_entity(meta)
    doc.header['$LASTSAVEDBY'] = ''
    if str(doc.header.get('$DIMSTYLE', '')).upper().startswith('EZ'):
        doc.header['$DIMSTYLE'] = 'Standard'
    msp_styles = {e.dxf.get('dimstyle') for lay in doc.layouts for e in lay if e.dxf.hasattr('dimstyle')}
    for ds in list(doc.dimstyles):
        nm = ds.dxf.name
        if nm.upper().startswith('EZ') and nm not in msp_styles:
            doc.dimstyles.remove(nm)
    used = any(e.has_xdata('EZDXF') for lay in doc.layouts for e in lay if hasattr(e, 'has_xdata'))
    if 'EZDXF' in doc.appids and not used:
        doc.appids.remove('EZDXF')
    return doc


def save_dxf(doc, path):
    clean_dxf_doc(doc)
    doc.saveas(path)


def clean_dxf(path):
    import ezdxf
    doc = ezdxf.readfile(path)
    save_dxf(doc, path)


def clean_zip(path):
    tmp = tempfile.mkdtemp()
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for k, it in enumerate(zin.infolist()):
            data = zin.read(it.filename)
            ext = it.filename.lower().rsplit('.', 1)[-1]
            # модели и вложенные архивы не трогаем: их подписывает ЭП заявитель
            if not it.is_dir() and ext in ('pptx', 'docx', 'xlsx', 'pdf', 'dxf'):
                f = os.path.join(tmp, '%d.%s' % (k, ext))
                open(f, 'wb').write(data)
                clean(f, os.path.splitext(os.path.basename(it.filename))[0])
                data = open(f, 'rb').read()
            zout.writestr(it, data)
    open(path, 'wb').write(buf.getvalue())


def recalc_xlsx(path):
    """Сохранить в xlsx вычисленные значения формул (openpyxl пишет формулы без значений, и программы
    предпросмотра показывают пустые итоги): пересчёт в LibreOffice без интерфейса, затем очистка свойств."""
    import shutil
    import subprocess
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, 'in.xlsx')
    shutil.copyfile(path, src)
    subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'xlsx:Calc MS Excel 2007 XML',
                    '--outdir', os.path.join(tmp, 'out'), src], check=True, capture_output=True, timeout=180)
    out = os.path.join(tmp, 'out', 'in.xlsx')
    zin = zipfile.ZipFile(out)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'docProps/app.xml':
                data = re.sub(rb'<Application>[^<]*</Application>', b'<Application></Application>', data)
            if it.filename == 'docProps/core.xml':
                data = data.replace(b'<dc:language>en-US</dc:language>', b'<dc:language>ru-RU</dc:language>')
            zout.writestr(it, data)
    zin.close()
    open(path, 'wb').write(buf.getvalue())
    shutil.rmtree(tmp, ignore_errors=True)
    clean_office(path, os.path.splitext(os.path.basename(path))[0])


def clean(path, title=None):
    ext = path.lower().rsplit('.', 1)[-1]
    if ext in ('pptx', 'docx', 'xlsx'):
        clean_office(path, title or os.path.splitext(os.path.basename(path))[0])
    elif ext == 'pdf':
        clean_pdf(path)
    elif ext == 'png':
        clean_png(path)
    elif ext == 'dxf':
        clean_dxf(path)
    elif ext == 'zip':
        clean_zip(path)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for f in files:
                    clean(os.path.join(root, f))
        else:
            clean(a)
