"""Подложка АР из экспорта Revit: модель в мм, переносится в блок и вставляется со сдвигом,
чтобы пересечение осей 1/А стало точкой (0, 0). Слои подложки — серые, тонкие (ГОСТ 21.602, подложка)."""
from ezdxf import recover
from ezdxf.addons import importer

OX, OY = 2168.0, 4673.0                     # оси 1/А в координатах экспорта (дом и баня одинаково)
DROP_BLOCK = ('man_walking', 'Машиноместо', 'Антураж', 'DCS-Revit')   # люди, машины, антураж — не нужны
FAINT = ('I-FURN', 'M-EQPM', 'P-SANR-FIXT', 'G-IMPT', 'A-FLOR', 'A-FLOR-PATT', 'S-STRS', 'A-DETL', 'A-DETL-GENF',
         'A-GENM', 'DCS')


def add_underlay(doc, src, block_name, keep_dims=True):
    sdoc, _ = recover.readfile(src)
    smsp = sdoc.modelspace()
    ents = []
    for e in smsp:
        if e.dxftype() == 'INSERT' and any(k in e.dxf.name for k in DROP_BLOCK):
            continue
        if e.dxftype() == 'DIMENSION' and not keep_dims:
            continue
        ents.append(e)
    imp = importer.Importer(sdoc, doc)
    blk = doc.blocks.new(block_name)
    imp.import_entities(ents, blk)
    imp.finalize()
    # слои подложки: префикс «АР», серый цвет, тонкие линии
    for lay in list(doc.layers):
        n = lay.dxf.name
        if n.startswith(('A-', 'S-', 'G-', 'I-', 'M-', 'P-', 'DCS')) or n == '0' and False:
            lay.color = 9 if n.startswith(FAINT) else 8
            lay.dxf.lineweight = 13
    for n in ('S-GRID-IDEN', 'A-ANNO-DIMS', 'G-ANNO-DIMS'):        # марки осей и размеры Revit — далеко от плана
        if n in doc.layers:
            doc.layers.get(n).off()
            doc.layers.get(n).freeze()
    return blk.name


def insert_underlay(msp, block_name, layer='АР_подложка'):
    return msp.add_blockref(block_name, (-OX, -OY), dxfattribs={'layer': layer})
