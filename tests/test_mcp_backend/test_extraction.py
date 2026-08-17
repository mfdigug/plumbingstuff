from mcp_backend.extraction import extract_items


def test_splits_multiple_items_and_strips_preamble():
    items = extract_items("I need a 90mm stormwater flex and a roll of PTFE tape")
    assert [i["item_name"] for i in items] == ["90mm stormwater flex", "PTFE tape"]
    assert [i["item_index"] for i in items] == [0, 1]


def test_container_phrase_becomes_additional_context():
    items = extract_items("a roll of PTFE tape")
    assert items[0]["additional_context"] == "1 roll"
    assert items[0]["item_name"] == "PTFE tape"


def test_numeric_quantity_is_parsed():
    items = extract_items("3 copper elbows and 2 ball valves")
    assert [i["quantity"] for i in items] == [3, 2]


def test_number_words_beyond_three_are_parsed():
    items = extract_items("four copper elbows, ten ball valves, a dozen tek screws and twenty tile spacers")
    assert [i["quantity"] for i in items] == [4, 10, 12, 20]
    assert [i["item_name"] for i in items] == ["copper elbows", "ball valves", "tek screws", "tile spacers"]


def test_a_dozen_does_not_get_stranded_by_the_bare_article():
    # "a" alone means quantity 1 -- must not shadow the two-word "a dozen" phrase.
    items = extract_items("a dozen tek screws")
    assert items[0]["quantity"] == 12
    assert items[0]["item_name"] == "tek screws"


def test_unrecognized_quantity_word_defaults_to_one():
    items = extract_items("hundred copper elbows")
    assert items[0]["quantity"] == 1
    assert items[0]["item_name"] == "hundred copper elbows"


def test_single_item_query_returns_one_entry():
    items = extract_items("basin tap chrome")
    assert len(items) == 1
    assert items[0]["item_name"] == "basin tap chrome"


def test_color_is_detected_from_known_vocab():
    items = extract_items("a matte black mixer tap")
    assert items[0]["color"] == "matte black"


def test_material_is_detected_from_known_vocab():
    items = extract_items("a copper elbow")
    assert items[0]["material"] == "copper"


def test_source_spans_track_back_to_original_text():
    items = extract_items("toilet suite, basin mixer")
    assert items[0]["source_spans"] == ["toilet suite"]
    assert items[1]["source_spans"] == ["basin mixer"]


def test_source_spans_drop_bare_article_but_keep_container_phrase():
    items = extract_items("I need a 90mm stormwater flex and a roll of PTFE tape")
    assert items[0]["source_spans"] == ["90mm stormwater flex"]
    assert items[1]["source_spans"] == ["a roll of PTFE tape"]


def test_unstocked_brand_is_detected():
    items = extract_items("a jaeger fitting")
    assert items[0]["unstocked_brand"] == "Jaeger"


def test_unstocked_brand_is_none_for_stocked_brands():
    items = extract_items("an auspex elbow")
    assert items[0]["unstocked_brand"] is None
