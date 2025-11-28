from chatbot.intent import parse

def test_basic_cs580():
    p = parse("easy cs 580 recent --explain")
    assert p["polarity"] == "easy"
    assert p["subject"] == "CS"
    assert p["class_num"] == "580"
    assert p["recent"] is True
    assert p["explain"] is True

def test_keywords():
    p = parse("show easy ml courses 500-level")
    assert "ml" in p["keywords"]
    assert p["level"] == 500

def test_instructor():
    p = parse("details cs 580 prof yu")
    assert p["details"] is True
    assert p["instructor_like"] == "yu"
