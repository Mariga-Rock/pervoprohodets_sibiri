from app.events_loader import (
    load_events, get_event, get_daily_pool, get_events_count
)

print(f"Всего ивентов: {get_events_count()}")

elk = get_event("event_frozen_elk")
print(f"event_frozen_elk: {elk['title']}")
print(f"  Вариантов выбора: {len(elk['choices'])}")

first_choice = elk["choices"][0]
print(f"  choice[0] = {first_choice['choice_id']}, "
      f"next_event = {first_choice['next_event']}")

pool = get_daily_pool()
print(f"\nВ дневном пуле: {len(pool)} ивентов")
for eid in pool:
    print(f"  - {eid}")

assert "event_frozen_elk_disgust" not in pool, \
    "chain_only попал в дневной пул!"
print("\n[OK] chain_only исключён из дневного пула")

a = load_events()
b = load_events()
assert a is b, "Кэш не работает!"
print("[OK] Кэш работает (a is b)")
