"""Свойства выпускаемых файлов: название документа и организация вместо служебных отметок библиотек."""
import os
import pymupdf as fitz

ORG = 'ООО «Технология»'


def clean_pdf(path, title):
    doc = fitz.open(path)
    doc.set_metadata({'title': title, 'author': ORG, 'subject': '', 'keywords': '',
                      'creator': '', 'producer': '', 'creationDate': '', 'modDate': ''})
    doc.del_xml_metadata()
    cat = doc.pdf_catalog()     # после склейки листов в каталоге остаётся свой /Info с именем библиотеки
    if doc.xref_get_key(cat, 'Info')[0] != 'null':
        doc.xref_set_key(cat, 'Info', 'null')
    tmp = path + '.tmp'
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    raw = open(tmp, 'rb').read()
    head, sep, rest = raw[:200].partition(b'% Written by MuPDF')
    if sep:     # комментарий в заголовке — пробелами той же длины, смещения в xref не меняются
        line = sep + rest.split(b'\n', 1)[0]
        raw = raw.replace(line, b'%' + b' ' * (len(line) - 1), 1)
        open(tmp, 'wb').write(raw)
    os.replace(tmp, path)


def clean_dxf(doc):
    """Перед doc.saveas(): без служебных записей библиотеки, неиспользуемых стилей и с читаемыми именами стилей АР."""
    doc.header['$LASTSAVEDBY'] = ''
    doc.header['$DIMSTYLE'] = 'ПТ100' if 'ПТ100' in doc.dimstyles else 'Standard'
    doc.header['$TEXTSTYLE'] = 'ПТ' if 'ПТ' in doc.styles else 'Standard'
    doc._update_ezdxf_metadata = lambda: None
    doc._create_appids = lambda: doc._create_appid_if_not_exist('HATCHBACKGROUNDCOLOR', 0)
    meta = doc.rootdict.get('EZDXF_META')
    if meta is not None:
        doc.rootdict.discard('EZDXF_META')
        if meta.is_alive:
            doc.objects.delete_entity(meta)     # вместе с записями, которыми словарь владеет
    for o in list(doc.objects):     # словари метаданных без владельца (если файл уже сохранялся)
        if o.is_alive and o.dxftype() == 'DICTIONARY' and ('CREATED_BY_EZDXF' in o or 'WRITTEN_BY_EZDXF' in o):
            doc.objects.delete_entity(o)
    # стили АР с испорченными при конвертации именами (кодировка) — переименовать
    def broken(n):
        return any(0xdc80 <= ord(c) <= 0xdcff for c in n) or 'РЎ' in n or 'Р\xa0' in n
    ren = {}
    for st in list(doc.styles):
        n = st.dxf.name
        if broken(n):
            new = f'АР_текст_{len(ren) + 1}'
            ns = doc.styles.new(new, dxfattribs={'font': st.dxf.font, 'width': st.dxf.get('width', 1),
                                                 'height': st.dxf.get('height', 0), 'oblique': st.dxf.get('oblique', 0)})
            ren[n] = new
    used_st, used_ds, xdata = set(), set(), False
    for layout in doc.blocks:
        for e in layout:
            if e.dxf.hasattr('style'):
                if e.dxf.style in ren:
                    e.dxf.style = ren[e.dxf.style]
                used_st.add(e.dxf.style)
            if e.dxftype() == 'DIMENSION':
                used_ds.add(e.dxf.dimstyle)
            if e.xdata and 'EZDXF' in e.xdata.data:
                xdata = True
    for ds in list(doc.dimstyles):
        if ds.dxf.name not in used_ds | {'Standard', 'ПТ100'}:
            doc.dimstyles.remove(ds.dxf.name)
    keep = used_st | {'Standard', 'ПТ', 'ПТ_загл'} | {ds.dxf.dimtxsty for ds in doc.dimstyles if ds.dxf.hasattr('dimtxsty')}
    for st in list(doc.styles):
        if st.dxf.name and st.dxf.name not in keep and not st.is_shape_file:
            doc.styles.remove(st.dxf.name)
    if 'EZDXF' in doc.appids and not xdata:
        doc.appids.remove('EZDXF')


def clean_xlsx(wb, title):
    p = wb.properties
    p.creator = ORG
    p.lastModifiedBy = ORG
    p.title = title
