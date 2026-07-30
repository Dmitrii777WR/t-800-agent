---
title: "Pricing, usage limits и модели"
source: https://cursor.com/docs/models-and-pricing
audience: beginner
tier: 1
last_synced: 2026-07-30
provenance: manual
author: t-800
---

# Pricing, usage limits и модели

## Простыми словами

Cursor считает использование Agent и моделей. На бесплатном тарифе лимитов меньше, на Pro/Teams/Enterprise — больше возможностей.

## Что важно новичку

- Если Agent перестал отвечать или просит подождать — возможно, лимит
- Auto-модель часто экономит расход
- Max Mode и тяжёлые модели могут тратить больше
- Usage смотрите в Dashboard

## Что спрашивать у T-800 Agent

```text
Объясни мои лимиты Cursor простыми словами и где их посмотреть.
```

## Частые ошибки

- Думать, что все модели стоят одинаково
- Запускать большие задачи без Plan
- Не смотреть usage dashboard

## Пулы usage (Pro и выше)

Два отдельных пула, оба сбрасываются с месячным биллинг-циклом:

| Пул | Что внутри | Включено |
|-----|------------|----------|
| **Cursor Models** | Cursor Grok 4.5, Composer 2.5 | Значительно больше включённого usage |
| **Other Models** | Сторонние модели по API-цене модели | Минимум $20/мес на Pro+ (больше на старших тирах), дальше — доплата по мере использования |

Пулы видны в настройках редактора и на usage-дашборде. Тариф Start пул Other Models не включает.

## Cursor Router (Teams / Enterprise)

Router — это механика за **Auto**: ML-классификатор на каждый запрос решает, какая модель под задачу. Доступен только на Teams и Enterprise.

| Режим | Биллинг | Поведение |
|-------|---------|-----------|
| **Cost** | Bundled-цены Auto, за 1M токенов независимо от модели | Логика старого Auto, оптимизация расхода |
| **Balance** | По курсу сроутированной модели | Default для новых пользователей; качество/скорость/цена |
| **Intelligence** | По курсу сроутированной модели | Самые сильные модели пула для сложных задач |

Balance и Intelligence тратят лимиты быстрее Cost: в среднем ~2x, местами до 2–4x. Ручного выбора модели внутри Router нет — только выбор режима.

### Админ-контролы (team dashboard)

- **Enable Cursor Router** — вкл/выкл роутинг для команды; на Enterprise по умолчанию выключен, включается вручную (и настраивается per organization group)
- **Routing preferences** — какие режимы видят участники; можно отключить до 2 режимов
- **Underlying model** — показывать или скрывать, к какой модели сроутило (для Balance/Intelligence; default — скрыто, рекомендовано)
- **Impose Auto** — Soft: новый чат стартует на Auto (можно переключить); Hard: выбор модели залочен на Auto. Оба по умолчанию выключены

Для работы Router на Enterprise требуется включённый Cursor Grok 4.5 — роутеру нужна мощная и дешёвая модель для «своих» ответов. Блокировка слишком многих моделей деградирует роутинг и может отключить Router. Через SDK Router — это model id `auto-smart` с параметром `optimize_for` (`cost` / `balanced` / `intelligence`).

## Cursor Token Rate (Teams / Enterprise)

$0.25 за 1M токенов на запросы к сторонним моделям — и при прямом выборе такой модели, и когда Auto Balance/Intelligence роутит на неё. Считается по входным, выходным и кэшированным токенам; действует и на BYOK-usage поверх оплаты провайдеру. Покрывает поисковую инфраструктуру, кастомное исполнение и роутинг моделей.

Освобождены: **Auto Cost** и все first-party модели (Composer 2.5, Grok 4.5).

## Тариф Start (только Индия)

₹649/мес с учётом налогов, оплата в INR (UPI, карта). Включает щедрый usage пула Cursor Models (Grok 4.5 и Composer 2.5 в non-fast режиме; у Grok 4.5 фиксированный medium effort — сменить effort и включить Fast нельзя), Cloud Agents, Cursor для iOS, плагины, MCP, hooks и skills. Не включает: пул Other Models, on-demand usage, Bugbot, Auto, Automations и Cursor SDK.

## Официальные ссылки

- https://cursor.com/docs/models-and-pricing
- https://cursor.com/docs/cursor-router
- https://cursor.com/help/models-and-usage/token-rate
- https://cursor.com/help/models-and-usage/usage-limits
