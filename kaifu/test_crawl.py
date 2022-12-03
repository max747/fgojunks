import crawl


def test_parse_text():
    text = """抹茶  1000回
種 390
牙 130
鎖 152
髄液 151
QP 177
#FGO開封カウンタ"""

    title, count, item_dict = crawl.parse_text(text)
    assert title == "抹茶"
    assert count == "1000"
    assert len(item_dict) == 5
    assert item_dict["種"] == "390"
    assert item_dict["牙"] == "130"
    assert item_dict["鎖"] == "152"
    assert item_dict["髄液"] == "151"
    assert item_dict["QP"] == "177"
