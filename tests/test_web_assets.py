"""Static frontend contract: files present, no CDN, tabs wired, math not duplicated."""
import pathlib
import re

WEB = pathlib.Path("web")


def test_web_assets_exist():
    for name in ("index.html", "styles.css", "charts.js", "app.js", "i18n.js"):
        assert (WEB / name).is_file(), name


def test_no_cdn_links():
    # The app must work fully offline. data: URIs are inline by definition, so
    # strip them before scanning; the SVG namespace inside the favicon is not a
    # network fetch.
    for f in sorted(WEB.glob("*")):
        if f.suffix not in (".html", ".css", ".js"):
            continue
        text = re.sub(r'"data:[^"]*"|\'data:[^\']*\'', '""', f.read_text())
        for bad in ("http://", "https://", "//cdn", "unpkg", "jsdelivr", "cdnjs"):
            assert bad not in text, (f.name, bad)


def test_four_tabs_present():
    html = (WEB / "index.html").read_text()
    for tab in ("Invest", "Portfolio", "Trading", "Simulate"):
        assert 'data-tab="%s"' % tab in html


def test_charts_layer_does_not_duplicate_math():
    js = (WEB / "charts.js").read_text()
    assert "1.04" not in js and "0.026" not in js


def test_app_only_talks_to_the_api():
    js = (WEB / "app.js").read_text()
    assert "/api/" in js
    # no hardcoded golden constants leaking into the client
    for constant in ("147.40", "0.026", "1.04", "0.95"):
        assert constant not in js, constant
