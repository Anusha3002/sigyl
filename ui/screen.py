"""Draws the game screen. No camera here: give it a camera frame and the match state, get a picture.

Layout (1280 x 720):
  left 960 px   the camera (where you draw), with aura bars on top and your five slots at the bottom
  right 320 px  the timer and the three cards on offer
"""
import os
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from game.cards import MAX_AURA, Card, CardType
from game.session import DRAFT, RESULT, REVEAL, WAITING, MatchSession

W, H, CAM_W = 1280, 720, 960
PANEL = (28, 34, 44)          # BGR, dark warm brown
GOLD = (80, 190, 240)
WHITE = (245, 245, 245)
GREY = (160, 160, 160)
GREEN = (110, 210, 110)
RED = (90, 90, 235)
PARCHMENT = (170, 215, 240)
FONT = cv2.FONT_HERSHEY_SIMPLEX
CARD_W, CARD_H = 150, 212     # cards on offer
SLOT_W, SLOT_H = 58, 82       # small cards in the slot row
BIG_W, BIG_H = 230, 325       # cards in the reveal


def text(img, s: str, org: Tuple[int, int], scale: float = 0.6, color=WHITE, thick: int = 1, center: bool = False) -> None:
    if center:
        (tw, _), _ = cv2.getTextSize(s, FONT, scale, thick)
        org = (org[0] - tw // 2, org[1])
    cv2.putText(img, s, (org[0] + 2, org[1] + 2), FONT, scale, (0, 0, 0), thick, cv2.LINE_AA)
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


def shade(img, x0: int, y0: int, x1: int, y1: int, amount: float = 0.55) -> None:
    """Darken a rectangle so text on top of the camera stays readable."""
    img[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - amount)).astype(np.uint8)


class CardArt:
    """Loads assets/cards/<name>.jpg and hands out resized copies."""

    def __init__(self, folder: str = "assets/cards"):
        self.folder = folder
        self._cache: Dict[Tuple[str, int, int], np.ndarray] = {}

    def get(self, card: Optional[Card], w: int, h: int) -> np.ndarray:
        key = ("?" if card is None else card.label, w, h)
        if key not in self._cache:
            self._cache[key] = self._make(card, w, h)
        return self._cache[key]

    def _make(self, card: Optional[Card], w: int, h: int) -> np.ndarray:
        if card is not None and card.title:
            img = cv2.imread(os.path.join(self.folder, card.title.lower() + ".jpg"))
            if img is not None:
                return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
        img = np.full((h, w, 3), (60, 50, 44) if card is None else PARCHMENT, np.uint8)
        cv2.rectangle(img, (2, 2), (w - 3, h - 3), (30, 60, 90), 2)
        label = "?" if card is None else ("FIZZLE" if card.type == CardType.FIZZLE else card.label.upper())
        scale = max(0.35, min(1.2, w / 150.0)) * (1.6 if card is None else 0.6)
        text(img, label, (w // 2, h // 2 + 6), scale, WHITE if card is None else (40, 40, 60), 2 if card is None else 1, center=True)
        return img


def paste(canvas, img, x: int, y: int) -> None:
    h, w = img.shape[:2]
    canvas[y:y + h, x:x + w] = img


def aura_bar(canvas, x: int, y: int, w: int, value: int, label: str, right: bool = False) -> None:
    cv2.rectangle(canvas, (x, y), (x + w, y + 18), (40, 40, 40), -1)
    fill = int(w * max(0, min(MAX_AURA, value)) / MAX_AURA)
    color = GREEN if value > 50 else (GOLD if value > 20 else RED)
    if right:
        cv2.rectangle(canvas, (x + w - fill, y), (x + w, y + 18), color, -1)
    else:
        cv2.rectangle(canvas, (x, y), (x + fill, y + 18), color, -1)
    cv2.rectangle(canvas, (x, y), (x + w, y + 18), WHITE, 1)
    text(canvas, f"{label}  {value}", (x + (w - 110 if right else 4), y + 40), 0.6, WHITE, 1)


def render(frame, session: MatchSession, now: float, art: CardArt, message: str = "", detail: str = "") -> np.ndarray:
    """frame: the camera picture (any size, already mirrored, with hand and trail drawn on it)."""
    canvas = np.zeros((H, W, 3), np.uint8)
    canvas[:, :CAM_W] = cv2.resize(frame, (CAM_W, H))
    canvas[:, CAM_W:] = PANEL
    phase = session.phase
    if phase in (REVEAL, RESULT):
        shade(canvas, 0, 0, CAM_W, H, 0.6)

    # top: aura bars
    shade(canvas, 0, 0, CAM_W, 58)
    aura = session.aura
    aura_bar(canvas, 16, 10, 330, aura[0], "YOU")
    aura_bar(canvas, CAM_W - 346, 10, 330, aura[1], "BOT", right=True)

    # bottom: your five slots (and the bot's, once revealed)
    shade(canvas, 0, H - 104, CAM_W, H)
    shown = session.shown_slots
    x0 = (CAM_W - (5 * SLOT_W + 4 * 14)) // 2
    for i in range(5):
        x, y = x0 + i * (SLOT_W + 14), H - 94
        if i < len(session.picks):
            paste(canvas, art.get(session.picks[i], SLOT_W, SLOT_H), x, y)
        else:
            cv2.rectangle(canvas, (x, y), (x + SLOT_W, y + SLOT_H), GREY, 1)
            text(canvas, str(i + 1), (x + SLOT_W // 2, y + SLOT_H // 2 + 7), 0.6, GREY, 1, center=True)
        if phase == REVEAL and i == len(shown) - 1:
            cv2.rectangle(canvas, (x - 3, y - 3), (x + SLOT_W + 2, y + SLOT_H + 2), GOLD, 2)
    text(canvas, "YOUR SLOTS", (x0 - 132, H - 46), 0.5, GREY)

    if phase == WAITING:
        _center_banner(canvas, "SIGYL", "Zoom to start: pinch, then spread your fingers wide")
        _panel_help(canvas)
    elif phase == DRAFT:
        text(canvas, f"PICK {session.turn} OF 5", (CAM_W // 2, 36), 0.8, WHITE, 2, center=True)
        _panel_offer(canvas, session, now, art)
    elif phase == REVEAL:
        _reveal(canvas, session, art)
        _panel_log(canvas, session)
    elif phase == RESULT:
        w = session.winner
        title = "DRAW" if w is None else ("YOU WIN" if w == 0 else "BOT WINS")
        _center_banner(canvas, title, f"Aura  you {aura[0]}  -  bot {aura[1]}      Zoom to play again",
                       GOLD if w == 0 else WHITE)
        _panel_log(canvas, session)

    if message:
        text(canvas, message, (CAM_W // 2, 92), 0.75, GOLD, 2, center=True)
    if detail:
        text(canvas, detail, (CAM_W // 2, 120), 0.55, WHITE, 1, center=True)
    return canvas


def _center_banner(canvas, title: str, sub: str, color=WHITE) -> None:
    text(canvas, title, (CAM_W // 2, H // 2 - 20), 2.4, color, 5, center=True)
    text(canvas, sub, (CAM_W // 2, H // 2 + 36), 0.7, WHITE, 1, center=True)


def _panel_help(canvas) -> None:
    lines = ["HOW TO PLAY", "", "1. Zoom to start.", "2. Three cards appear.", "   Pinch and draw the sigil",
             "   of the card you want.", "3. Make a fist to lock it in.", "4. Five picks, then the",
             "   cards face the bot's,", "   slot by slot.", "", "Highest aura wins."]
    for i, s in enumerate(lines):
        text(canvas, s, (CAM_W + 22, 60 + i * 30), 0.55 if i else 0.7, GOLD if i == 0 else WHITE, 2 if i == 0 else 1)


def _panel_offer(canvas, session: MatchSession, now: float, art: CardArt) -> None:
    left = session.time_left(now)
    frac = left / session.pick_seconds if session.pick_seconds else 0
    color = WHITE if left > 10 else (GOLD if left > 5 else RED)
    text(canvas, f"{int(left + 0.999):2d}s", (CAM_W + 20, 44), 1.1, color, 2)
    cv2.rectangle(canvas, (CAM_W + 110, 22), (W - 20, 40), (55, 60, 70), -1)
    cv2.rectangle(canvas, (CAM_W + 110, 22), (CAM_W + 110 + int((W - 130 - CAM_W) * frac), 40), color, -1)
    x = CAM_W + (W - CAM_W - CARD_W) // 2
    for i, card in enumerate(session.offer):
        y = 66 + i * (CARD_H + 5)
        img = art.get(card, CARD_W, CARD_H)
        if session.selected is not None and session.selected != i:
            img = (img * 0.45).astype(np.uint8)
        paste(canvas, img, x, y)
        if session.selected == i:
            cv2.rectangle(canvas, (x - 5, y - 3), (x + CARD_W + 4, y + CARD_H + 2), GOLD, 4)
            text(canvas, "PICKED", (x - 78, y + CARD_H // 2), 0.5, GOLD, 2)
            text(canvas, "fist to", (x - 78, y + CARD_H // 2 + 22), 0.45, WHITE)
            text(canvas, "lock in", (x - 78, y + CARD_H // 2 + 40), 0.45, WHITE)


def _reveal(canvas, session: MatchSession, art: CardArt) -> None:
    shown = session.shown_slots
    if not shown:
        text(canvas, "All five locked in. Revealing...", (CAM_W // 2, H // 2), 1.0, WHITE, 2, center=True)
        return
    slot = shown[-1]
    text(canvas, f"SLOT {slot.slot} OF {len(session.result.slots) if session.result.knockout else 5}", (CAM_W // 2, 110), 0.9, GOLD, 2, center=True)
    gap = 110
    xa = CAM_W // 2 - gap // 2 - BIG_W
    xb = CAM_W // 2 + gap // 2
    y = 150
    paste(canvas, art.get(slot.cards[0], BIG_W, BIG_H), xa, y)
    paste(canvas, art.get(slot.cards[1], BIG_W, BIG_H), xb, y)
    text(canvas, "VS", (CAM_W // 2, y + BIG_H // 2 + 10), 1.1, WHITE, 2, center=True)
    for who, x, d in (("YOU", xa, slot.delta[0]), ("BOT", xb, slot.delta[1])):
        text(canvas, who, (x + BIG_W // 2, y - 10), 0.7, WHITE, 2, center=True)
        s = f"{d:+d} aura" if d else "no change"
        text(canvas, s, (x + BIG_W // 2, y + BIG_H + 34), 0.9, GREEN if d > 0 else (RED if d < 0 else GREY), 2, center=True)
    if slot.note:
        text(canvas, slot.note[:90], (CAM_W // 2, y + BIG_H + 70), 0.55, WHITE, 1, center=True)


def _panel_log(canvas, session: MatchSession) -> None:
    text(canvas, "SLOT BY SLOT", (CAM_W + 22, 44), 0.7, GOLD, 2)
    for i, slot in enumerate(session.shown_slots):
        y = 90 + i * 118
        text(canvas, f"{slot.slot}. {slot.cards[0].label}  vs  {slot.cards[1].label}", (CAM_W + 22, y), 0.52, WHITE)
        for j, (who, d) in enumerate((("you", slot.delta[0]), ("bot", slot.delta[1]))):
            text(canvas, f"{who} {d:+d}" if d else f"{who}  0", (CAM_W + 40 + j * 120, y + 26), 0.5,
                 GREEN if d > 0 else (RED if d < 0 else GREY))
        text(canvas, f"aura {slot.aura[0]} - {slot.aura[1]}", (CAM_W + 40, y + 52), 0.5, GREY)
