from vs_data_api import lot_page
from vs_data_api.vs_data.lots import LotSummary


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
    assert html.count("not recorded") == 3  # sku, source, weight


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
