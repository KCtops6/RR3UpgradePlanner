import os
import sys
import json
import heapq
from decimal import Decimal, getcontext
import tkinter as tk
from tkinter import ttk, messagebox

getcontext().prec = 10  # enough precision for PR math

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Backend logic ---

def calculate_min_cost(car_data, current_tree, target_pr, discount_percent):
    GOLD_TO_DOLLARS = 10_000_000
    discount_multiplier = (100 - discount_percent) / 100.0
    categories = list(car_data["upgrades"].keys())
    upgrades = car_data["upgrades"]

    start_state = tuple(current_tree)
    base_pr = Decimal(str(car_data.get("pr_stock", 0)))

    current_pr_val = base_pr + sum(
        Decimal(str(upgrades[categories[i]][lvl - 1]["pr_increase"])) if lvl > 0 else Decimal("0")
        for i, lvl in enumerate(start_state)
    )

    pq = [(0, -float(current_pr_val), 0, 0, start_state, [])]  # total_cost, -pr, dollars, gold, state, path
    visited = {start_state: 0}

    while pq:
        total_cost, neg_pr, total_dollars, total_gold, state, path = heapq.heappop(pq)
        current_pr = Decimal(str(-neg_pr))

        if current_pr >= Decimal(str(target_pr)):
            return path, float(current_pr), list(state)

        for i, cat in enumerate(categories):
            level = state[i]
            cat_upgrades = upgrades[cat]
            if level >= len(cat_upgrades):
                continue

            next_upg = cat_upgrades[level]

            # Calculate cost with discount and round to int
            if next_upg["cost_dollars"] is not None:
                cost = round(next_upg["cost_dollars"] * discount_multiplier)
                currency = "$"
            elif next_upg["cost_gold"] is not None:
                cost = round(next_upg["cost_gold"] * discount_multiplier)
                currency = "G"
            else:
                continue

            new_state = list(state)
            new_state[i] += 1
            new_state = tuple(new_state)

            new_total_dollars = total_dollars + (cost if currency == "$" else 0)
            new_total_gold = total_gold + (cost if currency == "G" else 0)

            new_total_cost = new_total_dollars + new_total_gold * GOLD_TO_DOLLARS
            new_pr = current_pr + Decimal(str(next_upg["pr_increase"]))

            if new_state not in visited or visited[new_state] > new_total_cost:
                visited[new_state] = new_total_cost
                new_path = path + [ {
                    "category": cat,
                    "level": new_state[i],
                    "pr_increase": float(next_upg["pr_increase"]),
                    "cost": cost,
                    "currency": currency
                }]
                heapq.heappush(pq, (new_total_cost, -float(new_pr), new_total_dollars, new_total_gold, new_state, new_path))

    return [], float(current_pr_val), list(start_state)

def print_upgrade_summary_to_strings(upgrade_plan, final_pr, discount_percent, base_pr):
    total_dollars = 0
    total_gold = 0
    running_pr = Decimal(str(base_pr))

    lines = []
    lines.append("Upgrade plan summary:")
    lines.append("-" * 60)

    for step in upgrade_plan:
        cat = step["category"].title()
        lvl = step["level"]
        pr_inc = Decimal(str(step["pr_increase"]))
        cost = step["cost"]
        currency = step["currency"]

        running_pr += pr_inc
        if currency == "$":
            total_dollars += cost
        else:
            total_gold += cost

    total_pr_increase = Decimal(str(final_pr)) - Decimal(str(base_pr))

    lines.append(f"Base PR: {base_pr:.2f}")
    lines.append(f"Total PR Increase: {float(total_pr_increase):.2f}")
    lines.append(f"Final PR: {final_pr:.2f}")
    lines.append(f"Discount applied: {discount_percent}%")
    lines.append(f"Total cost: ${total_dollars:,} + {total_gold}G")

    return [], lines

def format_upgrade_tree(tree):
    return "".join(str(level) for level in tree)

def get_update_folders():
    base_dir = resource_path(".")
    return [name for name in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, name)) and name.startswith("v")]

# --- GUI class ---

class RR3HelperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RR3 Helper GUI")

        # === Top Frame ===
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Update selection
        ttk.Label(top_frame, text="Update:").grid(row=0, column=0, sticky=tk.W)
        self.update_var = tk.StringVar()
        self.update_combo = ttk.Combobox(top_frame, textvariable=self.update_var, width=10, postcommand=self.load_updates)
        self.update_combo.grid(row=0, column=1, padx=5)

        # Car selection
        ttk.Label(top_frame, text="Car:").grid(row=0, column=2, sticky=tk.W)
        self.car_var = tk.StringVar()
        self.car_combo = ttk.Combobox(top_frame, textvariable=self.car_var, width=40, postcommand=self.load_cars)
        self.car_combo.grid(row=0, column=3, padx=5)

        # Starting upgrade tree
        ttk.Label(top_frame, text="Start Tree:").grid(row=0, column=4, sticky=tk.W)
        self.start_tree_entry = ttk.Entry(top_frame, width=10)
        self.start_tree_entry.insert(0, "stock")
        self.start_tree_entry.grid(row=0, column=5, padx=5)

        # Target PR
        ttk.Label(top_frame, text="Target PR:").grid(row=0, column=6, sticky=tk.W)
        self.pr_entry = ttk.Entry(top_frame, width=10)
        self.pr_entry.grid(row=0, column=7, padx=5)

        # Discount
        ttk.Label(top_frame, text="Discount (%):").grid(row=0, column=8, sticky=tk.W)
        self.discount_entry = ttk.Entry(top_frame, width=5)
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=0, column=9, padx=5)

        # Run button
        run_button = ttk.Button(top_frame, text="Calculate", command=self.run_calculation)
        run_button.grid(row=0, column=10, padx=10)

        # === Bottom Section ===
        bottom_frame = ttk.Frame(root, padding=10)
        bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Treeview with scrollbar for upgrade plan (left)
        columns = ("Category Level", "PR Increase", "Total PR", "Cost", "Total Dollars", "Total Gold")
        self.plan_tree = ttk.Treeview(bottom_frame, columns=columns, show="headings", height=30)
        for col in columns:
            self.plan_tree.heading(col, text=col)
            self.plan_tree.column(col, anchor=tk.CENTER, width=100)

        plan_scroll = ttk.Scrollbar(bottom_frame, orient="vertical", command=self.plan_tree.yview)
        self.plan_tree.configure(yscrollcommand=plan_scroll.set)
        self.plan_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        plan_scroll.pack(side=tk.LEFT, fill=tk.Y)

        # Summary text on the right remains a Text widget
        self.summary_text = tk.Text(bottom_frame, width=40, height=30)
        self.summary_text.pack(side=tk.RIGHT, fill=tk.BOTH)

        # To store car file mapping
        self.car_file_map = {}

    def load_updates(self):
        """Populate update versions based on folder structure"""
        updates = get_update_folders()
        self.update_combo['values'] = updates

    def load_cars(self):
        """Populate car list from selected update folder"""
        update = self.update_var.get()
        if not update:
            self.car_combo['values'] = []
            return

        update_path = resource_path(update)
        if not os.path.isdir(update_path):
            self.car_combo['values'] = []
            return

        car_files = [f for f in os.listdir(update_path) if f.endswith(".json")]
        car_names = []
        self.car_file_map.clear()
        for f in car_files:
            try:
                with open(os.path.join(update_path, f), "r", encoding="utf-8") as file:
                    data = json.load(file)
                    car_name = data.get("car_name", f)
                    car_names.append(car_name)
                    self.car_file_map[car_name] = f
            except Exception:
                pass
        self.car_combo['values'] = car_names

    def run_calculation(self):
        update = self.update_var.get()
        car = self.car_var.get()
        car_file = self.car_file_map.get(car)
        start_tree = self.start_tree_entry.get().strip()
        target_pr = self.pr_entry.get().strip()
        discount = self.discount_entry.get().strip()

        self.plan_tree.delete(*self.plan_tree.get_children())
        self.summary_text.delete(1.0, tk.END)

        if not update or not car or not car_file or not target_pr:
            messagebox.showerror("Missing Input", "Please fill in all required fields.")
            return

        try:
            discount = float(discount)
        except ValueError:
            messagebox.showerror("Invalid Input", "Discount must be a number.")
            return

        update_path = resource_path(update)
        car_path = os.path.join(update_path, car_file)
        try:
            with open(car_path, "r", encoding="utf-8") as f:
                car_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load car data: {e}")
            return

        upgrade_categories = list(car_data["upgrades"].keys())
        expected_length = len(upgrade_categories)

        if start_tree.lower() == "stock":
            current_tree = [0] * expected_length
        else:
            if len(start_tree) != expected_length or not start_tree.isdigit():
                messagebox.showerror("Invalid Input", f"Start Tree must be 'stock' or a digit string of length {expected_length}")
                return
            current_tree = [int(c) for c in start_tree]

        max_pr_gain = sum(
            upgrade["pr_increase"]
            for category in car_data["upgrades"].values()
            for upgrade in category
        )
        base_pr = car_data.get("pr_stock", 0)

        if target_pr.lower() in ("max", "all"):
            target_pr_val = base_pr + max_pr_gain
        else:
            try:
                target_pr_val = float(target_pr)
                if target_pr_val <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Input", "Target PR must be a positive number or 'max'.")
                return

        upgrade_plan, final_pr, final_tree = calculate_min_cost(car_data, current_tree, target_pr_val, discount)

        total_dollars = 0
        total_gold = 0
        running_pr = Decimal(str(base_pr))

        # Show starting PR and installed upgrades in summary
        self.summary_text.insert(tk.END, f"Base PR: {base_pr:.2f}\n")
        starting_pr_val = base_pr + sum(
            car_data["upgrades"][upgrade_categories[i]][lvl-1]["pr_increase"] if lvl > 0 else 0
            for i, lvl in enumerate(current_tree)
        )
        self.summary_text.insert(tk.END, f"Starting PR (with installed upgrades): {starting_pr_val:.2f}\n")
        self.summary_text.insert(tk.END, f"Installed Upgrades:\n")
        for cat, lvl in zip(upgrade_categories, current_tree):
            pr_inc = 0.0
            if lvl > 0:
                pr_inc = sum(up["pr_increase"] for up in car_data["upgrades"][cat][:lvl])
            self.summary_text.insert(tk.END, f"  {cat}: level {lvl} (+{pr_inc:.1f} PR)\n")
        self.summary_text.insert(tk.END, "\nUpgrade plan:\n")

        for step in upgrade_plan:
            cat = step["category"].title()
            lvl = step["level"]
            pr_inc = Decimal(str(step["pr_increase"]))
            cost = step["cost"]
            currency = step["currency"]

            running_pr += pr_inc
            if currency == "$":
                total_dollars += cost
            else:
                total_gold += cost

            cost_str = f"{currency}{cost:,}"
            total_dollars_str = f"${total_dollars:,}"
            total_gold_str = f"{total_gold}G"

            cat_lvl_str = f"{cat} {lvl}"
            pr_inc_str = f"+{float(pr_inc):.1f}"
            total_pr_str = f"{float(running_pr):.1f}"

            self.plan_tree.insert("", tk.END, values=(cat_lvl_str, pr_inc_str, total_pr_str, cost_str, total_dollars_str, total_gold_str))

        _, summary_lines = print_upgrade_summary_to_strings(upgrade_plan, final_pr, discount, base_pr)
        self.summary_text.insert(tk.END, "\n".join(summary_lines))


if __name__ == "__main__":
    root = tk.Tk()
    app = RR3HelperGUI(root)
    root.mainloop()

# pyinstaller --onefile --windowed --add-data "vXX.X;vXX.X" RR3_upgrades_app_vXX.X.py