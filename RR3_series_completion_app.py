import os
import json
from decimal import Decimal, getcontext
import heapq


getcontext().prec = 10
cars_folder = "cars"
series_file = "series/Pure Stock Challenge.json"
GOLD_TO_DOLLARS = 10_000_000  # same as old program

def calculate_min_cost(car_data, target_pr, discount_percent=0):
    discount_multiplier = (100 - discount_percent) / 100.0
    categories = list(car_data["upgrades"].keys())
    upgrades = car_data["upgrades"]
    base_pr = Decimal(str(car_data.get("pr_stock", car_data.get("base_pr", 0))))

    max_pr_gain = sum(
        Decimal(str(upg.get("pr", upg.get("pr_increase", 0))))
        for cat in upgrades.values()
        for upg in cat
    )
    max_pr = base_pr + max_pr_gain
    if max_pr < Decimal(str(target_pr)):
        return None

    start_state = tuple([0]*len(categories))
    pq = [(0, -float(base_pr), 0, 0, start_state, [])]
    visited = {start_state: 0}

    while pq:
        total_cost, neg_pr, total_dollars, total_gold, state, path = heapq.heappop(pq)
        current_pr = Decimal(str(-neg_pr))
        if current_pr >= Decimal(str(target_pr)):
            return {
                "final_pr": float(current_pr),
                "upgrades": path,
                "total_cost_dollars": total_dollars,
                "total_cost_gold": total_gold
            }

        for i, cat in enumerate(categories):
            lvl = state[i]
            cat_upgrades = upgrades[cat]
            if lvl >= len(cat_upgrades):
                continue
            upg = cat_upgrades[lvl]

            if upg.get("cost_dollars") is not None:
                cost = round(upg["cost_dollars"] * discount_multiplier)
                currency = "$"
            elif upg.get("cost_gold") is not None:
                cost = round(upg["cost_gold"] * discount_multiplier)
                currency = "G"
            else:
                continue

            new_state = list(state)
            new_state[i] += 1
            new_state = tuple(new_state)
            new_total_dollars = total_dollars + (cost if currency == "$" else 0)
            new_total_gold = total_gold + (cost if currency == "G" else 0)
            new_pr = current_pr + Decimal(str(upg.get("pr", upg.get("pr_increase", 0))))

            if new_state not in visited or visited[new_state] > new_total_dollars + new_total_gold * GOLD_TO_DOLLARS:
                visited[new_state] = new_total_dollars + new_total_gold * GOLD_TO_DOLLARS
                new_path = path + [{"category": cat, "level": new_state[i], "pr_increase": float(upg.get("pr", upg.get("pr_increase", 0))),
                                     "cost": cost, "currency": currency}]
                heapq.heappush(pq, (new_total_dollars + new_total_gold * GOLD_TO_DOLLARS, -float(new_pr), new_total_dollars, new_total_gold, new_state, new_path))

    return None

# --- Load series ---
with open(series_file, "r", encoding="utf-8") as f:
    series = json.load(f)

required_pr = series["max_required_pr"]
cars = series["cars"]

needed_cars = []

# --- Find the cheapest car and upgrades ---
best_solution = None

for car_name in cars:
    car_path = os.path.join(cars_folder, car_name + ".json")
    if not os.path.exists(car_path):
        continue
    with open(car_path, "r", encoding="utf-8") as f:
        car_data = json.load(f)

    result = calculate_min_cost(car_data, required_pr)
    if result is None:
        continue

    total_cost = result["total_cost_dollars"] + result["total_cost_gold"] * GOLD_TO_DOLLARS
    if best_solution is None or total_cost < best_solution["total_cost"]:
        # Build final upgrade tree string
        categories = list(car_data["upgrades"].keys())
        final_levels = [0] * len(categories)
        for step in result["upgrades"]:
            idx = categories.index(step["category"])
            final_levels[idx] = step["level"]
        final_tree_str = "".join(str(lvl) for lvl in final_levels)

        best_solution = {
            "car_name": car_name,
            "final_pr": result["final_pr"],
            "final_tree": final_tree_str,
            "total_cost": total_cost
        }

# --- Export to TXT ---
txt_file = "needed_car.txt"
with open(txt_file, "w", encoding="utf-8") as f:
    if best_solution:
        line = f"{best_solution['car_name']} (PR: {best_solution['final_pr']:.2f}, {best_solution['final_tree']}, {series['series_name']})"
        f.write(line + "\n")
    else:
        f.write("No car can reach the required PR.\n")

print(f"Text file exported: {txt_file}")
