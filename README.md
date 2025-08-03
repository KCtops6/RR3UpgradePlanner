# RR3 Helper GUI

A Python desktop application to calculate the minimum-cost upgrade plan for cars in *Real Racing 3* based on your current upgrade tree, target Performance Rating (PR), and any applicable discounts. It reads data from JSON files organized by game updates and cars.

---

## Features

- Select the game update version (e.g., `v13.5`) based on local folder structure.
- Choose a car from the selected update’s JSON files.
- Input your current upgrade tree (`stock` or digit string) to reflect installed upgrades.
- Enter a target PR to reach, or use `max` for full upgrade.
- Specify any discount percentage on upgrade costs.
- Outputs a detailed upgrade plan with costs and PR increases.
- Displays summary including base PR, starting PR, total costs, and discounts.
- Upgrade plan is displayed as a sortable table.
- Easy to use graphical user interface powered by Tkinter.

---

## Folder Structure

