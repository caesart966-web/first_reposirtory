#!/usr/bin/env bash
# Монтаж видео «как пройти в офис» для карточек Яндекса и 2ГИС (28.10.2026).
# Исходник — IMG_9086.MOV от заказчика (релиз `video` репозитория, 3:07,
# 720×1280): табличка «Социалистическая 74» → БЦ «Купеческий Двор» → лифт →
# 4 этаж → дверь офиса. Итог ~1:08: ожидание у лифта (46–113 с) и поездка
# в кабине (123–156 с) вырезаны плавными переходами, остальное ×1,25,
# поворот из лифта ×0,9. Вырезано и отражение снимающего в зеркале кабины.
#   bash scripts/route-video.sh IMG_9086.MOV kak-proyti-v-ofis.mp4
set -euo pipefail
# Лицо прохожего у двери офисов (исходник 170,2–171,7 с) размыто тремя пятнами
# по ходу его движения влево.
IN=$1; OUT=$2
SP=1.25          # общее ускорение
XF=0.8           # длительность плавного перехода, с
# Куски исходника (секунды): подход к лифту; посадка в лифт; кабина → 4 этаж → офис.
A0=0;     A1=46
B0=113.8; B1=123.2      # до 123.4 — дальше в зеркале кабины отражается снимающий
C0=156;   C1=158.5      # кабина, двери открываются
D0=158.5; D1=160.3      # поворот из лифта — медленнее, иначе дёргается
E0=160.3; E1=187.5      # «4 этаж», коридор, дверь офиса
LA=$(echo "($A1-$A0)/$SP" | bc -l); LB=$(echo "($B1-$B0)/$SP" | bc -l)
LC=$(echo "($C1-$C0)/$SP + ($D1-$D0)/0.9 + ($E1-$E0)/$SP" | bc -l)
O1=$(echo "$LA-$XF" | bc -l); O2=$(echo "$LA+$LB-2*$XF" | bc -l)
TOTAL=$(echo "$LA+$LB+$LC-2*$XF" | bc -l); FO=$(echo "$TOTAL-0.8" | bc -l)
ffmpeg -v error -y -i "$IN" -filter_complex "
[0:v]split=4[base][c1][c2][c3];
[c1]crop=260:320:120:300,boxblur=24:3[b1];
[c2]crop=240:320:60:300,boxblur=24:3[b2];
[c3]crop=240:360:0:280,boxblur=24:3[b3];
[base][b1]overlay=120:300:enable='between(t,170.2,170.7)'[o1];
[o1][b2]overlay=60:300:enable='between(t,170.7,170.95)'[o2];
[o2][b3]overlay=0:280:enable='between(t,170.95,171.75)'[v];
[v]split=5[va][vb][vc][vd][ve];
[va]trim=$A0:$A1,setpts=(PTS-STARTPTS)/$SP[A];
[vb]trim=$B0:$B1,setpts=(PTS-STARTPTS)/$SP[B];
[vc]trim=$C0:$C1,setpts=(PTS-STARTPTS)/$SP[C];
[vd]trim=$D0:$D1,setpts=(PTS-STARTPTS)/0.9[D];
[ve]trim=$E0:$E1,setpts=(PTS-STARTPTS)/$SP[E];
[C][D][E]concat=n=3:v=1:a=0,fps=30[CE];
[A]fps=30[A2];[B]fps=30[B2];
[A2][B2]xfade=transition=fade:duration=$XF:offset=$O1[AB];
[AB][CE]xfade=transition=fade:duration=$XF:offset=$O2,fade=t=in:d=0.4,fade=t=out:st=$FO:d=0.8,format=yuv420p[vout];
[0:a]asplit=5[aa][ab][ac][ad][ae];
[aa]atrim=$A0:$A1,asetpts=PTS-STARTPTS,atempo=$SP[a1];
[ab]atrim=$B0:$B1,asetpts=PTS-STARTPTS,atempo=$SP[a2];
[ac]atrim=$C0:$C1,asetpts=PTS-STARTPTS,atempo=$SP[a3];
[ad]atrim=$D0:$D1,asetpts=PTS-STARTPTS,atempo=0.9[a4];
[ae]atrim=$E0:$E1,asetpts=PTS-STARTPTS,atempo=$SP[a5];
[a3][a4][a5]concat=n=3:v=0:a=1[ace];
[a1][a2]acrossfade=d=$XF[aab];
[aab][ace]acrossfade=d=$XF,afade=t=in:d=0.4,afade=t=out:st=$FO:d=0.8[aout]" \
  -map "[vout]" -map "[aout]" -c:v libx264 -preset slow -crf 20 -profile:v high -r 30 \
  -c:a aac -b:a 128k -ar 44100 -movflags +faststart "$OUT"
echo "готово: $OUT, ожидаемая длина ${TOTAL:0:5} с"
