"""fix_booklet.py ВХОД.pdf ВЫХОД.pdf — ТЭП и отметки буклета по итогам кадастрового инженера (17.09.2026).

Цифры меняются в самих операторах показа текста (pikepdf): тот же шрифт, кегль и место, без наложенных
заплаток. Цифры моноширинные, поэтому длина и выравнивание не меняются. Нужен pikepdf.
"""
import sys
import pikepdf
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from pdftext import walk, op_text  # noqa: E402

# (страница, старый текст -> новый) — замена внутри одного оператора показа текста
REPL = {
    2: [(' 1 235,0 ', ' 1 226,9 '), (' 12,31 ', ' 11,94 ')],   # пояснительная записка (общая 1 470,5 уже верная)
    4: [('1449,98', '1226,90')],                                                          # СПОЗУ, экспликация зданий
    9: [('+207,14', '+206,96')],                                                          # фасад Д-А, отметка +10,940
    17: [('1178,32', '1226,90'), ('1454,00', '1470,50'), ('206,11', '207,96'), ('12,310', '11,940'),
         ('4,6', '4,4'), ('1484,46', '1461,98')],                                        # ТЭП
}
EXPECT = {2: 2, 4: 1, 9: 1, 17: 7}          # сколько операторов должно измениться


def main(src, dst):
    pdf = pikepdf.open(src)
    for pno, reps in REPL.items():
        page = pdf.pages[pno - 1]
        n = 0

        def cb(ops, i, font):
            nonlocal n
            t = op_text(ops, i, font)
            hit = [(a, b) for a, b in reps if a in t]
            if not hit:
                return False
            operands, op = ops[i]
            for a, b in hit:
                assert len(a) == len(b)
                if str(op) == 'TJ':
                    arr = operands[0]
                    for k, x in enumerate(arr):
                        if isinstance(x, pikepdf.String) and a in font.decode(bytes(x)):
                            arr[k] = pikepdf.String(font.encode(font.decode(bytes(x)).replace(a, b)))
                            break
                    else:
                        raise RuntimeError('стр. %d: %r разбит между элементами TJ' % (pno, a))
                else:
                    operands[-1] = pikepdf.String(font.encode(t.replace(a, b)))
            ops[i] = pikepdf.ContentStreamInstruction(operands, op)
            n += 1
            print('стр. %d: %r -> %r' % (pno, t, op_text(ops, i, font)))
            return True

        ops, changed = walk(pdf, page.obj, page.obj.get('/Resources'), cb)
        if changed:
            page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
        assert n == EXPECT[pno], (pno, n)
    pdf.save(dst, deterministic_id=True)


if __name__ == '__main__':
    main(*sys.argv[1:3])
