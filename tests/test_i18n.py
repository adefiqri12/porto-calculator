"""Guards against untranslated UI text and missing dictionary keys.

The earlier frontend shipped 45 user-visible strings with only 3 wired to the
dictionary, so the language toggle barely worked. These tests make that
regression impossible: every key referenced by markup or code must exist in
both languages.
"""
import pathlib
import re

WEB = pathlib.Path("web")
I18N = (WEB / "i18n.js").read_text()
HTML = (WEB / "index.html").read_text()
APP = (WEB / "app.js").read_text()

KEY_RE = re.compile(r'"([a-z][a-z0-9_]*\.[a-z0-9_]+)"\s*:')


def _dict_keys(block_name):
    """Keys inside the id: {...} or en: {...} block."""
    start = I18N.index(block_name + ": {")
    depth = 0
    i = I18N.index("{", start)
    for j in range(i, len(I18N)):
        if I18N[j] == "{":
            depth += 1
        elif I18N[j] == "}":
            depth -= 1
            if depth == 0:
                return set(KEY_RE.findall(I18N[i:j]))
    raise AssertionError("unbalanced block: " + block_name)


ID_KEYS = _dict_keys("id")
EN_KEYS = _dict_keys("en")


def test_dictionary_is_substantial():
    # A guard against the dictionary silently shrinking back to a stub.
    assert len(EN_KEYS) >= 60, len(EN_KEYS)


def test_languages_have_identical_keys():
    assert ID_KEYS == EN_KEYS, {
        "only_id": sorted(ID_KEYS - EN_KEYS),
        "only_en": sorted(EN_KEYS - ID_KEYS),
    }


def test_every_markup_key_exists():
    used = set(re.findall(r'data-i18n(?:-title)?="([^"]+)"', HTML))
    assert used, "no data-i18n attributes found in markup"
    assert used <= EN_KEYS, sorted(used - EN_KEYS)


def test_every_code_key_exists():
    used = set(re.findall(r'(?:I18n\.t|T)\("([^"]+)"\)', APP))
    assert used, "no I18n.t() calls found in app.js"
    assert used <= EN_KEYS, sorted(used - EN_KEYS)


def test_no_untranslated_card_titles_remain():
    # card("Hardcoded", ...) is the regression this guards against.
    literal = re.findall(r'card\(\s*"', APP)
    assert literal == [], "hardcoded card title(s): %r" % literal


def test_persistence_is_implemented():
    assert "localStorage" in APP
    assert "STORE_KEY" in APP
    assert "loadInputs" in APP and "saveInputs" in APP


def test_no_reference_to_undeclared_global():
    # app.js wraps itself in (function () { ... })() with no `global` parameter,
    # so `global.localStorage` throws a ReferenceError that a try/catch swallows
    # silently. That bug shipped once and made restore a no-op.
    assert "global." not in APP, [l for l in APP.splitlines() if "global." in l]
    assert "window.localStorage" in APP


def test_no_unused_keys():
    # Dead keys accumulate when a feature is removed (the A/B/C Simulate table
    # left 14 behind). Keep the dictionary honest.
    used = set(re.findall(r'data-i18n(?:-title)?="([^"]+)"', HTML))
    used |= set(re.findall(r'(?:I18n\.t|T)\("([^"]+)"\)', APP))
    unused = sorted(EN_KEYS - used)
    assert unused == [], unused


def test_tabs_are_translatable_but_keep_stable_hooks():
    # data-tab stays literal English (stable selector); the visible label is keyed.
    for tab in ("Invest", "Portfolio", "Trading", "Simulate"):
        assert 'data-tab="%s"' % tab in HTML
    for key in ("tab.invest", "tab.portfolio", "tab.trading", "tab.simulate"):
        assert key in EN_KEYS and key in ID_KEYS
