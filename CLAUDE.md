# Project: Pricing Tier Calculator

## Overview
Tiered pricing calculator with Chart.js visualization. Vanilla JS, no framework, no build tools.

## Key Files
- `pricing-component.js` — `PricingComponent` ES module class (tier management, calculation engine, Chart.js rendering)
- `index.html` — Demo page with embedded CSS, loads Chart.js 4.x from CDN
- `test_pricing.py` — 35 Selenium tests (Python, pytest, headless Chrome)
- `.github/workflows/deploy.yml` — GitHub Pages static deployment

## Architecture
- `PricingComponent` is fully self-contained: takes a container element, renders tier table + chart
- Constructor accepts `(container, initialTiers?, currency?)`
- Exports: `PricingComponent` class, `CURRENCIES` array
- `render()` rebuilds the full DOM (table + chart wrapper), `updateChart()` destroys and recreates the Chart.js instance
- `bindInputs()` handles bidirectional sync between number inputs, text inputs, and range sliders
- `calculate()` returns `{ labels, cumulative, average, current }` arrays sampled at up to 1000 points
- `toJSON()` / `loadJSON(config)` — serialize/restore full state; `Infinity` stored as `"infinity"` in JSON
- `exportConfig()` triggers a file download, `importConfig()` opens a file picker

## Pricing Model
- Tiers sorted by `sequence`
- Each tier repeats `multiplier` times (supports `Infinity` for unlimited)
- Cost per repetition: `price + max(0, consumed - freeUnits) * unitPrice`
- Multiplier is a repetition count, NOT a price scaling factor
- **MRR** (Minimum Recurring Revenue): price floor — `total = max(MRR, usageCost) * (1 - discount/100)`
- **Discount**: percentage off the total (applied after MRR floor)
- Marginal rate is 0 while usage cost is below MRR; average unit price is `null` (hidden on chart) below MRR

## UI Details
- Multiplier field is `type="text"` (not number) to support "∞" input
- `parseMultiplier()` accepts: `∞`, `inf`, `infinity` → `Infinity`; positive integers; defaults to 1
- Multiplier slider: range 1–10, position 10 = `∞`
- Sequence column has no slider (just a number input)
- Currency selector is a `<select>` above the tier table, updates chart axis labels and tooltips
- MRR and Discount inputs with synced sliders (MRR: 0–5000, Discount: 0–100%)
- Export JSON / Import JSON buttons in the actions row below the tier table
- Chart canvas wrapped in a `div` with `position: relative; height: 400px` to prevent Chart.js infinite growth bug
- Color palette: blue `#0d6efd` (primary/focus), indigo `#6610f2` (slider accent), purple `#6f42c1` (hover)

## Testing
- `python3 -m pytest test_pricing.py -v`
- Spins up `http.server` on port 8791 in a daemon thread
- Uses headless Chrome via Selenium 4.x (auto-managed ChromeDriver)
- Tests use `_get_tier_inputs()` (excludes range inputs) and `_get_tier_sliders()` helpers
- Chart data extracted via `Chart.instances` JS API
- Sliders manipulated via `dispatchEvent(new Event('input'))` since Selenium can't drag range inputs natively

## Conventions
- Commits end with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- User prefers squash + force push to keep history clean
- Remote: `github.com:xjrk58/pricing-calculator.git`, branch `main`
