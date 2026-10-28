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
    assert html.index("01 / 03 / 26") < html.index("02 / 01 / 25")


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
    html = lot_page.render_lot(summary(germ_tests=[germ(None, 50, seed_count="<i>", notes="<b>bold")]))
    assert "<b>bold" not in html and "&lt;b&gt;bold" in html and "&lt;i&gt;" in html
    assert "no date" in html


def test_dates_are_day_month_year():
    html = lot_page.render_lot(summary(germ_tests=[germ(date(2026, 3, 9), 90)]))
    assert "09 / 03 / 26" in html and "2026-03-09" not in html


def test_search_box_is_above_the_lot_and_prefilled():
    html = lot_page.render_lot(summary())
    assert 'name="lot_number"' in html and 'value="3538"' in html
    assert html.index('name="lot_number"') < html.index("<h1>")
    assert 'id="result"' in html and "fetch(" in html


def test_germination_section_is_marked_for_grey_background():
    html = lot_page.render_lot(summary())
    assert 'class="germination"' in html and ".germination{background:" in html


def test_message_page_keeps_the_search_box_with_what_was_typed():
    html = lot_page.render_message("Not a lot number", "Use a whole number.", value="<b>x")
    assert 'value="&lt;b&gt;x"' in html and "<b>x" not in html


def test_form_page_has_search_box_and_no_result():
    html = lot_page.render_form()
    assert 'name="lot_number"' in html and 'id="result"' in html


def test_no_search_button_because_the_page_refreshes_itself():
    html = lot_page.render_form()
    assert "<button" not in html and "<svg" not in html
    assert 'type="search"' in html  # Enter or the keyboard's search key still submits the form


def test_fields_are_in_a_two_column_grid_sku_source_first():
    html = lot_page.render_lot(summary())
    assert 'class="fields"' in html and "grid-template-columns:1fr 1fr" in html
    order = [html.index(f">{label}</dt>") for label in ("SKU", "Source", "Weight", "Germination result")]
    assert order == sorted(order)


def test_title_and_heading_are_the_lot_number_with_a_hash():
    html = lot_page.render_lot(summary())
    assert "<title>#3538</title>" in html and "<h1>#3538</h1>" in html
    assert "Lot 3538" not in html


def test_there_is_space_below_the_search_form():
    assert "form{margin-bottom:1rem}" in lot_page.render_lot(summary())


def test_date_has_room_before_the_result():
    html = lot_page.render_lot(summary(germ_tests=[germ(date(2026, 3, 9), 90)]))
    assert "th,td{padding:.4rem .5rem .4rem 0" in html and "td.date{white-space:nowrap}" in html


def test_lot_number_heading_is_large():
    assert "h1{font-size:clamp(2.5rem,14vw,4rem)" in lot_page.render_lot(summary())


def test_germination_tests_are_a_table_with_result_right_aligned():
    tests = [germ(date(2026, 3, 1), 91, notes="ok"), germ(date(2025, 1, 2), None)]
    html = lot_page.render_lot(summary(germ_tests=tests))
    assert "<table" in html and html.count("<tr") == 3  # header + 2 tests
    for heading in ("Date", "Seeds", "Notes", "Result"):
        assert f">{heading}</th>" in html
    assert html.index(">Notes</th>") < html.index(">Result</th>")  # result is the right-most column
    assert ".num{text-align:right" in html
    assert '<td class="num">91%</td>' in html and '<td class="num">in progress</td>' in html


def test_no_table_when_there_are_no_tests():
    html = lot_page.render_lot(summary(germ_tests=[]))
    assert "<table" not in html and "No germination tests yet" in html


def test_notes_are_a_link_that_opens_a_dialog_not_text_in_the_table():
    html = lot_page.render_lot(summary(germ_tests=[germ(date(2026, 3, 1), 91, notes="Slow to start")]))
    assert 'data-notes="Slow to start"' in html and ">?</a>" in html and 'aria-label="Show notes"' in html
    assert "<dialog" in html and "showModal()" in html
    assert "<td>Slow to start</td>" not in html


def test_no_notes_link_when_a_test_has_no_notes():
    html = lot_page.render_lot(summary(germ_tests=[germ(date(2026, 3, 1), 91, notes=None)]))
    assert 'data-notes="' not in html and 'class="notes-link"' not in html


def test_notes_with_quotes_and_markup_are_escaped_in_the_attribute():
    html = lot_page.render_lot(summary(germ_tests=[germ(date(2026, 3, 1), 91, notes='say "hi" <b>')]))
    assert 'data-notes="say &quot;hi&quot; &lt;b&gt;"' in html


def test_dialog_is_outside_the_swapped_result_so_it_survives_a_new_lookup():
    html = lot_page.render_lot(summary())
    assert '</div><dialog id="notes"' in html  # the result div has closed before the dialog starts


def test_sku_value_is_bigger_than_the_other_values():
    html = lot_page.render_lot(summary())
    assert '<dd class="big"><a href="/sku/CAR-1">CAR-1</a></dd>' in html
    assert html.count('class="big"') == 1
    assert "dd.big{font-size:1.8rem" in html


def test_sku_is_not_serif():
    html = lot_page.render_lot(summary())
    assert "dd.big{font-size:1.8rem;line-height:1.2}" in html
    assert "Georgia" not in html and "serif" not in html.replace("sans-serif", "")


def test_sku_links_to_the_sku_list_and_is_url_quoted():
    assert 'href="/sku/A%20B%2FC"' in lot_page.render_lot(summary(sku="A B/C"))
