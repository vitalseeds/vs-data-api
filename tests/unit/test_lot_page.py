from datetime import date

from vs_data_api import lot_page
from vs_data_api.vs_data.lots import GermTest, LotSummary


def summary(**kw):
    values = dict(lot_number=3538, sku="CAR-1", source="Seeds Ltd", final_weight_g=125.5)
    return LotSummary(**{**values, **kw})


def test_format_weight():
    assert lot_page.format_weight(None) == "not recorded"
    assert lot_page.format_weight(125.5) == "125.5 g"
    assert lot_page.format_weight(125.0) == "125 g"


def test_render_lot_shows_fields():
    html = lot_page.render_lot(summary())
    for text in ("3538", "CAR-1", "Seeds Ltd", "125.5 g", 'name="viewport"'):
        assert text in html


def test_missing_values_say_not_recorded():
    html = lot_page.render_lot(summary(sku=None, source=None, final_weight_g=None))
    assert html.count("not recorded") == 4  # sku, source, weight, germination result


def test_source_is_escaped():
    html = lot_page.render_lot(summary(source="<script>x</script>"))
    assert "<script>x" not in html
    assert "&lt;script&gt;" in html


def test_render_message_escapes_text():
    html = lot_page.render_message("Oops", "<b>bad</b>")
    assert "<b>bad" not in html and "&lt;b&gt;" in html


def test_form_posts_to_lot():
    html = lot_page.render_form()
    assert 'action="/lot"' in html and 'name="lot_number"' in html


def germ(d, result, seed_count="50", notes=None):
    return GermTest(date=d, result=result, seed_count=seed_count, notes=notes)


def test_format_result():
    assert lot_page.format_result(None) == "not recorded"
    assert lot_page.format_result(85) == "85%"
    assert lot_page.format_result(87.5) == "87.5%"
    assert lot_page.format_result(0) == "0%"
    assert lot_page.format_result(100.0) == "100%"


def test_render_lot_shows_result_and_lists_tests_newest_first():
    tests = [germ(date(2026, 3, 1), 91), germ(date(2025, 1, 2), 80)]
    html = lot_page.render_lot(summary(germ_result=91, germ_tests=tests))
    assert "91%" in html
    assert html.index("2026-03-01") < html.index("2025-01-02")


def test_in_progress_when_no_result():
    html = lot_page.render_lot(summary(germ_result=None, germ_tests=[germ(date(2026, 3, 1), None)]))
    assert "in progress" in html


def test_zero_result_is_not_hidden():
    html = lot_page.render_lot(summary(germ_result=0, germ_tests=[germ(date(2026, 3, 1), 0)]))
    assert "0%" in html and "in progress" not in html


def test_no_tests_message():
    html = lot_page.render_lot(summary(germ_result=None, germ_tests=[]))
    assert "No germination tests yet" in html


def test_test_text_is_escaped_and_missing_date_labelled():
    html = lot_page.render_lot(summary(germ_tests=[germ(None, 50, seed_count="<i>", notes="<script>")]))
    assert "<script>" not in html and "&lt;script&gt;" in html and "&lt;i&gt;" in html
    assert "no date" in html
