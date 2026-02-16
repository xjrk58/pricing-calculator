# Pricing Tier Calculator

A tiered pricing calculator with interactive Chart.js visualization. Define pricing tiers with per-unit costs, flat fees, free units, and repeating tiers — then see cumulative, average, and marginal price curves update in real time.

## Demo

Open `index.html` in a browser (requires a local server for ES modules):

```bash
python3 -m http.server
```

Then visit `http://localhost:8000`.

## Pricing Model

Tiers are ordered by sequence. Each tier defines:

| Field | Description |
|-------|-------------|
| **Sequence** | Ordering of the tier |
| **Units** | Number of units this tier covers per repetition |
| **Price** | Flat fee charged each time this tier is entered |
| **Unit Price** | Per-unit cost within the tier |
| **Free Units** | Units within the tier that are not charged |
| **Multiplier** | How many times the tier repeats (supports `∞` for unlimited) |

Cost for units consumed in a single tier repetition:

```
billableUnits = max(0, consumed - freeUnits)
tierCost = price + billableUnits * unitPrice
```

### Global Adjustments

- **MRR (Minimum Recurring Revenue)** — a price floor. If usage cost is below MRR, the customer pays MRR. If usage exceeds MRR, they pay the usage amount.
- **Discount %** — percentage off the total (applied after the MRR floor).

```
total = max(MRR, usageCost) * (1 - discount / 100)
```

## Chart

Three lines plotted from 0 to the total unit range:

- **Total Cumulative Price** — sum of all costs from unit 0 to N (with MRR floor and discount applied)
- **Average Unit Price** — cumulative price / N (hidden while usage is below MRR)
- **Current Price (Marginal)** — effective per-unit rate at unit N (0 while under MRR floor)

## Features

- Editable tier table with inline number inputs
- Range sliders below each field for quick adjustment
- Currency selector (USD, EUR, GBP, JPY, CHF, and more)
- MRR minimum floor and discount percentage
- Add/remove tiers with automatic chart re-render
- Multiplier supports integers or `∞` for unlimited repetition
- Export/import full configuration as JSON
- Dual Y-axes: cumulative price (left) and unit price (right)
- Tooltips on hover with exact values

## Files

| File | Purpose |
|------|---------|
| `index.html` | Demo page with embedded CSS and Chart.js CDN |
| `pricing-component.js` | Self-contained ES module (`PricingComponent` class) |
| `test_pricing.py` | 35 Selenium tests (headless Chrome) |
| `.github/workflows/deploy.yml` | GitHub Pages deployment |

## Tests

```bash
pip install selenium pytest
python3 -m pytest test_pricing.py -v
```

Requires Google Chrome installed. Selenium 4.x auto-manages the ChromeDriver.

## Technology

- Vanilla JavaScript (no framework, no build tools)
- Chart.js 4.x via CDN
- Python + Selenium + pytest for testing
