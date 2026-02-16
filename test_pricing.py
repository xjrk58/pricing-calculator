import http.server
import os
import threading
import time
import unittest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PORT = 8791
DIR = os.path.dirname(os.path.abspath(__file__))


def start_server():
    handler = http.server.SimpleHTTPRequestHandler
    os.chdir(DIR)
    server = http.server.HTTPServer(("", PORT), handler)
    server.serve_forever()


class PricingComponentTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server_thread = threading.Thread(target=start_server, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,900")
        cls.driver = webdriver.Chrome(options=opts)
        cls.driver.get(f"http://localhost:{PORT}/index.html")
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def _wait_chart(self):
        """Wait until the Chart.js canvas has rendered (non-zero dimensions)."""
        self.wait.until(
            lambda d: d.execute_script(
                "const c = document.getElementById('pricing-chart-canvas');"
                "return c && c.getBoundingClientRect().height > 50;"
            )
        )

    def _get_tier_inputs(self):
        """Return all input rows grouped by tier index (excludes range sliders)."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, ".tier-table tbody tr")
        tiers = []
        for row in rows:
            inputs = row.find_elements(By.CSS_SELECTOR, 'input:not([type="range"])')
            tiers.append({inp.get_attribute("data-field"): inp for inp in inputs})
        return tiers

    def _get_tier_sliders(self):
        """Return all slider inputs grouped by tier index."""
        rows = self.driver.find_elements(By.CSS_SELECTOR, ".tier-table tbody tr")
        tiers = []
        for row in rows:
            sliders = row.find_elements(By.CSS_SELECTOR, "input.field-slider")
            tiers.append({s.get_attribute("data-field"): s for s in sliders})
        return tiers

    def _chart_data(self):
        """Extract current chart dataset values via Chart.js API."""
        return self.driver.execute_script(
            "const chart = Chart.instances[Object.keys(Chart.instances)[0]];"
            "return {"
            "  labels: chart.data.labels,"
            "  cumulative: chart.data.datasets[0].data,"
            "  average: chart.data.datasets[1].data,"
            "  current: chart.data.datasets[2].data"
            "};"
        )

    def _reload(self):
        """Reload page and wait for chart."""
        self.driver.get(f"http://localhost:{PORT}/index.html")
        self._wait_chart()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_page_loads(self):
        """Page title and heading are correct."""
        self.assertIn("Pricing Tier Calculator", self.driver.title)
        h1 = self.driver.find_element(By.TAG_NAME, "h1")
        self.assertEqual(h1.text, "Pricing Tier Calculator")

    def test_02_default_tiers_displayed(self):
        """Three default tiers render in the table."""
        tiers = self._get_tier_inputs()
        self.assertEqual(len(tiers), 3)
        # First tier: sequence=1, units=100
        self.assertEqual(tiers[0]["sequence"].get_attribute("value"), "1")
        self.assertEqual(tiers[0]["units"].get_attribute("value"), "100")

    def test_03_default_multiplier_values(self):
        """Default tiers show correct multiplier values including infinity."""
        tiers = self._get_tier_inputs()
        self.assertEqual(tiers[0]["multiplier"].get_attribute("value"), "1")
        self.assertEqual(tiers[1]["multiplier"].get_attribute("value"), "2")
        self.assertEqual(tiers[2]["multiplier"].get_attribute("value"), "\u221e")  # ∞

    def test_04_chart_renders(self):
        """Chart canvas exists and has non-trivial size."""
        self._wait_chart()
        canvas = self.driver.find_element(By.ID, "pricing-chart-canvas")
        height = canvas.rect["height"]
        self.assertGreater(height, 50)

    def test_05_chart_has_three_datasets(self):
        """Chart contains exactly 3 datasets with correct labels."""
        self._wait_chart()
        labels = self.driver.execute_script(
            "const chart = Chart.instances[Object.keys(Chart.instances)[0]];"
            "return chart.data.datasets.map(d => d.label);"
        )
        self.assertEqual(len(labels), 3)
        self.assertIn("Total Cumulative Price", labels)
        self.assertIn("Average Unit Price", labels)
        self.assertIn("Current Price (Marginal)", labels)

    def test_06_chart_data_starts_at_zero(self):
        """At unit 0, cumulative is 0 and average is null."""
        self._wait_chart()
        data = self._chart_data()
        self.assertEqual(data["labels"][0], 0)
        self.assertEqual(data["cumulative"][0], 0)
        self.assertIsNone(data["average"][0])

    def test_07_cumulative_is_nondecreasing(self):
        """Cumulative price should never decrease."""
        self._wait_chart()
        data = self._chart_data()
        for i in range(1, len(data["cumulative"])):
            self.assertGreaterEqual(
                data["cumulative"][i],
                data["cumulative"][i - 1],
                f"Cumulative decreased at index {i}",
            )

    def test_08_edit_tier_updates_chart(self):
        """Changing a tier's unit price updates chart data."""
        self._wait_chart()
        data_before = self._chart_data()
        last_cum_before = data_before["cumulative"][-1]

        tiers = self._get_tier_inputs()
        unit_price_input = tiers[0]["unitPrice"]
        unit_price_input.clear()
        unit_price_input.send_keys("20")
        time.sleep(0.3)

        data_after = self._chart_data()
        last_cum_after = data_after["cumulative"][-1]
        self.assertNotEqual(last_cum_before, last_cum_after)

        # Restore original value
        unit_price_input.clear()
        unit_price_input.send_keys("10")
        time.sleep(0.3)

    def test_09_add_tier(self):
        """Clicking '+ Add Tier' adds a row and updates the chart."""
        tiers_before = self._get_tier_inputs()
        data_before = self._chart_data()

        add_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn-add")
        add_btn.click()
        time.sleep(0.3)

        tiers_after = self._get_tier_inputs()
        self.assertEqual(len(tiers_after), len(tiers_before) + 1)

        data_after = self._chart_data()
        self.assertGreater(len(data_after["labels"]), 0)
        self.assertGreater(data_after["labels"][-1], data_before["labels"][-1])

    def test_10_remove_tier(self):
        """Clicking remove button removes a tier row."""
        tiers_before = self._get_tier_inputs()
        count_before = len(tiers_before)

        remove_btns = self.driver.find_elements(By.CSS_SELECTOR, ".btn-remove")
        remove_btns[-1].click()
        time.sleep(0.3)

        tiers_after = self._get_tier_inputs()
        self.assertEqual(len(tiers_after), count_before - 1)

    def test_11_cannot_remove_last_tier(self):
        """Should not be able to remove the final remaining tier."""
        while True:
            tiers = self._get_tier_inputs()
            if len(tiers) <= 1:
                break
            remove_btn = self.driver.find_elements(By.CSS_SELECTOR, ".btn-remove")[0]
            remove_btn.click()
            time.sleep(0.2)

        remove_btn = self.driver.find_elements(By.CSS_SELECTOR, ".btn-remove")[0]
        remove_btn.click()
        time.sleep(0.2)

        tiers = self._get_tier_inputs()
        self.assertEqual(len(tiers), 1)

        self._reload()

    def test_12_chart_does_not_grow(self):
        """Chart height stays stable across multiple re-renders."""
        self._wait_chart()
        canvas = self.driver.find_element(By.ID, "pricing-chart-canvas")
        initial_height = canvas.rect["height"]

        tiers = self._get_tier_inputs()
        inp = tiers[0]["units"]
        for val in ["150", "200", "100"]:
            inp.clear()
            inp.send_keys(val)
            time.sleep(0.3)

        canvas = self.driver.find_element(By.ID, "pricing-chart-canvas")
        final_height = canvas.rect["height"]
        self.assertAlmostEqual(initial_height, final_height, delta=5)

    def test_13_free_units_produce_zero_marginal(self):
        """When all consumed units fall within freeUnits, marginal rate is 0."""
        self._wait_chart()
        data = self._chart_data()
        idx = None
        for i, label in enumerate(data["labels"]):
            if label >= 5:
                idx = i
                break
        self.assertIsNotNone(idx)
        if data["labels"][idx] <= 10:
            self.assertEqual(data["current"][idx], 0)

    def test_14_tooltip_on_hover(self):
        """Hovering over the chart triggers a tooltip element."""
        self._wait_chart()
        canvas = self.driver.find_element(By.ID, "pricing-chart-canvas")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})", canvas)
        time.sleep(0.3)

        action = ActionChains(self.driver)
        action.move_to_element(canvas).perform()
        time.sleep(0.5)

        tooltip_active = self.driver.execute_script(
            "const chart = Chart.instances[Object.keys(Chart.instances)[0]];"
            "return chart.tooltip && chart.tooltip.opacity > 0;"
        )
        self.assertTrue(tooltip_active, "Tooltip should be visible on hover")

    def test_15_multiplier_repeats_tier(self):
        """A tier with multiplier=2 covers 2x its unit range on the chart."""
        self._reload()
        # Default: tier1=100*1, tier2=200*2, tier3=500*inf(5)
        # Total = 100 + 400 + 2500 = 3000
        data = self._chart_data()
        self.assertEqual(data["labels"][-1], 3000)

    def test_16_edit_multiplier_to_number(self):
        """Changing multiplier from ∞ to a number updates the chart range."""
        self._reload()
        data_before = self._chart_data()
        max_before = data_before["labels"][-1]

        tiers = self._get_tier_inputs()
        mult_input = tiers[2]["multiplier"]  # tier 3, currently ∞
        mult_input.clear()
        mult_input.send_keys("1")
        time.sleep(0.3)

        data_after = self._chart_data()
        max_after = data_after["labels"][-1]
        # 100 + 400 + 500 = 1000, down from 3000
        self.assertEqual(max_after, 1000)
        self.assertLess(max_after, max_before)

        # Restore
        mult_input.clear()
        mult_input.send_keys("\u221e")
        time.sleep(0.3)

    def test_17_edit_multiplier_to_infinity(self):
        """Typing ∞ into multiplier sets unlimited repetitions."""
        self._reload()
        tiers = self._get_tier_inputs()
        mult_input = tiers[0]["multiplier"]  # tier 1, currently 1
        mult_input.clear()
        mult_input.send_keys("\u221e")
        time.sleep(0.3)

        # With tier1 unlimited (100*5=500), tier2 never reached
        # Total should be 500 for just tier 1's chart range
        # But tier2 and tier3 are after in sequence, so the unlimited tier
        # absorbs all units and later tiers are unreachable on the chart.
        data = self._chart_data()
        # The last marginal rate should be tier1's unitPrice (10), not tier2/3
        self.assertEqual(data["current"][-1], 10)

        self._reload()

    def test_18_multiplier_cost_calculation(self):
        """Verify cost is correct: each repetition charges price + billable * unitPrice."""
        self._reload()
        # Use JS to directly test the calculation engine with known tiers
        result = self.driver.execute_script("""
            // Single tier: units=100, price=10, unitPrice=2, freeUnits=0, multiplier=3
            const container = document.createElement('div');
            document.body.appendChild(container);
            const mod = await import('./pricing-component.js');
            const comp = new mod.PricingComponent(container, [
                { sequence: 1, units: 100, price: 10, unitPrice: 2, freeUnits: 0, multiplier: 3 }
            ]);
            const data = comp.calculate();
            document.body.removeChild(container);

            // At 300 units (full 3 reps): 3 * (10 + 100*2) = 630
            const lastLabel = data.labels[data.labels.length - 1];
            const lastCum = data.cumulative[data.cumulative.length - 1];
            return { lastLabel, lastCum };
        """)
        self.assertEqual(result["lastLabel"], 300)
        self.assertEqual(result["lastCum"], 630)

        self._reload()

    def test_19_sliders_present_for_all_fields(self):
        """Each tier row has a slider for every field."""
        self._reload()
        sliders = self._get_tier_sliders()
        self.assertEqual(len(sliders), 3)
        for s in sliders:
            for field in ("units", "price", "unitPrice", "freeUnits", "multiplier"):
                self.assertIn(field, s, f"Missing slider for {field}")

    def test_20_slider_syncs_to_number_input(self):
        """Moving a slider updates the corresponding number input and chart."""
        self._reload()
        data_before = self._chart_data()
        sliders = self._get_tier_sliders()
        inputs = self._get_tier_inputs()

        # Change units slider for tier 1 via JS (Selenium can't drag range natively)
        slider = sliders[0]["units"]
        self.driver.execute_script(
            "arguments[0].value = 500;"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            slider,
        )
        time.sleep(0.3)

        # Number input should reflect the new value
        self.assertEqual(inputs[0]["units"].get_attribute("value"), "500")

        # Chart should have changed
        data_after = self._chart_data()
        self.assertNotEqual(data_before["labels"][-1], data_after["labels"][-1])

        self._reload()

    def test_21_number_input_syncs_to_slider(self):
        """Typing in a number input updates the corresponding slider."""
        self._reload()
        inputs = self._get_tier_inputs()
        sliders = self._get_tier_sliders()

        inputs[0]["units"].clear()
        inputs[0]["units"].send_keys("800")
        time.sleep(0.3)

        slider_val = sliders[0]["units"].get_attribute("value")
        self.assertEqual(slider_val, "800")

        self._reload()

    def test_22_multiplier_slider_sets_infinity(self):
        """Dragging multiplier slider to max sets multiplier to infinity."""
        self._reload()
        sliders = self._get_tier_sliders()
        inputs = self._get_tier_inputs()

        slider = sliders[0]["multiplier"]
        self.driver.execute_script(
            "arguments[0].value = 10;"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            slider,
        )
        time.sleep(0.3)

        self.assertEqual(inputs[0]["multiplier"].get_attribute("value"), "\u221e")

        self._reload()

    def test_23_multiplier_slider_sets_number(self):
        """Moving multiplier slider to a numeric position updates text input."""
        self._reload()
        sliders = self._get_tier_sliders()
        inputs = self._get_tier_inputs()

        # Tier 3 multiplier is ∞ (slider=10). Set to 3.
        slider = sliders[2]["multiplier"]
        self.driver.execute_script(
            "arguments[0].value = 3;"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            slider,
        )
        time.sleep(0.3)

        self.assertEqual(inputs[2]["multiplier"].get_attribute("value"), "3")

        self._reload()

    def test_24_currency_selector_present(self):
        """Currency dropdown exists with common currencies."""
        self._reload()
        select = self.driver.find_element(By.ID, "currency-select")
        options = select.find_elements(By.TAG_NAME, "option")
        codes = [o.get_attribute("value") for o in options]
        for code in ("USD", "EUR", "GBP", "JPY", "CHF"):
            self.assertIn(code, codes)
        # Default is USD
        self.assertEqual(select.get_attribute("value"), "USD")

    def test_25_currency_selector_defaults_dollar(self):
        """Chart axis labels default to $ symbol."""
        self._reload()
        axis_label = self.driver.execute_script(
            "const chart = Chart.instances[Object.keys(Chart.instances)[0]];"
            "return chart.options.scales.yCumulative.title.text;"
        )
        self.assertIn("$", axis_label)

    def test_26_change_currency_updates_chart(self):
        """Selecting a different currency updates chart axis labels."""
        self._reload()
        select = self.driver.find_element(By.ID, "currency-select")
        select.click()
        for option in select.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == "EUR":
                option.click()
                break
        time.sleep(0.3)

        axis_label = self.driver.execute_script(
            "const chart = Chart.instances[Object.keys(Chart.instances)[0]];"
            "return chart.options.scales.yCumulative.title.text;"
        )
        self.assertIn("\u20ac", axis_label)  # €

        # Restore USD
        select = self.driver.find_element(By.ID, "currency-select")
        select.click()
        for option in select.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == "USD":
                option.click()
                break
        time.sleep(0.3)

    def test_27_mrr_and_discount_inputs_present(self):
        """MRR and Discount inputs and sliders exist."""
        self._reload()
        for el_id in ("mrr-input", "mrr-slider", "discount-input", "discount-slider"):
            el = self.driver.find_element(By.ID, el_id)
            self.assertIsNotNone(el)

    def test_28_mrr_sets_minimum_price(self):
        """MRR acts as a price floor — cumulative never drops below it."""
        self._reload()
        mrr_input = self.driver.find_element(By.ID, "mrr-input")
        mrr_input.clear()
        mrr_input.send_keys("5000")
        time.sleep(0.3)

        data = self._chart_data()
        # At 0 units, cumulative = MRR = 5000
        self.assertEqual(data["cumulative"][0], 5000)
        # All values should be >= MRR
        for val in data["cumulative"]:
            self.assertGreaterEqual(val, 5000)
        # Marginal rate should be 0 while usage is below MRR floor
        self.assertEqual(data["current"][0], 0)

        self._reload()

    def test_29_discount_reduces_cumulative(self):
        """Setting a discount reduces cumulative price."""
        self._reload()
        data_before = self._chart_data()

        disc_input = self.driver.find_element(By.ID, "discount-input")
        disc_input.clear()
        disc_input.send_keys("50")
        time.sleep(0.3)

        data_after = self._chart_data()
        # Cumulative at max should be roughly half
        self.assertAlmostEqual(
            data_after["cumulative"][-1],
            data_before["cumulative"][-1] / 2,
            delta=1,
        )

        self._reload()

    def test_30_mrr_slider_syncs_input(self):
        """MRR slider updates the number input."""
        self._reload()
        slider = self.driver.find_element(By.ID, "mrr-slider")
        inp = self.driver.find_element(By.ID, "mrr-input")

        self.driver.execute_script(
            "arguments[0].value = 200;"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            slider,
        )
        time.sleep(0.3)

        self.assertEqual(inp.get_attribute("value"), "200")
        self._reload()

    def test_31_discount_slider_syncs_input(self):
        """Discount slider updates the number input."""
        self._reload()
        slider = self.driver.find_element(By.ID, "discount-slider")
        inp = self.driver.find_element(By.ID, "discount-input")

        self.driver.execute_script(
            "arguments[0].value = 25;"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            slider,
        )
        time.sleep(0.3)

        self.assertEqual(inp.get_attribute("value"), "25")
        self._reload()

    def test_32_discount_affects_marginal_rate(self):
        """Discount reduces the marginal rate proportionally."""
        self._reload()
        data_before = self._chart_data()
        # Find a non-zero marginal rate
        rate_before = None
        for v in data_before["current"]:
            if v > 0:
                rate_before = v
                break
        self.assertIsNotNone(rate_before)

        disc_input = self.driver.find_element(By.ID, "discount-input")
        disc_input.clear()
        disc_input.send_keys("50")
        time.sleep(0.3)

        data_after = self._chart_data()
        rate_after = None
        for v in data_after["current"]:
            if v > 0:
                rate_after = v
                break
        self.assertAlmostEqual(rate_after, rate_before / 2, delta=0.1)

        self._reload()

    def test_33_export_import_buttons_present(self):
        """Export and Import buttons exist."""
        self._reload()
        export_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn-export")
        import_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn-import")
        self.assertEqual(export_btn.text, "Export JSON")
        self.assertEqual(import_btn.text, "Import JSON")

    def test_34_to_json_returns_config(self):
        """toJSON() returns current state with tiers, currency, mrr, discount."""
        self._reload()
        config = self.driver.execute_script("""
            const comp = document.querySelector('#pricing-container').__pricingComponent;
            // Attach reference for test access
            return null;
        """)
        # Use the component directly via JS on the page
        config = self.driver.execute_script("""
            const container = document.createElement('div');
            document.body.appendChild(container);
            const mod = await import('./pricing-component.js');
            const comp = new mod.PricingComponent(container);
            comp.mrr = 200;
            comp.discount = 15;
            const json = comp.toJSON();
            document.body.removeChild(container);
            return json;
        """)
        self.assertEqual(config["currency"], "USD")
        self.assertEqual(config["mrr"], 200)
        self.assertEqual(config["discount"], 15)
        self.assertEqual(len(config["tiers"]), 3)
        # Infinity serialized as 'infinity'
        self.assertEqual(config["tiers"][2]["multiplier"], "infinity")

    def test_35_load_json_restores_config(self):
        """loadJSON() restores tiers, currency, mrr, discount."""
        self._reload()
        result = self.driver.execute_script("""
            const container = document.createElement('div');
            document.body.appendChild(container);
            const mod = await import('./pricing-component.js');
            const comp = new mod.PricingComponent(container);
            comp.loadJSON({
                currency: 'EUR',
                mrr: 500,
                discount: 10,
                tiers: [
                    { sequence: 1, units: 50, price: 5, unitPrice: 2, freeUnits: 0, multiplier: 'infinity' }
                ]
            });
            const json = comp.toJSON();
            document.body.removeChild(container);
            return json;
        """)
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["mrr"], 500)
        self.assertEqual(result["discount"], 10)
        self.assertEqual(len(result["tiers"]), 1)
        self.assertEqual(result["tiers"][0]["units"], 50)
        self.assertEqual(result["tiers"][0]["multiplier"], "infinity")


if __name__ == "__main__":
    unittest.main()
