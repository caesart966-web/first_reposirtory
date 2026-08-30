"""TCO-модель: ДВС vs электромобиль в таксопарке Сочи, горизонт 3 года.

Все суммы — тысячи рублей на один автомобиль, если не указано иное.
Источники и статус каждого допущения — в словаре ASSUMPTIONS.
"""

# ---------------------------------------------------------------- допущения
P = dict(
    km_year=90_000,          # пробег такси, км/год (250 км/сутки)
    years=3,

    # --- ДВС: Lada Vesta Comfort (в перечне Минпромторга для такси)
    ice_price=1_580,         # тыс. руб., РРЦ 2026
    ice_l100=9.5,            # л/100 км в такси-режиме (город + кондиционер)
    ice_fuel=69.0,           # руб./л, АИ-92, Сочи, август 2026
    ice_service_year=120,    # тыс. руб./год, ТО + ремонт при 90 тыс. км
    ice_residual=0.35,       # доля РРЦ через 3 года / 270 тыс. км

    # --- ЭМ: Evolute i-Joy (в перечне Минпромторга для такси)
    ev_price=2_775,          # тыс. руб., РРЦ 2026
    ev_subsidy=925,          # тыс. руб., льготный лизинг Минпромторга, 35% но не более
    ev_kwh100=20.0,          # кВт*ч/100 км в такси-режиме Сочи (WLTP 13,4 + климат/рельеф)
    ev_charge_loss=0.10,     # потери при быстрой зарядке
    ev_price_kwh=14.0,       # руб./кВт*ч, микс 60% свой AC (10) + 40% публичный DC (20)
    ev_service_year=50,      # тыс. руб./год, ТО + ремонт (в 2-3 раза ниже ДВС)
    ev_residual=0.22,        # доля РРЦ через 3 года / 270 тыс. км (деградация батареи)

    # --- инфраструктура и простой
    hub_capex=350,           # тыс. руб. на 1 авто (AC-посты + техприсоединение)
    hub_residual=0.40,       # остаточная стоимость хаба через 3 года из 5 лет службы
    revenue_year=2_160,      # тыс. руб./год, валовая выручка автомобиля
    downtime=0.03,           # доля линейного времени, теряемая на зарядку
)


def tco(p, subsidy=True, **over):
    q = dict(p); q.update(over)
    km = q['km_year'] * q['years']

    ice_fuel = q['ice_l100'] / 100 * q['ice_fuel'] * km / 1000
    ice_srv = q['ice_service_year'] * q['years']
    ice_net = q['ice_price'] - q['ice_price'] * q['ice_residual']
    ice = dict(capex=ice_net, energy=ice_fuel, service=ice_srv, downtime=0.0, hub=0.0)

    ev_paid = q['ev_price'] - (q['ev_subsidy'] if subsidy else 0)
    ev_energy = (q['ev_kwh100'] * (1 + q['ev_charge_loss'])) / 100 * q['ev_price_kwh'] * km / 1000
    ev_srv = q['ev_service_year'] * q['years']
    ev_net = ev_paid - q['ev_price'] * q['ev_residual']
    ev_down = q['revenue_year'] * q['years'] * q['downtime']
    ev_hub = q['hub_capex'] * (1 - q['hub_residual'])
    ev = dict(capex=ev_net, energy=ev_energy, service=ev_srv, downtime=ev_down, hub=ev_hub)

    ice['total'] = sum(ice.values())
    ev['total'] = sum(ev.values())
    return ice, ev, ice['total'] - ev['total']


def breakeven_km(p, subsidy=True, **over):
    """Пробег, на котором накопленные затраты сравниваются."""
    q = dict(p); q.update(over)
    ev_paid = q['ev_price'] - (q['ev_subsidy'] if subsidy else 0)
    fixed_gap = ((ev_paid - q['ev_price'] * q['ev_residual'])
                 - (q['ice_price'] - q['ice_price'] * q['ice_residual'])
                 + q['hub_capex'] * (1 - q['hub_residual']))          # тыс. руб.
    var_ice = q['ice_l100'] / 100 * q['ice_fuel'] + q['ice_service_year'] / q['km_year'] * 1000
    var_ev = ((q['ev_kwh100'] * (1 + q['ev_charge_loss'])) / 100 * q['ev_price_kwh']
              + q['ev_service_year'] / q['km_year'] * 1000
              + q['revenue_year'] * q['downtime'] / q['km_year'] * 1000)
    save = var_ice - var_ev                                            # руб./км
    return fixed_gap * 1000 / save, save, var_ice, var_ev, fixed_gap


if __name__ == '__main__':
    ice, ev, delta = tco(P)
    _, ev0, delta0 = tco(P, subsidy=False)
    be, save, v_ice, v_ev, gap = breakeven_km(P)
    be0, *_ = breakeven_km(P, subsidy=False)

    print('=== TCO за 3 года / 270 тыс. км, тыс. руб. на 1 автомобиль ===')
    rows = [('Автомобиль (нетто: цена - остаточная стоимость)', 'capex'),
            ('Топливо / электроэнергия', 'energy'),
            ('ТО и ремонт', 'service'),
            ('Простой на зарядку (недополученная выручка)', 'downtime'),
            ('Зарядная инфраструктура (нетто)', 'hub'),
            ('ИТОГО', 'total')]
    print(f"{'Статья':52}{'ДВС':>9}{'ЭМ+суб.':>10}{'ЭМ без суб.':>13}")
    for label, k in rows:
        print(f'{label:52}{ice[k]:9.0f}{ev[k]:10.0f}{ev0[k]:13.0f}')
    print(f"\nВыгода ЭМ с субсидией:  {delta:+.0f} тыс. руб. ({delta/3:+.0f} тыс. руб./год)")
    print(f"Выгода ЭМ без субсидии: {delta0:+.0f} тыс. руб. ({delta0/3:+.0f} тыс. руб./год)")
    print(f"\nПеременные затраты: ДВС {v_ice:.2f} руб./км, ЭМ {v_ev:.2f} руб./км, экономия {save:.2f} руб./км")
    print(f"Разрыв по постоянным затратам: {gap:.0f} тыс. руб.")
    print(f"Точка безубыточности: {be/1000:.0f} тыс. км = {be/P['km_year']*12:.0f} мес.")
    print(f"Без субсидии:         {be0/1000:.0f} тыс. км = {be0/P['km_year']*12:.0f} мес.")

    print('\n=== Чувствительность выгоды за 3 года, тыс. руб. на авто ===')
    cases = [
        ('Базовый сценарий', dict()),
        ('Субсидия не получена', dict(_sub=False)),
        ('Вся зарядка публичная, 20 руб./кВт*ч', dict(ev_price_kwh=20.0)),
        ('Пробег 60 тыс. км/год вместо 90', dict(km_year=60_000)),
        ('Остаток ЭМ 15% вместо 22%', dict(ev_residual=0.15)),
        ('Расход 24 кВт*ч/100 км (горы, жара)', dict(ev_kwh100=24.0)),
        ('Топливо +20% (АИ-92 83 руб./л)', dict(ice_fuel=82.8)),
        ('Простой 6% вместо 3%', dict(downtime=0.06)),
    ]
    for name, over in cases:
        sub = over.pop('_sub', True)
        print(f'{name:42}{tco(P, subsidy=sub, **over)[2]:+9.0f}')

    print('\n=== Мощность зарядного хаба ===')
    for n in (20, 50, 200):
        kwh = n * P['km_year'] / 365 * P['ev_kwh100'] / 100 * (1 + P['ev_charge_loss'])
        print(f'{n:3} авто: {kwh:6.0f} кВт*ч/сутки -> {kwh/8:5.0f} кВт присоединённой мощности (заряд за 8 ч)')
