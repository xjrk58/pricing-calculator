export const CURRENCIES = [
  { code: 'USD', symbol: '$' },
  { code: 'EUR', symbol: '€' },
  { code: 'GBP', symbol: '£' },
  { code: 'JPY', symbol: '¥' },
  { code: 'CHF', symbol: 'CHF' },
  { code: 'CAD', symbol: 'CA$' },
  { code: 'AUD', symbol: 'A$' },
  { code: 'CNY', symbol: '¥' },
  { code: 'INR', symbol: '₹' },
  { code: 'BRL', symbol: 'R$' },
  { code: 'KRW', symbol: '₩' },
  { code: 'CZK', symbol: 'Kč' },
  { code: 'PLN', symbol: 'zł' },
];

export class PricingComponent {
  constructor(container, initialTiers, currency) {
    this.container = container;
    this.tiers = initialTiers || [
      { sequence: 1, units: 100, price: 0, unitPrice: 10, freeUnits: 10, multiplier: 1 },
      { sequence: 2, units: 200, price: 50, unitPrice: 7, freeUnits: 0, multiplier: 2 },
      { sequence: 3, units: 500, price: 0, unitPrice: 3, freeUnits: 0, multiplier: Infinity },
    ];
    this.currency = currency || CURRENCIES[0];
    this.discount = 0;
    this.mrr = 0;
    this.chart = null;
    this.render();
    this.updateChart();
  }

  render() {
    this.container.innerHTML = '';

    const configSection = document.createElement('div');
    configSection.className = 'pricing-config';

    const heading = document.createElement('h2');
    heading.textContent = 'Pricing Tier Configuration';
    configSection.appendChild(heading);

    const currencyRow = document.createElement('div');
    currencyRow.className = 'currency-row';
    const currLabel = document.createElement('label');
    currLabel.textContent = 'Currency: ';
    currLabel.htmlFor = 'currency-select';
    const currSelect = document.createElement('select');
    currSelect.id = 'currency-select';
    currSelect.className = 'currency-select';
    for (const c of CURRENCIES) {
      const opt = document.createElement('option');
      opt.value = c.code;
      opt.textContent = `${c.code} (${c.symbol})`;
      if (c.code === this.currency.code) opt.selected = true;
      currSelect.appendChild(opt);
    }
    currSelect.addEventListener('change', (e) => {
      this.currency = CURRENCIES.find((c) => c.code === e.target.value);
      this.updateChart();
    });
    currencyRow.appendChild(currLabel);
    currencyRow.appendChild(currSelect);
    configSection.appendChild(currencyRow);

    const globalsRow = document.createElement('div');
    globalsRow.className = 'globals-row';
    globalsRow.innerHTML = `
      <div class="global-field">
        <label for="mrr-input">MRR</label>
        <input type="number" id="mrr-input" value="${this.mrr}" min="0" step="1">
        <input type="range" id="mrr-slider" value="${Math.min(this.mrr, 5000)}" min="0" max="5000" step="10" class="field-slider">
      </div>
      <div class="global-field">
        <label for="discount-input">Discount %</label>
        <input type="number" id="discount-input" value="${this.discount}" min="0" max="100" step="0.1">
        <input type="range" id="discount-slider" value="${this.discount}" min="0" max="100" step="1" class="field-slider">
      </div>
    `;
    configSection.appendChild(globalsRow);

    const table = document.createElement('table');
    table.className = 'tier-table';

    const thead = document.createElement('thead');
    thead.innerHTML = `<tr>
      <th>Seq</th><th>Units</th><th>Price</th><th>Unit Price</th>
      <th>Free Units</th><th>Multiplier</th><th></th>
    </tr>`;
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    this.tiers
      .sort((a, b) => a.sequence - b.sequence)
      .forEach((tier, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = this.tierRowHTML(tier, index);
        tbody.appendChild(tr);
      });
    table.appendChild(tbody);
    configSection.appendChild(table);

    const actionsRow = document.createElement('div');
    actionsRow.className = 'actions-row';

    const addBtn = document.createElement('button');
    addBtn.className = 'btn btn-add';
    addBtn.textContent = '+ Add Tier';
    addBtn.addEventListener('click', () => this.addTier());
    actionsRow.appendChild(addBtn);

    const exportBtn = document.createElement('button');
    exportBtn.className = 'btn btn-export';
    exportBtn.textContent = 'Export JSON';
    exportBtn.addEventListener('click', () => this.exportConfig());
    actionsRow.appendChild(exportBtn);

    const importBtn = document.createElement('button');
    importBtn.className = 'btn btn-import';
    importBtn.textContent = 'Import JSON';
    importBtn.addEventListener('click', () => this.importConfig());
    actionsRow.appendChild(importBtn);

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.id = 'import-file-input';
    fileInput.style.display = 'none';
    fileInput.addEventListener('change', (e) => this.handleImportFile(e));
    actionsRow.appendChild(fileInput);

    configSection.appendChild(actionsRow);

    const chartSection = document.createElement('div');
    chartSection.className = 'pricing-chart';

    const chartHeading = document.createElement('h2');
    chartHeading.textContent = 'Pricing Chart';
    chartSection.appendChild(chartHeading);

    const chartWrap = document.createElement('div');
    chartWrap.style.position = 'relative';
    chartWrap.style.height = '400px';

    const canvas = document.createElement('canvas');
    canvas.id = 'pricing-chart-canvas';
    chartWrap.appendChild(canvas);
    chartSection.appendChild(chartWrap);

    this.container.appendChild(configSection);
    this.container.appendChild(chartSection);

    this.bindInputs();
  }

  tierRowHTML(tier, index) {
    const field = (name, value, step, sMin, sMax, sStep) => {
      const clamped = Math.min(Math.max(value, sMin), sMax);
      return `<td>
        <input type="number" data-index="${index}" data-field="${name}" value="${value}" step="${step || 1}" min="0">
        <input type="range" data-index="${index}" data-field="${name}" value="${clamped}" min="${sMin}" max="${sMax}" step="${sStep}" class="field-slider">
      </td>`;
    };
    const multDisplay = tier.multiplier === Infinity ? '∞' : tier.multiplier;
    const multSlider = tier.multiplier === Infinity ? 10 : Math.min(tier.multiplier, 9);
    return [
      `<td><input type="number" data-index="${index}" data-field="sequence" value="${tier.sequence}" step="1" min="0"></td>`,
      field('units', tier.units, 1, 0, 2000, 10),
      field('price', tier.price, 0.01, 0, 500, 1),
      field('unitPrice', tier.unitPrice, 0.01, 0, 50, 0.5),
      field('freeUnits', tier.freeUnits, 1, 0, 500, 1),
      `<td>
        <input type="text" data-index="${index}" data-field="multiplier" value="${multDisplay}" class="multiplier-input">
        <input type="range" data-index="${index}" data-field="multiplier" value="${multSlider}" min="1" max="10" step="1" class="field-slider">
      </td>`,
      `<td><button class="btn btn-remove" data-index="${index}">&times;</button></td>`,
    ].join('');
  }

  parseMultiplier(raw) {
    const v = raw.trim().toLowerCase();
    if (v === '∞' || v === 'inf' || v === 'infinity') return Infinity;
    const n = parseInt(v, 10);
    return Number.isFinite(n) && n >= 1 ? n : 1;
  }

  _findPeer(el, selector) {
    return el.closest('td').querySelector(selector);
  }

  bindInputs() {
    // Number inputs → update data + sync slider
    this.container.querySelectorAll('.tier-table input[type="number"]').forEach((input) => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index);
        const field = e.target.dataset.field;
        const val = parseFloat(e.target.value) || 0;
        this.tiers[idx][field] = val;
        const slider = this._findPeer(e.target, '.field-slider');
        if (slider) slider.value = Math.min(Math.max(val, +slider.min), +slider.max);
        this.updateChart();
      });
    });

    // Numeric sliders → update data + sync number input
    this.container.querySelectorAll('.field-slider:not([data-field="multiplier"])').forEach((slider) => {
      slider.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index);
        const field = e.target.dataset.field;
        const val = parseFloat(e.target.value);
        this.tiers[idx][field] = val;
        const numInput = this._findPeer(e.target, 'input[type="number"]');
        if (numInput) numInput.value = val;
        this.updateChart();
      });
    });

    // Multiplier text input → update data + sync slider
    this.container.querySelectorAll('.multiplier-input').forEach((input) => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index);
        this.tiers[idx].multiplier = this.parseMultiplier(e.target.value);
        const slider = this._findPeer(e.target, '.field-slider');
        if (slider) {
          const m = this.tiers[idx].multiplier;
          slider.value = m === Infinity ? 10 : Math.min(m, 9);
        }
        this.updateChart();
      });
    });

    // Multiplier slider → update data + sync text input
    this.container.querySelectorAll('.field-slider[data-field="multiplier"]').forEach((slider) => {
      slider.addEventListener('input', (e) => {
        const idx = parseInt(e.target.dataset.index);
        const val = parseInt(e.target.value);
        this.tiers[idx].multiplier = val >= 10 ? Infinity : val;
        const textInput = this._findPeer(e.target, '.multiplier-input');
        if (textInput) textInput.value = val >= 10 ? '∞' : val;
        this.updateChart();
      });
    });

    // MRR input + slider
    const mrrInput = this.container.querySelector('#mrr-input');
    const mrrSlider = this.container.querySelector('#mrr-slider');
    mrrInput.addEventListener('input', () => {
      this.mrr = parseFloat(mrrInput.value) || 0;
      mrrSlider.value = Math.min(Math.max(this.mrr, 0), 5000);
      this.updateChart();
    });
    mrrSlider.addEventListener('input', () => {
      this.mrr = parseFloat(mrrSlider.value);
      mrrInput.value = this.mrr;
      this.updateChart();
    });

    // Discount input + slider
    const discInput = this.container.querySelector('#discount-input');
    const discSlider = this.container.querySelector('#discount-slider');
    discInput.addEventListener('input', () => {
      this.discount = Math.min(Math.max(parseFloat(discInput.value) || 0, 0), 100);
      discSlider.value = this.discount;
      this.updateChart();
    });
    discSlider.addEventListener('input', () => {
      this.discount = parseFloat(discSlider.value);
      discInput.value = this.discount;
      this.updateChart();
    });

    this.container.querySelectorAll('.btn-remove').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.dataset.index);
        this.removeTier(idx);
      });
    });
  }

  addTier() {
    const maxSeq = this.tiers.reduce((m, t) => Math.max(m, t.sequence), 0);
    this.tiers.push({
      sequence: maxSeq + 1,
      units: 100,
      price: 0,
      unitPrice: 5,
      freeUnits: 0,
      multiplier: 1,
    });
    this.render();
    this.updateChart();
  }

  removeTier(index) {
    if (this.tiers.length <= 1) return;
    this.tiers.splice(index, 1);
    this.render();
    this.updateChart();
  }

  toJSON() {
    return {
      currency: this.currency.code,
      mrr: this.mrr,
      discount: this.discount,
      tiers: this.tiers.map((t) => ({
        ...t,
        multiplier: t.multiplier === Infinity ? 'infinity' : t.multiplier,
      })),
    };
  }

  loadJSON(config) {
    if (config.currency) {
      this.currency = CURRENCIES.find((c) => c.code === config.currency) || CURRENCIES[0];
    }
    if (typeof config.mrr === 'number') this.mrr = config.mrr;
    if (typeof config.discount === 'number') this.discount = config.discount;
    if (Array.isArray(config.tiers) && config.tiers.length > 0) {
      this.tiers = config.tiers.map((t) => ({
        ...t,
        multiplier: t.multiplier === 'infinity' || t.multiplier === Infinity ? Infinity : (t.multiplier || 1),
      }));
    }
    this.render();
    this.updateChart();
  }

  exportConfig() {
    const json = JSON.stringify(this.toJSON(), null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pricing-config.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  importConfig() {
    this.container.querySelector('#import-file-input').click();
  }

  handleImportFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const config = JSON.parse(reader.result);
        this.loadJSON(config);
      } catch {
        alert('Invalid JSON file');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }

  calculate() {
    const sorted = [...this.tiers].sort((a, b) => a.sequence - b.sequence);

    // Total units for chart x-axis. For unlimited tiers show 5 repetitions.
    let totalUnits = 0;
    for (const tier of sorted) {
      if (tier.units <= 0) continue;
      if (tier.multiplier === Infinity) {
        totalUnits += tier.units * 5;
      } else {
        totalUnits += tier.units * Math.max(1, tier.multiplier);
      }
    }
    if (totalUnits === 0) return { labels: [], cumulative: [], average: [], current: [] };

    const steps = Math.min(totalUnits, 1000);
    const stepSize = totalUnits / steps;

    const labels = [];
    const cumulative = [];
    const average = [];
    const current = [];

    for (let i = 0; i <= steps; i++) {
      const N = i * stepSize;
      labels.push(Math.round(N));

      let cumCost = 0;
      let remaining = N;
      let marginalRate = 0;

      for (const tier of sorted) {
        if (remaining <= 0) break;
        if (tier.units <= 0) continue;
        const maxReps = tier.multiplier === Infinity ? Infinity : Math.max(1, tier.multiplier);

        for (let rep = 0; rep < maxReps && remaining > 0; rep++) {
          const consumed = Math.min(remaining, tier.units);
          const billable = Math.max(0, consumed - tier.freeUnits);
          cumCost += tier.price + billable * tier.unitPrice;

          // If N falls within this repetition, record its marginal rate
          if (remaining <= tier.units) {
            marginalRate = consumed <= tier.freeUnits ? 0 : tier.unitPrice;
          }

          remaining -= consumed;
        }
      }

      const factor = 1 - this.discount / 100;
      const adjusted = Math.max(this.mrr, cumCost) * factor;
      const adjMarginal = (cumCost >= this.mrr ? marginalRate : 0) * factor;

      cumulative.push(Math.round(adjusted * 100) / 100);
      average.push(N > 0 && cumCost >= this.mrr ? Math.round((adjusted / N) * 100) / 100 : null);
      current.push(Math.round(adjMarginal * 100) / 100);
    }

    return { labels, cumulative, average, current };
  }

  updateChart() {
    const { labels, cumulative, average, current } = this.calculate();
    const canvas = this.container.querySelector('#pricing-chart-canvas');
    if (!canvas) return;

    if (this.chart) {
      this.chart.destroy();
    }

    this.chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Total Cumulative Price',
            data: cumulative,
            borderColor: '#0d6efd',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            pointHitRadius: 8,
            yAxisID: 'yCumulative',
          },
          {
            label: 'Average Unit Price',
            data: average,
            borderColor: '#059669',
            backgroundColor: 'rgba(5, 150, 105, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            pointHitRadius: 8,
            yAxisID: 'yRate',
          },
          {
            label: 'Current Price (Marginal)',
            data: current,
            borderColor: '#dc2626',
            backgroundColor: 'rgba(220, 38, 38, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            pointHitRadius: 8,
            stepped: true,
            yAxisID: 'yRate',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: (items) => `Units: ${items[0].label}`,
              label: (item) => `${item.dataset.label}: ${this.currency.symbol}${item.formattedValue}`,
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: 'Number of Units' },
            ticks: {
              maxTicksLimit: 12,
            },
          },
          yCumulative: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: `Cumulative Price (${this.currency.symbol})` },
            beginAtZero: true,
          },
          yRate: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: `Unit Price (${this.currency.symbol})` },
            beginAtZero: true,
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }
}
