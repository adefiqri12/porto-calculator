"""Static frontend contract: files present, no CDN, tabs wired, math not duplicated."""
import pathlib

WEB = pathlib.Path("web")


def test_web_assets_exist():
    for name in ("index.html", "styles.css", "charts.js", "app.js", "i18n.js"):
        assert (WEB / name).is_file(), name


def test_no_cdn_links():
    html = (WEB / "index.html").read_text()
    assert "http://" not in html and "https://" not in html


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
