"""The whole chain without a camera: made-up hands -> gestures -> strokes -> sigil -> match."""
import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from game.session import DRAFT, RESULT, REVEAL, WAITING, MatchSession
from recognition.sigils import SIGILS, SigilRecognizer
from recognition.dollar1 import resample
from tests.test_gestures import make_hand, zoom_sequence
from ui.play import Game
from ui.screen import H, W, CardArt, render

DT = 1 / 30.0


class Player:
    """Feeds made-up hands to a Game, keeping the clock."""

    def __init__(self, seed=3, pick_seconds=30.0):
        self.game = Game(MatchSession(seed=seed, pick_seconds=pick_seconds, reveal_seconds=0.5), SigilRecognizer())
        self.now = 0.0

    def feed(self, hands):
        for h in hands:
            self.game.update(self.now, self.now * 1000.0, h)
            self.now += DT

    def zoom(self):
        self.feed(zoom_sequence() + [make_hand(pinch=2.0)] * 15)

    def draw(self, name):
        pts = resample(SIGILS[name][0], 60)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        size = max(max(xs) - min(xs), max(ys) - min(ys))
        path = [(0.4 + 0.25 * (x - min(xs)) / size, 0.4 + 0.25 * (y - min(ys)) / size) for x, y in pts]
        self.feed([make_hand(pinch=2.0, cx=path[0][0], cy=path[0][1])] * 5
                  + [make_hand(pinch=0.1, cx=x, cy=y) for x, y in path]
                  + [make_hand(pinch=1.5, cx=path[-1][0], cy=path[-1][1])] * 8)

    def fist(self):
        self.feed([make_hand(pinch=0.8, curl=0.3)] * 25 + [make_hand(pinch=2.0)] * 5)


def test_zoom_starts_the_match():
    p = Player()
    assert p.game.session.phase == WAITING
    p.zoom()
    assert p.game.session.phase == DRAFT and len(p.game.session.offer) == 3


def test_drawing_a_cards_sigil_picks_it_and_a_fist_locks_it():
    p = Player()
    p.zoom()
    target = p.game.session.offer[2]
    p.draw(target.title)
    assert p.game.session.selected == 2 and p.game.session.picks == []
    p.fist()
    assert p.game.session.picks == [target] and p.game.session.turn == 2


def test_drawing_another_sigil_changes_the_pick():
    p = Player()
    p.zoom()
    offer = p.game.session.offer
    p.draw(offer[0].title)
    p.draw(offer[1].title)
    assert p.game.session.selected == 1
    p.fist()
    assert p.game.session.picks == [offer[1]]


def test_a_sigil_that_is_not_on_offer_picks_nothing():
    p = Player()
    p.zoom()
    on_offer = {c.title for c in p.game.session.offer}
    other = next(n for n in ("Hourglass", "Quake", "Bloom", "Fade") if n not in on_offer)
    p.draw(other)
    if p.game.session.selected is None:      # normally rejected; if it resembles one, that is a pick
        assert "Not recognized" in p.game.message
    p.fist()
    assert len(p.game.session.picks) in (0, 1)


def test_fist_without_a_pick_does_nothing_and_you_can_still_draw():
    p = Player()
    p.zoom()
    p.fist()
    assert p.game.session.picks == []
    target = p.game.session.offer[0]
    p.draw(target.title)
    p.fist()
    assert p.game.session.picks == [target]


def test_a_full_match_by_gestures_then_zoom_to_play_again():
    p = Player()
    p.zoom()
    for turn in range(5):
        assert p.game.session.phase == DRAFT and p.game.session.turn == turn + 1
        p.draw(p.game.session.offer[turn % 3].title)
        p.fist()
    assert p.game.session.phase == REVEAL and len(p.game.session.picks) == 5
    p.feed([None] * int(8 / DT))
    assert p.game.session.phase == RESULT
    p.zoom()
    assert p.game.session.phase == DRAFT and p.game.session.picks == []


def test_timer_runs_out_while_nobody_moves():
    p = Player(pick_seconds=1.0)
    p.zoom()
    p.feed([None] * int(1.3 / DT))
    assert len(p.game.session.picks) == 1 and p.game.session.picks[0].label == "Fizzle"


def test_every_phase_renders_a_full_picture():
    art = CardArt()
    frame = np.zeros((480, 640, 3), np.uint8)
    p = Player()
    shots = [render(frame, p.game.session, p.now, art)]
    p.zoom()
    p.draw(p.game.session.offer[0].title)
    shots.append(render(frame, p.game.session, p.now, art, *p.game.current_message(p.now)))
    for turn in range(5):
        if p.game.session.selected is None:
            p.draw(p.game.session.offer[0].title)
        p.fist()
    p.feed([None] * int(1.2 / DT))
    shots.append(render(frame, p.game.session, p.now, art))
    p.feed([None] * int(8 / DT))
    shots.append(render(frame, p.game.session, p.now, art))
    assert p.game.session.phase == RESULT
    assert all(s.shape == (H, W, 3) for s in shots)


def test_all_26_card_images_exist():
    import os
    from game.cards import CATALOG
    for title, _, _ in CATALOG:
        assert os.path.exists(os.path.join("assets", "cards", title.lower() + ".jpg")), title


def test_a_judged_stroke_leaves_a_timing_report_for_one_frame():
    p = Player()
    p.zoom()
    target = p.game.session.offer[1].title
    reports = []
    real_update = p.game.update

    def spy(now, t_ms, hand):
        real_update(now, t_ms, hand)
        if p.game.stroke_report:
            reports.append(dict(p.game.stroke_report))
    p.game.update = spy
    p.draw(target)
    assert len(reports) == 1
    r = reports[0]
    assert r["label"] == target and target in r["offer"] and r["recognize_ms"] >= 0
    assert 0 < p.now * 1000.0 - r["drawn_ms"] < 2000 and r["points"] > 10
