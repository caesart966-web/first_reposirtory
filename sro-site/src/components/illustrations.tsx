// Фирменные SVG-иллюстрации сайта: тонкая линейная графика, цвет наследуется
// от родителя через currentColor. Без растровых изображений и внешних запросов.
type Props = { className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }

export function CitySkyline({ className = '' }: Props) {
  return (
    <svg className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 260" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"><g strokeWidth="2"><path d="M24 242 H1176"/><path d="M60 242 V150 M160 242 V150 M56 150 H164 M56 131 H164 M56 112 H164 M60 150 V112 M93 150 V112 M127 150 V112 M160 150 V112 M60 180 H160 M60 210 H160"/><path d="M198 242 V78 H236 V60 H282 V242"/><path d="M338 242 V110 H438 V242 M338 122 H438"/><path d="M470 242 V58 M486 242 V58 M470 58 L478 28 L486 58 M396 52 H764 M396 63 H764 M396 52 V63 M764 52 V63 M640 70 V146 M612 176 H668"/><path d="M600 242 V190 M638 242 V190 M676 242 V190 M714 242 V190 M594 190 H720 M594 216 H720"/><path d="M788 242 V96 C788 82 799 75 814 75 H842 C858 75 866 84 866 98 V242 Z" fill="currentColor" fillOpacity="0.05"/><path d="M912 242 V160 M1016 242 V160 M908 160 H1020 M908 139 H1020 M908 118 H1020 M912 160 V118 M947 160 V118 M982 160 V118 M1016 160 V118 M912 201 H1016"/><path d="M1058 242 V186 H1152 V242 M1058 214 H1152"/><path d="M312 242 V224 M890 242 V226 M1044 242 V228"/><circle cx="312" cy="209" r="15"/><circle cx="890" cy="212" r="14"/><circle cx="1044" cy="216" r="12"/><circle cx="1092" cy="84" r="28" fill="currentColor" fillOpacity="0.06"/><path d="M398 63 H424 V84 H398 Z" fill="currentColor" fillOpacity="0.1"/></g><g strokeWidth="1.5"><path d="M470 242 L486 212 L470 182 L486 152 L470 122 L486 92 L470 62"/><path d="M396 63 L412 52 L428 63 L444 52 L460 63 L476 52 L492 63 L508 52 L524 63 L540 52 L556 63 L572 52 L588 63 L604 52 L620 63 L636 52 L652 63 L668 52 L684 63 L700 52 L716 63 L732 52 L748 63 L764 52"/><path d="M478 28 L404 52 M478 28 L600 52 M478 28 L744 52"/><path d="M630 63 H650 V70 H630 Z M488 63 V78 H506 V63"/><circle cx="640" cy="150.5" r="4.5"/><path d="M640 155 L618 176 M640 155 L662 176"/><path d="M85 158 V172 M110 158 V172 M135 158 V172 M85 188 V202 M110 188 V202 M135 188 V202 M85 218 V232 M110 218 V232 M135 218 V232 M72 112 V103 M98 112 V103 M124 112 V103 M148 112 V103"/><path d="M248 72 V228 M259 72 V228 M270 72 V228 M204 100 H230 M204 130 H230 M204 160 H230 M204 190 H230 M204 220 H230 M259 60 V42"/><circle cx="259" cy="38" r="2.5"/><path d="M371 130 V232 M404 130 V232 M348 158 H428 M348 186 H428 M348 214 H428"/><path d="M612 190 V181 M650 190 V181 M688 190 V181"/><path d="M810 90 V228 M836 90 V228"/><path d="M938 170 V186 M964 170 V186 M990 170 V186 M938 211 V227 M964 211 V227 M990 211 V227 M925 118 V109 M960 118 V109 M995 118 V109"/><path d="M1082 194 V206 M1105 194 V206 M1128 194 V206 M1096 242 V222 H1114 V242"/><path d="M500 226 H584 M510 226 V242 M534 226 V242 M558 226 V242 M578 226 V242"/><path d="M34 210 L22 242 M34 210 L46 242 M34 210 V242 M25 203 H43"/><circle cx="34" cy="203" r="5.5"/><path d="M146 78 Q153 70 160 77 Q167 71 174 78 M924 56 Q930 49 936 55 Q942 50 948 56 M1124 100 Q1130 93 1136 99 Q1142 94 1148 100"/><path d="M170 252 H300 M652 252 H790 M986 252 H1072"/></g></svg>
  )
}

export function BlueprintGrid({ className = '' }: Props) {
  return (
    <svg className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"><defs><radialGradient id="blueprintgrid-sro-fade" cx="46%" cy="44%" r="70%"><stop offset="0" stopColor="#fff"/><stop offset="0.65" stopColor="#fff" stopOpacity="0.6"/><stop offset="1" stopColor="#fff" stopOpacity="0"/></radialGradient><mask id="blueprintgrid-sro-gridmask"><rect width="800" height="600" fill="url(#blueprintgrid-sro-fade)"/></mask></defs><g mask="url(#blueprintgrid-sro-gridmask)" strokeWidth="1.5"><path strokeOpacity="0.07" d="M40 0V600M80 0V600M120 0V600M160 0V600M200 0V600M240 0V600M280 0V600M320 0V600M360 0V600M400 0V600M440 0V600M480 0V600M520 0V600M560 0V600M600 0V600M640 0V600M680 0V600M720 0V600M760 0V600M0 40H800M0 80H800M0 120H800M0 160H800M0 200H800M0 240H800M0 280H800M0 320H800M0 360H800M0 400H800M0 440H800M0 480H800M0 520H800M0 560H800"/><path strokeOpacity="0.11" d="M200 0V600M400 0V600M600 0V600M0 200H800M0 400H800"/></g><g strokeWidth="1.5" strokeOpacity="0.3" strokeDasharray="22 7 3 7"><path d="M170 220H684M200 132V520M430 420H736"/></g><g strokeWidth="2" strokeOpacity="0.5"><circle cx="704" cy="220" r="20"/><circle cx="200" cy="110" r="20"/><circle cx="756" cy="420" r="20"/></g><g fill="currentColor" stroke="none" fillOpacity="0.05"><path d="M192 212H360V228H208V460H192Z"/><path d="M440 212H560V228H440Z"/><path d="M460 412H560V428H460Z"/><path d="M620 412H680V428H620Z"/></g><path fill="currentColor" stroke="none" fillOpacity="0.04" d="M360 228H440A80 80 0 0 1 360 308Z"/><path fill="currentColor" stroke="none" fillOpacity="0.04" d="M620 412H560A60 60 0 0 1 620 352Z"/><g strokeWidth="2" strokeOpacity="0.55" fill="currentColor" fillOpacity="0.08"><rect x="187" y="207" width="26" height="26" rx="2"/><rect x="448" y="408" width="24" height="24" rx="2"/></g><g strokeWidth="2.2" strokeOpacity="0.75"><path d="M560 212H192V460"/><path d="M560 228H440M360 228H208V460"/><path d="M560 212V228M192 460H208M360 212V228M440 212V228"/><path d="M460 412H560M620 412H680M460 428H560M620 428H680M460 412V428M680 412V428M560 412V428M620 412V428"/></g><g strokeWidth="2" strokeOpacity="0.55"><path d="M360 228V308M440 228A80 80 0 0 1 360 308"/><path d="M620 412V352M560 412A60 60 0 0 1 620 352"/></g><g strokeWidth="1.5" strokeOpacity="0.5"><path d="M192 200V150M360 200V150M440 200V150M560 200V150M176 160H576"/><path d="M204 155L192 160L204 165M548 155L560 160L548 165"/><path d="M353 167L367 153M433 167L447 153"/><path d="M180 212H130M180 460H130M140 198V474"/><path d="M135 224L140 212L145 224M135 448L140 460L145 448"/><path d="M460 436V496M680 436V496M446 488H694"/><path d="M472 483L460 488L472 493M668 483L680 488L668 493"/></g><g strokeWidth="1.5" strokeOpacity="0.35"><path d="M630 120H650M640 110V130M94 508H114M104 498V518M442 72H462M452 62V82"/></g></svg>
  )
}

// Знак в шапке: весы Фемиды. Пропорции сняты с той же гравюры Раймонди, что
// стоит фоном страницы (размах коромысла принят за 1: чаша 0,50, подвес 0,48,
// подъём центра 0,07) — но не обводка: штрих гравюры составляет около 1%
// ширины объекта, а значку на 20-24px нужно примерно 5%, поэтому линии здесь
// собственные. Пропорция бокса 46x26 — родная для весов, отсюда и широкий
// плоский силуэт.
export function ScalesMark({ className = '' }: Props) {
  return (
    <svg
      className={className}
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 46 26"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M23 1.8V5" />
      <path d="M8.98 7 23 5l14.04 2" />
      <path d="M8.98 7 1.99 21M8.98 7l6.99 14" />
      <path d="M1.99 21a8.9 8.9 0 0 0 13.98 0" />
      <path d="M1.99 21h13.98" />
      <path d="M37.02 7 30.03 21M37.02 7l6.99 14" />
      <path d="M30.03 21a8.9 8.9 0 0 0 13.98 0" />
      <path d="M30.03 21h13.98" />
    </svg>
  )
}
