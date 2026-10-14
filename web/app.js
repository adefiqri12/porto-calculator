/* App wiring. All math comes from the API; this file only moves data around. */
(function () {
  "use strict";

  var $ = function (sel) { return document.querySelector(sel); };

  function num(sel) {
    var v = parseFloat($(sel).value);
    return isNaN(v) ? 0 : v;
  }

  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms === undefined ? 150 : ms);
    };
  }

  function postJSON(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!r.ok) {
          var detail = data && data.detail ? data.detail : r.statusText;
          if (Array.isArray(detail)) {
            detail = detail.map(function (d) {
              return (d.loc ? d.loc.join(".") + ": " : "") + d.msg;
            }).join("\n");
          }
          var err = new Error(String(detail));
          err.status = r.status;
          throw err;
        }
        return data;
      });
    });
  }

  function showErr(sel, msg) { $(sel).textContent = msg || ""; }

  function card(title, value, note, cls) {
    return '<div class="card"><h4>' + title + '</h4>' +
      '<div class="big ' + (cls || "") + '">' + value + '</div>' +
      (note ? '<div class="note">' + note + '</div>' : "") + '</div>';
  }

  var money = function (v) { return I18n.formatMoney(v); };
  // Trading and simulation amounts are USD-denominated in the source model
  // (fees and margins are in dollars), so they are always shown as USD.
  var usd = function (v, d) { return I18n.formatUSD(v, d); };
  var pct = function (v, d) { return I18n.formatPercent(v, d === undefined ? 2 : d); };
  var numf = function (v, d) { return I18n.formatNumber(v, d === undefined ? 2 : d); };

  /* ---------------- tabs ---------------- */

  function setTab(name) {
    var tabs = document.querySelectorAll(".tab");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle("is-active", tabs[i].getAttribute("data-tab") === name);
    }
    var panels = document.querySelectorAll(".panel");
    for (var j = 0; j < panels.length; j++) {
      panels[j].classList.toggle("is-active", panels[j].id === "panel-" + name);
    }
    if (name === "Invest") renderInvest();
    if (name === "Portfolio") renderPortfolio();
    if (name === "Trading") renderTrading();
    if (name === "Simulate") renderSimulate();
  }

  /* ---------------- invest ---------------- */

  function renderInvest() {
    showErr("#invest-err", "");
    var dcaBody = {
      monthly: num("#dca-monthly"),
      annual_roi_pct: num("#dca-roi"),
      months: Math.max(0, Math.round(num("#dca-months")))
    };
    var cagrBody = {
      total_return_pct: num("#cagr-return"),
      years: num("#cagr-years")
    };

    var cagrReq = cagrBody.years > 0
      ? postJSON("/api/cagr", cagrBody).catch(function () { return { cagr_pct: null }; })
      : Promise.resolve({ cagr_pct: null });

    cagrReq.then(function (cagrRes) {
      return postJSON("/api/dca", dcaBody).then(function (dcaRes) {
        $("#invest-cards").innerHTML =
          card("CAGR", cagrRes.cagr_pct === null ? "-" : pct(cagrRes.cagr_pct), "per year", "a") +
          card("Future value", money(dcaRes.future_value), "", "b") +
          card("Total invested", money(dcaRes.total_invested), "", "") +
          card("Total return", money(dcaRes.total_return), "", "c");

        var rows = dcaRes.yearly.map(function (r) {
          return "<tr><td>" + r.year + "</td><td class='num'>" + money(r.contributed) +
            "</td><td class='num'>" + money(r.value) +
            "</td><td class='num win'>" + money(r["return"]) + "</td></tr>";
        }).join("");
        $("#invest-table tbody").innerHTML = rows || "<tr><td colspan='4'>-</td></tr>";

        var labels = dcaRes.yearly.map(function (r) { return "Y" + r.year; });
        if (labels.length) {
          Charts.barChart($("#invest-chart"), labels, [
            { name: "Contributed", color: "#58a6ff", values: dcaRes.yearly.map(function (r) { return r.contributed; }) },
            { name: "Value", color: "#3fb950", values: dcaRes.yearly.map(function (r) { return r.value; }) }
          ]);
        } else {
          Charts.barChart($("#invest-chart"), ["-"], [{ name: "Value", color: "#3fb950", values: [0] }]);
        }
      });
    }).catch(function (e) { showErr("#invest-err", e.message); });
  }

  /* ---------------- portfolio ---------------- */

  var pfHoldings = [
    { name: "BBCA", weight_pct: 60, annual_roi_pct: 12 },
    { name: "ETH", weight_pct: 40, annual_roi_pct: 24 }
  ];

  function pfSum() {
    return pfHoldings.reduce(function (a, h) { return a + (parseFloat(h.weight_pct) || 0); }, 0);
  }

  function renderPfRows() {
    var body = $("#pf-table tbody");
    body.innerHTML = pfHoldings.map(function (h, i) {
      return "<tr>" +
        "<td><input type='text' data-i='" + i + "' data-k='name' value='" + h.name + "'></td>" +
        "<td class='num'><input type='number' step='any' data-i='" + i + "' data-k='weight_pct' value='" + h.weight_pct + "'></td>" +
        "<td class='num'><input type='number' step='any' data-i='" + i + "' data-k='annual_roi_pct' value='" + h.annual_roi_pct + "'></td>" +
        "<td class='num'><button class='btn icon' data-rm='" + i + "'>x</button></td>" +
        "</tr>";
    }).join("");

    var sum = pfSum();
    var ok = Math.abs(sum - 100) <= 0.01;
    var el = $("#pf-sum");
    el.textContent = (ok ? I18n.t("sum.ok") : I18n.t("sum.bad")) + " (" + numf(sum, 2) + "%)";
    el.classList.toggle("ok", ok);
    el.classList.toggle("bad", !ok);

    body.querySelectorAll("input").forEach(function (inp) {
      inp.addEventListener("input", function () {
        var i = parseInt(inp.getAttribute("data-i"), 10);
        var k = inp.getAttribute("data-k");
        pfHoldings[i][k] = k === "name" ? inp.value : (parseFloat(inp.value) || 0);
        var s = pfSum();
        var good = Math.abs(s - 100) <= 0.01;
        el.textContent = (good ? I18n.t("sum.ok") : I18n.t("sum.bad")) + " (" + numf(s, 2) + "%)";
        el.classList.toggle("ok", good);
        el.classList.toggle("bad", !good);
      });
    });
    body.querySelectorAll("[data-rm]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        pfHoldings.splice(parseInt(btn.getAttribute("data-rm"), 10), 1);
        renderPfRows();
        renderPortfolio();
      });
    });
  }

  function renderPortfolio() {
    showErr("#pf-err", "");
    if (!$("#pf-table tbody").children.length) renderPfRows();
    if (Math.abs(pfSum() - 100) > 0.01) return;

    postJSON("/api/portfolio", {
      monthly: num("#pf-monthly"),
      months: Math.max(0, Math.round(num("#pf-months"))),
      holdings: pfHoldings.map(function (h) {
        return { name: h.name, weight_pct: parseFloat(h.weight_pct) || 0, annual_roi_pct: parseFloat(h.annual_roi_pct) || 0 };
      })
    }).then(function (res) {
      $("#pf-cards").innerHTML =
        card("Total", money(res.total_fv), "", "b") +
        res.per_asset.map(function (a) {
          return card(a.name + " (" + numf(a.weight_pct, 0) + "%)", money(a.future_value), "", "");
        }).join("");
      Charts.barChart($("#pf-chart"),
        res.per_asset.map(function (a) { return a.name; }),
        [{ name: "Future value", color: "#58a6ff", values: res.per_asset.map(function (a) { return a.future_value; }) }]);
    }).catch(function (e) { showErr("#pf-err", e.message); });
  }

  /* ---------------- trading ---------------- */

  var presets = null;

  function loadPresets() {
    return fetch("/api/presets").then(function (r) { return r.json(); }).then(function (data) {
      presets = data;
      var sel = $("#tr-preset");
      sel.innerHTML = Object.keys(data).map(function (k) {
        return "<option value='" + k + "'>" + data[k].label + "</option>";
      }).join("");
      sel.addEventListener("change", function () {
        var p = data[sel.value];
        $("#tr-reward").value = p.reward;
        $("#tr-risk").value = p.risk;
        $("#tr-lev").value = p.leverage;
        $("#tr-fee").value = p.fee_model;
        renderTrading();
      });
    });
  }

  function renderTrading() {
    showErr("#tr-err", "");
    var wr = num("#tr-wr");
    $("#tr-wr-val").textContent = numf(wr, 0) + "%";

    postJSON("/api/trading", {
      win_rate_pct: wr,
      reward: num("#tr-reward"),
      risk: num("#tr-risk"),
      leverage: num("#tr-lev"),
      fee_model: $("#tr-fee").value,
      capital: num("#tr-capital"),
      trades: Math.max(1, Math.round(num("#tr-trades"))),
      notional: num("#tr-notional")
    }).then(function (res) {
      var netCls = res.net_profit >= 0 ? "win" : "lose";
      $("#tr-cards").innerHTML =
        card("Expected value", numf(res.expected_value, 3), "per trade", "a") +
        card("Break-even WR", pct(res.break_even_win_rate_pct, 1), "", "c") +
        card("Profit factor", numf(res.profit_factor, 3), "", "") +
        card("Sharpe", numf(res.sharpe, 3), "per trade, not annualised", "b") +
        card("Net profit", usd(res.net_profit), numf(num("#tr-trades"), 0) + " trades", netCls) +
        card("Fee per trade", usd(res.fee_per_trade, 4), "", "") +
        card("Liquidation distance", pct(res.liquidation_distance_pct, 1), "price move", "warnc");

      var marker = $("#tr-marker");
      marker.style.left = "calc(2px + (100% - 4px) * " + (res.break_even_win_rate_pct / 100) + ")";
      var ml = $("#tr-marker-label");
      ml.style.left = "calc(2px + (100% - 4px) * " + (res.break_even_win_rate_pct / 100) + ")";
      ml.textContent = "BE " + numf(res.break_even_win_rate_pct, 1) + "%";

      var alert = $("#tr-alert");
      if (res.liquidation_warning) {
        alert.textContent = I18n.t("alert.liq") +
          " (liq " + numf(res.liquidation_distance_pct, 1) + "%)";
        alert.classList.add("show");
      } else {
        alert.classList.remove("show");
        alert.textContent = "";
      }
    }).catch(function (e) { showErr("#tr-err", e.message); });
  }

  /* ---------------- simulate ---------------- */

  function range(min, max, step) {
    var out = [];
    for (var v = min; v <= max + 1e-9; v += step) out.push(Math.round(v * 100) / 100);
    return out;
  }

  function renderSimulate() {
    showErr("#sim-err", "");
    var lo = num("#sim-min"), hi = num("#sim-max");
    if (hi < lo) { var t = lo; lo = hi; hi = t; }
    var step = Math.max(1, Math.round((hi - lo) / 8) || 1);
    var wrs = range(lo, hi, step);

    postJSON("/api/simulate", {
      preset: "A",
      win_rate_pcts: wrs,
      capital: num("#sim-capital"),
      trades: Math.max(1, Math.round(num("#sim-trades")))
    }).then(function (res) {
      $("#sim-cards").innerHTML =
        card("Best by Sharpe", res.best_by_sharpe.strategy, numf(res.best_by_sharpe.sharpe, 3), "a") +
        card("Best by net", res.best_by_net.strategy, usd(res.best_by_net.net), "b");

      $("#sim-table tbody").innerHTML = res.rows.map(function (r) {
        var cls = function (v) { return v >= 0 ? "win" : "lose"; };
        return "<tr><td>" + numf(r.wr, 0) + "%</td>" +
          "<td class='num " + cls(r.net_a) + "'>" + usd(r.net_a) + "</td>" +
          "<td class='num " + cls(r.net_b) + "'>" + usd(r.net_b) + "</td>" +
          "<td class='num " + cls(r.net_c) + "'>" + usd(r.net_c) + "</td>" +
          "<td class='num'>" + usd(r.gross_a) + "</td>" +
          "<td class='num'>" + usd(r.gross_c) + "</td>" +
          "<td class='num'>" + numf(r.sh_a, 3) + "</td>" +
          "<td class='num'>" + numf(r.sh_c, 3) + "</td></tr>";
      }).join("");

      Charts.lineChart($("#sim-chart"),
        res.rows.map(function (r) { return numf(r.wr, 0) + "%"; }),
        [
          { name: "A", color: "#58a6ff", values: res.rows.map(function (r) { return r.net_a; }) },
          { name: "B", color: "#3fb950", values: res.rows.map(function (r) { return r.net_b; }) },
          { name: "C", color: "#f0883e", values: res.rows.map(function (r) { return r.net_c; }) }
        ]);

      $("#sim-cap-table tbody").innerHTML = res.capital_rows.map(function (r) {
        return "<tr><td>" + usd(r.capital, 0) + "</td>" +
          "<td class='num'>" + usd(r.fixed_value) + "</td>" +
          "<td class='num'>" + usd(r.percent_value) + "</td>" +
          "<td class='num'>" + usd(r.compounding_value) + "</td></tr>";
      }).join("");
    }).catch(function (e) { showErr("#sim-err", e.message); });
  }

  /* ---------------- init ---------------- */

  function init() {
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () { setTab(btn.getAttribute("data-tab")); });
    });

    $("#currency").addEventListener("change", function (e) {
      I18n.setCurrency(e.target.value);
      setTab(document.querySelector(".tab.is-active").getAttribute("data-tab"));
    });
    $("#lang").addEventListener("change", function (e) {
      I18n.setLang(e.target.value);
      setTab(document.querySelector(".tab.is-active").getAttribute("data-tab"));
    });

    var reInvest = debounce(renderInvest);
    ["#cagr-return", "#cagr-years", "#dca-monthly", "#dca-roi", "#dca-months"].forEach(function (s) {
      $(s).addEventListener("input", reInvest);
    });

    var rePf = debounce(renderPortfolio);
    ["#pf-monthly", "#pf-months"].forEach(function (s) { $(s).addEventListener("input", rePf); });
    $("#pf-add").addEventListener("click", function () {
      pfHoldings.push({ name: "Asset", weight_pct: 0, annual_roi_pct: 10 });
      renderPfRows();
    });

    $("#tr-wr").addEventListener("input", function () {
      $("#tr-wr-val").textContent = numf(num("#tr-wr"), 0) + "%";
    });
    var reTr = debounce(renderTrading);
    ["#tr-wr", "#tr-fee", "#tr-lev", "#tr-capital", "#tr-trades", "#tr-notional", "#tr-reward", "#tr-risk"]
      .forEach(function (s) { $(s).addEventListener("input", reTr); });

    var reSim = debounce(renderSimulate);
    ["#sim-min", "#sim-max", "#sim-capital", "#sim-trades"].forEach(function (s) {
      $(s).addEventListener("input", reSim);
    });

    window.addEventListener("resize", debounce(function () {
      setTab(document.querySelector(".tab.is-active").getAttribute("data-tab"));
    }, 250));

    loadPresets().then(function () {
      setTab("Invest");
    }).catch(function () {
      setTab("Invest");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
