---
title: "Тарифы и лимиты"
source: https://cursor.com/pricing
audience: beginner
tier: 2
last_synced: 2026-07-30
provenance: manual
author: t-800
---

## Простыми словами

Бесплатный **Hobby** — с лимитами на Agent. **Pro** — больше запросов, MCP, skills, cloud agents.

## Для новичка

Hobby хватит на обучение. Если часто упираетесь в лимит — смотрите Pro.

## Что важно

- Лимиты обновляются по правилам тарифа (см. pricing)
- «Auto» модель — экономит лимиты

## Auto и режимы Cursor Router

Режим **Auto** — это роутер: он сам выбирает модель под каждый запрос. Три режима оптимизации в выборе модели:

| Режим | Смысл |
|-------|-------|
| **Cost** | Как старый Auto: минимум расхода, bundled-цены Auto |
| **Balance** | Default для новых пользователей: баланс качества и цены |
| **Intelligence** | Посильнее модели для сложных задач; дороже |

## Два пула usage

На Pro и выше месячный usage делится на два пула:

- **Cursor Models** — свои модели (Cursor Grok 4.5, Composer 2.5), включено заметно больше
- **Other Models** — сторонние модели по API-цене; на Pro+ включено минимум $20 в месяц

Оба пула видны в настройках и на usage-дашборде.

## Token Rate

На тарифах Teams и Enterprise за запросы к сторонним моделям берётся Cursor Token Rate — $0.25 за 1M токенов (вход, выход и кэш), включая BYOK. Auto Cost и свои модели (Grok 4.5, Composer 2.5) — без Token Rate.

## Тариф Start

**Start** — тариф для разработчиков в Индии: ₹649/мес (с учётом налогов). Включает пул Cursor Models и Cloud Agents, но не включает пул Other Models, Bugbot, Auto и on-demand usage.

## Официальная ссылка

https://cursor.com/pricing
