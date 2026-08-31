// Фирменные SVG-иллюстрации сайта: тонкая линейная графика, цвет наследуется
// от родителя через currentColor. Без растровых изображений и внешних запросов.
//
// Силуэт города (CitySkyline) отсюда удалён 30.08.2026: он стоял внизу тёмной
// секции заявки, а та перешла на фотографию в полную силу, и силуэт зданий
// оказался вторым рядом зданий в одной секции. Восстанавливается из истории,
// если фон вернётся к линейной графике.
type Props = { className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }

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
