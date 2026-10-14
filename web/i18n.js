/* i18n plus money/number formatting. No network, no dependencies.
 *
 * Every user-visible string lives here. Static markup carries a
 * data-i18n="key" attribute; app.js applies the dictionary on load and
 * whenever the language changes. Dynamically generated text calls I18n.t().
 */
(function (global) {
  var STRINGS = {
    id: {
      "app.title": "Kalkulator Porto",

      "tab.invest": "Investasi",
      "tab.portfolio": "Portofolio",
      "tab.trading": "Trading",
      "tab.simulate": "Simulasi",

      "header.currency": "Mata uang",
      "header.language": "Bahasa",

      "label.total_return": "Total imbal hasil (%)",
      "label.years": "Tahun",
      "label.monthly": "Setoran bulanan",
      "label.annual_roi": "ROI tahunan (%)",
      "label.months": "Bulan",
      "label.preset": "Preset strategi",
      "label.fee_model": "Model fee",
      "label.leverage": "Leverage",
      "label.capital": "Modal",
      "label.trades": "Jumlah trade",
      "label.notional": "Notional (USD)",
      "label.reward": "Reward (USD)",
      "label.risk": "Risk (USD)",
      "label.win_rate_from": "Win rate dari (%)",
      "label.win_rate_to": "Win rate sampai (%)",
      "label.win_rate": "Win rate",
      "label.risk_pct": "Risiko per trade (%)",
      "label.stop_pct": "Jarak stop (%)",
      "label.rr": "Reward : risiko",
      "label.sims": "Jumlah simulasi",
      "label.bust_pct": "Batas bangkrut (% modal)",
      "label.slippage": "Slippage (%)",

      "th.year": "Tahun",
      "th.contributed": "Disetor",
      "th.value": "Nilai",
      "th.return": "Imbal hasil",
      "th.asset": "Aset",
      "th.weight": "Bobot (%)",
      "th.roi": "ROI tahunan (%)",
      "th.wr": "WR",
      "th.mean_net": "Rata-rata net",
      "th.p_success": "P(sukses)",
      "th.p_busted": "P(bangkrut)",
      "th.max_dd": "Max DD",
      "th.expectancy": "Ekspektansi",
      "th.sharpe": "Sharpe",

      "card.cagr": "CAGR",
      "card.future_value": "Nilai akhir",
      "card.invested": "Total modal",
      "card.return": "Total imbal hasil",
      "card.total": "Total",
      "card.ev": "Nilai harapan",
      "card.breakeven": "WR impas",
      "card.pf": "Profit factor",
      "card.sharpe": "Sharpe",
      "card.net": "Laba bersih",
      "card.fee": "Fee per trade",
      "card.liq": "Jarak likuidasi",
      "card.best_net": "Terbaik (laba)",
      "card.ruin": "Risiko bangkrut",
      "card.notional": "Ukuran posisi",
      "card.kelly": "Risiko Kelly",

      "note.per_year": "per tahun",
      "note.per_trade": "per trade",
      "note.not_annualised": "per trade, tidak disetahunkan",
      "note.price_move": "pergerakan harga",
      "note.trades": "trade",
      "note.half_kelly": "setengah",

      "btn.add_asset": "+ Tambah aset",


      "sub.invest": "CAGR dan nilai akhir setoran berkala.",
      "sub.portfolio": "Bagi setoran bulanan ke beberapa aset, masing-masing dengan ROI sendiri.",
      "sub.trading": "Nilai harapan, win rate impas, dan risiko likuidasi. Nilai dalam USD.",
      "sub.simulate": "Strategi manual, disapu lintas win rate dengan simulasi Monte Carlo. Nilai dalam USD.",

      "alert.liq": "Peringatan: jarak likuidasi hampir sama dengan stop loss. Satu candle buruk bisa melikuidasi posisi.",
      "sum.ok": "Total bobot OK",
      "sum.bad": "Total bobot harus 100%",
      "opt.futures": "Futures (0,05% x2 + 0,03%)",
      "opt.spot": "Spot (0,5% x2, minimum $0,95)"
    },
    en: {
      "app.title": "Porto Calculator",

      "tab.invest": "Invest",
      "tab.portfolio": "Portfolio",
      "tab.trading": "Trading",
      "tab.simulate": "Simulate",

      "header.currency": "Currency",
      "header.language": "Language",

      "label.total_return": "Total return (%)",
      "label.years": "Years",
      "label.monthly": "Monthly amount",
      "label.annual_roi": "Annual ROI (%)",
      "label.months": "Months",
      "label.preset": "Strategy preset",
      "label.fee_model": "Fee model",
      "label.leverage": "Leverage",
      "label.capital": "Capital",
      "label.trades": "Trades",
      "label.notional": "Notional (USD)",
      "label.reward": "Reward (USD)",
      "label.risk": "Risk (USD)",
      "label.win_rate_from": "Win rate from (%)",
      "label.win_rate_to": "Win rate to (%)",
      "label.win_rate": "Win rate",
      "label.risk_pct": "Risk per trade (%)",
      "label.stop_pct": "Stop distance (%)",
      "label.rr": "Reward : risk",
      "label.sims": "Simulations",
      "label.bust_pct": "Bust level (% of capital)",
      "label.slippage": "Slippage (%)",

      "th.year": "Year",
      "th.contributed": "Contributed",
      "th.value": "Value",
      "th.return": "Return",
      "th.asset": "Asset",
      "th.weight": "Weight (%)",
      "th.roi": "Annual ROI (%)",
      "th.wr": "WR",
      "th.mean_net": "Mean net",
      "th.p_success": "P(success)",
      "th.p_busted": "P(busted)",
      "th.max_dd": "Max DD",
      "th.expectancy": "Expectancy",
      "th.sharpe": "Sharpe",

      "card.cagr": "CAGR",
      "card.future_value": "Future value",
      "card.invested": "Total invested",
      "card.return": "Total return",
      "card.total": "Total",
      "card.ev": "Expected value",
      "card.breakeven": "Break-even WR",
      "card.pf": "Profit factor",
      "card.sharpe": "Sharpe",
      "card.net": "Net profit",
      "card.fee": "Fee per trade",
      "card.liq": "Liquidation distance",
      "card.best_net": "Best by net",
      "card.ruin": "Ruin risk",
      "card.notional": "Position size",
      "card.kelly": "Kelly risk",

      "note.per_year": "per year",
      "note.per_trade": "per trade",
      "note.not_annualised": "per trade, not annualised",
      "note.price_move": "price move",
      "note.trades": "trades",
      "note.half_kelly": "half",

      "btn.add_asset": "+ Add asset",


      "sub.invest": "CAGR and dollar-cost-averaging future value.",
      "sub.portfolio": "Split a monthly contribution across assets, each with its own expected ROI.",
      "sub.trading": "Expected value, break-even win rate, and liquidation risk. Amounts in USD.",
      "sub.simulate": "Manual strategy, swept across win rates with a Monte Carlo simulation. Amounts in USD.",

      "alert.liq": "Warning: liquidation distance is nearly the same as the stop loss. One bad candle can liquidate the position.",
      "sum.ok": "Weights sum to 100%",
      "sum.bad": "Weights must sum to 100%",
      "opt.futures": "Futures (0.05% x2 + 0.03%)",
      "opt.spot": "Spot (0.5% x2, $0.95 floor)"
    }
  };

  var lang = "id";
  var currency = "IDR";

  function t(key) {
    var table = STRINGS[lang] || STRINGS.en;
    if (table[key] !== undefined) return table[key];
    if (STRINGS.en[key] !== undefined) return STRINGS.en[key];
    return key;
  }

  function setLang(v) { lang = v; }
  function getLang() { return lang; }
  function setCurrency(v) { currency = v; }
  function getCurrency() { return currency; }

  function formatMoney(value) {
    if (value === null || value === undefined || isNaN(value)) return "-";
    try {
      return new Intl.NumberFormat(currency === "IDR" ? "id-ID" : "en-US", {
        style: "currency",
        currency: currency,
        maximumFractionDigits: currency === "IDR" ? 0 : 2,
        minimumFractionDigits: 0
      }).format(value);
    } catch (e) {
      return String(Math.round(value));
    }
  }

  /* Trading and simulation amounts are USD-denominated in the source model. */
  function formatUSD(value, digits) {
    if (value === null || value === undefined || isNaN(value)) return "-";
    try {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: digits === undefined ? 2 : digits,
        minimumFractionDigits: 0
      }).format(value);
    } catch (e) {
      return "$" + formatNumber(value, 2);
    }
  }

  function formatNumber(value, digits) {
    if (value === null || value === undefined || isNaN(value)) return "-";
    var d = digits === undefined ? 2 : digits;
    return new Intl.NumberFormat(lang === "id" ? "id-ID" : "en-US", {
      maximumFractionDigits: d,
      minimumFractionDigits: 0
    }).format(value);
  }

  function formatPercent(value, digits) {
    if (value === null || value === undefined || isNaN(value)) return "-";
    return formatNumber(value, digits === undefined ? 2 : digits) + "%";
  }

  function compact(value) {
    var abs = Math.abs(value);
    if (abs >= 1e12) return formatNumber(value / 1e12, 1) + "T";
    if (abs >= 1e9) return formatNumber(value / 1e9, 1) + "B";
    if (abs >= 1e6) return formatNumber(value / 1e6, 1) + "M";
    if (abs >= 1e3) return formatNumber(value / 1e3, 1) + "K";
    return formatNumber(value, 0);
  }

  /* Fill every [data-i18n] element from the dictionary. */
  function apply(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute("data-i18n");
      var attr = nodes[i].getAttribute("data-i18n-attr");
      if (attr) nodes[i].setAttribute(attr, t(key));
      else nodes[i].textContent = t(key);
    }
    var titleNodes = scope.querySelectorAll("[data-i18n-title]");
    for (var j = 0; j < titleNodes.length; j++) {
      document.title = t(titleNodes[j].getAttribute("data-i18n-title"));
    }
  }

  global.I18n = {
    t: t,
    apply: apply,
    setLang: setLang,
    getLang: getLang,
    setCurrency: setCurrency,
    getCurrency: getCurrency,
    formatMoney: formatMoney,
    formatUSD: formatUSD,
    formatNumber: formatNumber,
    formatPercent: formatPercent,
    compact: compact,
    keys: function () { return Object.keys(STRINGS.en); }
  };
})(window);
