/* Dependency-free canvas charts. Drawing only: all math comes from the API. */
(function (global) {
  var PAD = { top: 18, right: 16, bottom: 34, left: 62 };

  function setup(canvas) {
    var dpr = global.devicePixelRatio || 1;
    var cssW = canvas.clientWidth || canvas.parentNode.clientWidth || 640;
    var cssH = parseInt(canvas.getAttribute("height") || "260", 10);
    canvas.width = Math.max(1, Math.round(cssW * dpr));
    canvas.height = Math.max(1, Math.round(cssH * dpr));
    canvas.style.height = cssH + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    return { ctx: ctx, w: cssW, h: cssH };
  }

  function bounds(series) {
    var lo = Infinity, hi = -Infinity;
    series.forEach(function (s) {
      s.values.forEach(function (v) {
        if (v === null || isNaN(v)) return;
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      });
    });
    if (lo === Infinity) { lo = 0; hi = 1; }
    if (lo === hi) { hi = lo + 1; }
    if (lo > 0) lo = 0;
    if (hi < 0) hi = 0;
    return { lo: lo, hi: hi };
  }

  function axes(ctx, w, h, lo, hi, labels) {
    var plotW = w - PAD.left - PAD.right;
    var plotH = h - PAD.top - PAD.bottom;
    var range = hi - lo;
    ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    ctx.strokeStyle = "#2a3340";
    ctx.fillStyle = "#8b98a5";
    ctx.lineWidth = 1;

    var ticks = 5;
    for (var i = 0; i <= ticks; i++) {
      var v = lo + (range * i) / ticks;
      var y = PAD.top + plotH - (plotH * i) / ticks;
      ctx.beginPath();
      ctx.moveTo(PAD.left, Math.round(y) + 0.5);
      ctx.lineTo(w - PAD.right, Math.round(y) + 0.5);
      ctx.stroke();
      ctx.textAlign = "right";
      ctx.fillText(global.I18n.compact(v), PAD.left - 8, y);
    }

    if (lo < 0 && hi > 0) {
      var zeroY = PAD.top + plotH - (plotH * (0 - lo)) / range;
      ctx.strokeStyle = "#4a5563";
      ctx.beginPath();
      ctx.moveTo(PAD.left, Math.round(zeroY) + 0.5);
      ctx.lineTo(w - PAD.right, Math.round(zeroY) + 0.5);
      ctx.stroke();
    }

    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#8b98a5";
    var step = plotW / Math.max(1, labels.length);
    labels.forEach(function (lab, i) {
      ctx.fillText(String(lab), PAD.left + step * i + step / 2, h - PAD.bottom + 9);
    });
    return { plotW: plotW, plotH: plotH, range: range };
  }

  function legend(ctx, w, series) {
    var x = PAD.left;
    var y = 8;
    ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    series.forEach(function (s) {
      ctx.fillStyle = s.color;
      ctx.fillRect(x, y - 4, 9, 9);
      ctx.fillStyle = "#8b98a5";
      ctx.fillText(s.name, x + 14, y);
      x += 14 + ctx.measureText(s.name).width + 18;
    });
  }

  function yOf(v, lo, range, plotH) {
    return PAD.top + plotH - (plotH * (v - lo)) / range;
  }

  function barChart(canvas, labels, series) {
    var s = setup(canvas);
    var ctx = s.ctx;
    var b = bounds(series);
    var geo = axes(ctx, s.w, s.h, b.lo, b.hi, labels);
    var n = Math.max(1, labels.length);
    var groupW = geo.plotW / n;
    var barW = Math.max(2, (groupW * 0.72) / Math.max(1, series.length));

    series.forEach(function (ser, si) {
      ctx.fillStyle = ser.color;
      ser.values.forEach(function (v, i) {
        if (v === null || isNaN(v)) return;
        var zeroY = yOf(0, b.lo, geo.range, geo.plotH);
        var valY = yOf(v, b.lo, geo.range, geo.plotH);
        var x = PAD.left + groupW * i + groupW * 0.14 + barW * si;
        var top = Math.min(zeroY, valY);
        var height = Math.max(1, Math.abs(zeroY - valY));
        ctx.fillRect(x, top, barW, height);
      });
    });
    legend(ctx, s.w, series);
  }

  function lineChart(canvas, labels, series) {
    var s = setup(canvas);
    var ctx = s.ctx;
    var b = bounds(series);
    var geo = axes(ctx, s.w, s.h, b.lo, b.hi, labels);
    var n = Math.max(1, labels.length - 1);
    var step = geo.plotW / n;

    series.forEach(function (ser) {
      ctx.strokeStyle = ser.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      var started = false;
      ser.values.forEach(function (v, i) {
        if (v === null || isNaN(v)) return;
        var x = PAD.left + step * i;
        var y = yOf(v, b.lo, geo.range, geo.plotH);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else { ctx.lineTo(x, y); }
      });
      ctx.stroke();

      ctx.fillStyle = ser.color;
      ser.values.forEach(function (v, i) {
        if (v === null || isNaN(v)) return;
        var x = PAD.left + step * i;
        var y = yOf(v, b.lo, geo.range, geo.plotH);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    });
    legend(ctx, s.w, series);
  }

  global.Charts = { barChart: barChart, lineChart: lineChart };
})(window);
