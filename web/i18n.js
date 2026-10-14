/* Minimal i18n plus money/number formatting. No network, no dependencies. */
(function (global) {
  var STRINGS = {
    id: {
      "tab.invest": "Investasi",
      "tab.portfolio": "Portofolio",
      "tab.trading": "Trading",
      "tab.simulate": "Simulasi",
      "card.cagr": "CAGR",
      "card.future_value": "Nilai akhir",
      "card.invested": "Total modal",
      "card.return": "Total imbal hasil",
      "card.total": "Total",
      "card.net": "Laba bersih",
      "card.sharpe": "Sharpe",
      "card.breakeven": "WR impas",
      "card.pf": "Profit factor",
      "card.fee": "Fee per trade",
      "card.ev": "Nilai harapan",
      "card.liq": "Jarak likuidasi",
      "alert.liq": "Peringatan: jarak likuidasi hampir sama dengan stop loss. Satu candle buruk bisa melikuidasi posisi.",
      "sum.ok": "Total bobot OK",
      "sum.bad": "Total bobot harus 100%"
    },
    en: {
      "tab.invest": "Invest",
      "tab.portfolio": "Portfolio",
      "tab.trading": "Trading",
      "tab.simulate": "Simulate",
      "card.cagr": "CAGR",
      "card.future_value": "Future value",
      "card.invested": "Total invested",
      "card.return": "Total return",
      "card.total": "Total",
      "card.net": "Net profit",
      "card.sharpe": "Sharpe",
      "card.breakeven": "Break-even WR",
      "card.pf": "Profit factor",
      "card.fee": "Fee per trade",
      "card.ev": "Expected value",
      "card.liq": "Liquidation distance",
      "alert.liq": "Warning: liquidation distance is nearly the same as the stop loss. One bad candle can liquidate the position.",
      "sum.ok": "Weights sum to 100%",
      "sum.bad": "Weights must sum to 100%"
    }
  };

  var lang = "id";
  var currency = "IDR";

  function t(key) {
    var table = STRINGS[lang] || STRINGS.en;
    return table[key] !== undefined ? table[key] : (STRINGS.en[key] || key);
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

  global.I18n = {
    t: t,
    setLang: setLang,
    getLang: getLang,
    setCurrency: setCurrency,
    getCurrency: getCurrency,
    formatMoney: formatMoney,
    formatUSD: formatUSD,
    formatNumber: formatNumber,
    formatPercent: formatPercent,
    compact: compact
  };
})(window);
