from matchvoice.agents.guard import check_text

MOMENT = {
    "clock": "44:22",
    "players": [{"name": "Yuto Vukovic"}, {"name": "Ilan Marchetti"}],
    "facts": {"team": "Rovers", "scorer": "Yuto Vukovic", "assist": "Ilan Marchetti", "xg": 0.066, "speed": 66.6},
}


def test_grounded_text_passes():
    assert check_text("Yuto Vukovic scores for the Rovers after an assist from Ilan Marchetti.", MOMENT) == []
    assert check_text("A 66.6 km/h shot with an xG of 0.07 at 44:22.", MOMENT) == []


def test_invented_number_is_flagged():
    assert check_text("The shot travelled at 72 km/h.", MOMENT)


def test_invented_name_is_flagged():
    assert check_text("Gran pase de il Marchetto para Vukovic.", MOMENT)


def test_sentence_start_word_is_not_a_name():
    assert check_text("Great finish by Yuto Vukovic!", MOMENT) == []
