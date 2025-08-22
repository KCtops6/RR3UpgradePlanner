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

def print_upgrade_summary_to_strings(upgrade_plan, final_pr, discount_percent, base_pr, final_tree):
    total_dollars = 0
    total_gold = 0
    running_pr = Decimal(str(base_pr))

    lines = []
    lines.append("Upgrade plan summary:")
    lines.append("-" * 10)

    for step in upgrade_plan:
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
    # NEW LINE: final tree string
    lines.append(f"Final upgrade tree: {format_upgrade_tree(final_tree)}")
    lines.append(f"Discount applied: {discount_percent}%")
    lines.append(f"Total cost: ${total_dollars:,} + {total_gold}G")

    return [], lines

def format_upgrade_tree(tree):
    return "".join(str(level) for level in tree)

def get_update_folders():
    """Return list of update files inside updates/ folder"""
    updates_dir = resource_path("updates")
    if not os.path.isdir(updates_dir):
        return []
    return [f[:-5] for f in os.listdir(updates_dir) if f.endswith(".json")]



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

        self.pr_entry.bind("<KeyRelease>", self.combined_validation)
        self.update_combo.bind("<<ComboboxSelected>>", self.combined_validation)
        self.car_combo.bind("<<ComboboxSelected>>", self.combined_validation)
        self.start_tree_entry.bind("<KeyRelease>", self.combined_validation)
        self.discount_entry.bind("<KeyRelease>", self.combined_validation)

        # Run button
        self.run_button = ttk.Button(top_frame, text="Calculate", command=self.run_calculation)
        self.run_button.grid(row=0, column=10, padx=10)
        self.run_button.config(state=tk.DISABLED)  # Start disabled

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
        """Populate car list, filtered by update if selected"""
        update = self.update_var.get()
        cars_dir = resource_path("cars")

        if not os.path.isdir(cars_dir):
            self.car_combo['values'] = []
            return

        all_cars = []
        # load car names from cars/ JSONs
        for f in os.listdir(cars_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(cars_dir, f), "r", encoding="utf-8") as file:
                        data = json.load(file)
                        car_name = data.get("car_name", f[:-5])
                        all_cars.append(car_name)
                except Exception:
                    pass

        # if update selected, filter
        if update:
            update_file = resource_path(f"updates/{update}.json")
            if os.path.isfile(update_file):
                try:
                    with open(update_file, "r", encoding="utf-8") as uf:
                        update_data = json.load(uf)
                        cars_in_update = update_data.get("cars", [])
                        all_cars = [c for c in all_cars if c in cars_in_update]
                except Exception:
                    pass

        self.car_combo['values'] = sorted(all_cars)

    def run_calculation(self):
        update = self.update_var.get()
        car = self.car_var.get()
        if not car:
            messagebox.showerror("Missing Input", "Please select a car.")
            return

        start_tree = self.start_tree_entry.get().strip()
        target_pr_str = self.pr_entry.get().strip()
        discount = self.discount_entry.get().strip()

        self.plan_tree.delete(*self.plan_tree.get_children())
        self.summary_text.delete(1.0, tk.END)

        try:
            discount = float(discount)
        except ValueError:
            messagebox.showerror("Invalid Input", "Discount must be a number.")
            return

        # Load car data
        car_path = resource_path(f"cars/{car}.json")
        try:
            with open(car_path, "r", encoding="utf-8") as f:
                car_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load car data: {e}")
            return

        # Build start tree
        categories = list(car_data["upgrades"].keys())
        if start_tree.lower() == "stock":
            current_tree = [0] * len(categories)
        else:
            try:
                current_tree = [int(x) for x in start_tree]
                if len(current_tree) != len(categories):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Input", f"Start tree must be 'stock' or {len(categories)} digits long.")
                return

        # Target PR
        base_pr = car_data.get("pr_stock", 0)
        if target_pr_str.lower() in ("max", "all"):
            max_pr_gain = sum(
                upgrade["pr_increase"]
                for category in car_data["upgrades"].values()
                for upgrade in category
            )
            target_pr = base_pr + max_pr_gain
        else:
            try:
                target_pr = float(target_pr_str)
            except ValueError:
                messagebox.showerror("Invalid Input", "Target PR must be a number or 'max'.")
                return

        # Run the calculation
        plan, final_pr, final_tree = calculate_min_cost(car_data, current_tree, target_pr, discount)

        # Fill the Treeview with steps
        running_pr = Decimal(str(base_pr))
        total_dollars = 0
        total_gold = 0
        for step in plan:
            cat = step["category"].title()
            lvl = step["level"]
            pr_inc = step["pr_increase"]
            cost = step["cost"]
            curr = step["currency"]

            running_pr += Decimal(str(pr_inc))
            if curr == "$":
                total_dollars += cost
                cost_str = f"${cost}"
            else:
                total_gold += cost
                cost_str = f"{cost}G"

            self.plan_tree.insert(
                "", "end",
                values=(f"{cat} {lvl}", f"+{pr_inc:.2f}", f"{running_pr:.2f}", cost_str, f"${total_dollars:,}", f"{total_gold}G")
            )

        # Print summary on right
        _, summary_lines = print_upgrade_summary_to_strings(plan, final_pr, discount, base_pr, final_tree)

        for line in summary_lines:
            self.summary_text.insert(tk.END, line + "\n")

    def validate_target_pr(self, event=None):
        target_pr_str = self.pr_entry.get().strip()
        car = self.car_var.get()

        # disable if no car selected
        if not car:
            self.run_button.config(state=tk.DISABLED)
            return

        # load car file
        car_path = resource_path(f"cars/{car}.json")
        try:
            with open(car_path, "r", encoding="utf-8") as f:
                car_data = json.load(f)
        except Exception:
            self.run_button.config(state=tk.DISABLED)
            return

        base_pr = car_data.get("pr_stock", 0)
        max_pr_gain = sum(
            upgrade["pr_increase"]
            for category in car_data["upgrades"].values()
            for upgrade in category
        )
        max_pr = base_pr + max_pr_gain

        # allow special inputs
        if target_pr_str.lower() in ("max", "all"):
            self.run_button.config(state=tk.NORMAL)
            return

        # validate numeric input
        try:
            target_pr_val = float(target_pr_str)
        except ValueError:
            self.run_button.config(state=tk.DISABLED)
            return

        # check valid range
        if target_pr_val <= base_pr or target_pr_val > max_pr or target_pr_val <= 0:
            self.run_button.config(state=tk.DISABLED)
        else:
            self.run_button.config(state=tk.NORMAL)

    def validate_discount(self, event=None):
        discount_str = self.discount_entry.get().strip()

        try:
            discount_val = float(discount_str)
            if discount_val < 0 or discount_val > 100:
                self.run_button.config(state=tk.DISABLED)
                return False
        except ValueError:
            self.run_button.config(state=tk.DISABLED)
            return False

        return True

    def combined_validation(self, event=None):
        discount_ok = self.validate_discount()
        if not discount_ok:
            return
        self.validate_target_pr()

if __name__ == "__main__":
    root = tk.Tk()
    app = RR3HelperGUI(root)
    root.mainloop()

# pyinstaller --onefile --windowed --add-data "vXX.X;vXX.X" RR3_upgrades_app.py