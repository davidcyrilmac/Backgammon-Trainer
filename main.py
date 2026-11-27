"""Backgammon Best Move -- Kivy front end for bgengine.py

Light (cream) checkers are YOURS and move 24 -> 1 (top-right round to
bottom-right). Red checkers are the opponent's. Set up the position by
tapping the board, pick the dice, press ANALYZE.
"""
import os
import random
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, Triangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
import kivy.utils as kivy_utils
platform = getattr(kivy_utils, "platform", "linux")  # noqa

import bgengine as bg
import bgnet

NETFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "net.json")

BG = (0.09, 0.11, 0.13, 1)
FELT = (0.10, 0.30, 0.22, 1)
BAR = (0.28, 0.18, 0.10, 1)
TRI_A = (0.72, 0.58, 0.38, 1)
TRI_B = (0.42, 0.26, 0.16, 1)
LIGHT = (0.96, 0.93, 0.84, 1)
RED = (0.78, 0.14, 0.14, 1)
INK = (0.08, 0.08, 0.08, 1)
COLS = 14          # 6 points | bar | 6 points | off-tray


def _tex(text, size, color=(1, 1, 1, 1)):
    lab = CoreLabel(text=text, font_size=size, color=color)
    lab.refresh()
    return lab.texture


HELP_TEXT = """[b][size=20sp]How to use Backgammon Best Move[/size][/b]

[b]What this app does[/b]
Play backgammon by hand on the board, ask the engine for the best play, get your own plays graded, use the doubling cube, and compare the engine's equity with a program such as GNU Backgammon. You move BOTH sides yourself (Light and Red), so it also works as a companion while you play a game elsewhere.

[b][size=16sp]1. Reading the screen[/size][/b]
[b]Board.[/b] Light (white) and Red (red) checkers keep their colours and places on screen at all times. Each point shows two numbers: Light's number in white (left) and Red's number in red (right). The side to move is drawn brighter. Notation such as 13/8 always uses the numbering of the side on roll.
[b]BAR[/b] (centre column): a disc with a count shows checkers that were hit. [b]OFF[/b] (right column): a disc with a count shows checkers borne off.
[b]Doubling cube[/b]: shown in the bar column (see section 8).
[b]Status line[/b] (under the board): who is to move, both pip counts, how many of the 36 rolls hit a blot, the cube, and a hint or message in yellow. Read it when something does not respond.

[b][size=16sp]2. Quick start: playing a game[/size][/b]
1. Press [b]Opening[/b] twice quickly. This sets up the starting position (one tap only shows a reminder, so a stray tap cannot wipe your board).
2. Optionally press [b]Double[/b] before rolling (section 8).
3. Press [b]Roll dice[/b] for a random roll, or tap a number in each of the Die 1 and Die 2 rows to enter a roll yourself (for example a roll from GNU Backgammon).
4. Make sure the [b]Move[/b] button is selected. Tap one of your checkers: it lights up yellow and every legal destination turns green. Tap a green spot to move there.
5. Play both dice. When the turn is complete the status line says so.
6. Press [b]Switch turn[/b]. The other side is now on roll and the dice clear. Repeat from step 2.

[b][size=16sp]3. Dice[/size][/b]
[b]Roll dice[/b] picks two random dice. It will not roll in the middle of a turn: finish or Undo the move, then press Switch turn. Tapping a selected die again clears it. If you change the dice before moving, the turn simply restarts with the new roll. Doubles give four moves.

[b][size=16sp]4. Moving checkers (Move mode)[/size][/b]
Only legal moves are accepted. The app enforces every rule: you must enter from the bar first, use both dice whenever possible, use the larger die when only one can be played, and bear off only when all 15 checkers are home.
[b]One die or several.[/b] After you pick up a checker, green spots include places reachable with one die and places reachable by using several dice in a row. Tap the final spot, for example 13/8 with a 4-1, and the app plays both steps.
[b]Bar.[/b] If you have a checker on the bar, tap the bar disc first, then the entry point.
[b]Bearing off.[/b] Pick up a checker, then tap the OFF column (it turns green when legal).
[b]Hitting.[/b] Move onto a single opposing checker (a blot) and it goes to the bar.
[b]Cancel a selection[/b] by tapping the same checker again.
[b]Not legal?[/b] The status line says why and lists the spots the checker can reach, for example "9 (4)" or "8 (4+1)".
[b]Undo move[/b] takes back your last single move; press it again to go further back, including after a completed turn (before you press Switch turn).

[b][size=16sp]5. ANALYZE: the engine's best play[/size][/b]
Set the dice, then press [b]ANALYZE[/b] BEFORE you move. The results list shows candidate plays, best first, with:
- the equity or win chance (see section 9) for the side on roll
- whether the play leaves blots and how many
- "2-ply": the engine looked at your play and the opponent's best reply to each of the 21 possible rolls
Tap any line to [b]preview[/b] that position on the board (a banner says PREVIEW). Then either:
- press [b]Switch turn[/b] to PLAY that line and hand over to the other side, or
- press [b]Reset view[/b] to cancel the preview and go back.
The top line is "Best for Light" or "Best for Red". If the opponent has a checker on the bar, the list also shows how often it dances (fails to enter).
ANALYZE is refused after you have started moving; press Undo move until the board is back at the start.

[b][size=16sp]6. Your play is graded[/size][/b]
When you finish a turn by moving the checkers yourself, the app compares your play with the engine's candidates and shows:
- your rank among the engine's best candidates
- how far behind the best play you were (equity, or win % in heuristic mode)
- a verdict: Best move, Essentially equal, Good, Inaccuracy, Mistake or Blunder
- your play highlighted in orange ("YOUR PLAY"); tap any line to preview it
- "Forced" when only one legal play existed
Grades are only as good as the evaluator. Differences under about 0.02 equity are within its margin of error.

[b][size=16sp]7. Switch turn[/size][/b]
Hands the roll to the other side without changing the board. It is refused while dice remain unplayed (finish or Undo first), while a double is pending, or after the game is over. It clears the dice and shows how your last play was graded.

[b][size=16sp]8. The doubling cube[/size][/b]
[b]Centred.[/b] The cube starts in the middle of the bar column showing 64 (value 1, either side may double). After a take it moves to the taker's end: Light's end at the bottom, Red's end at the top.
[b]Double.[/b] The side on roll may press Double only BEFORE rolling (clear the dice or press Switch turn first) and only if the cube is centred or that side owns it. The cube shows the new value in orange in the middle.
[b]Take or Pass.[/b] While a double is pending, nothing else works until the other side presses [b]Take[/b] (play on for the doubled stake and own the cube) or [b]Pass[/b] (give up the game and lose the current cube value). After a take, the doubler rolls.
[b]Redouble.[/b] Only the owner may redouble. The cube stops at 64.
[b]Scoring.[/b] Game points are 1 (single), 2 (gammon: loser has borne off none) or 3 (backgammon: loser also has a checker on the bar or in the winner's home board), multiplied by the cube. This is money-style play: there is no Crawford rule and no Jacoby rule.
The app does not advise on cube decisions; the engine is cubeless.

[b][size=16sp]9. Equity and the evaluator[/size][/b]
[b]Equity[/b] is the expected result of a game for the side on roll, in points, with no cube: +1.0 means winning a single game for sure, -1.0 losing one, and gammons count extra. It is shown with the neural net.
[b]Eval: Neural / Eval: Heuristic[/b] (button) switches the evaluator. Neural uses the trained network (net.json must sit next to the program). Heuristic is a simpler hand-made formula that reports win % and is rougher.
[b]Comparing with GNU Backgammon.[/b] Enter the same position and roll in both, then compare the best move and the equity (use GNU's cubeless money equity). Expect agreement on most ordinary plays and differences of a few hundredths of a point, sometimes more. The network is small and was trained by self-play; it is not a substitute for a GNU rollout.

[b][size=16sp]10. Setting up positions (Add / Remove)[/size][/b]
Use this to copy a position from another program or to practise a position.
1. Choose the colour: [b]Light[/b] or [b]Red[/b].
2. Choose [b]Add[/b] or [b]Remove[/b].
3. Tap a point to add or remove one checker of that colour. Tap the BAR or OFF column to add or remove checkers there.
Each side can have at most 15 checkers in total. Fix any problem the status line reports (for example more than 15 checkers) before analysing. [b]Clear[/b] (double tap) empties the board and resets the cube; [b]Opening[/b] (double tap) restores the starting position and resets the cube. Switch back to [b]Move[/b] to play. Edits always show the real board, so they also cancel a preview.

[b][size=16sp]11. End of the game[/size][/b]
The game ends when one side has borne off all 15 checkers, or when a double is passed. The status line shows the winner and points; moves, rolling, analysing, doubling and Switch turn are then blocked. [b]Undo move[/b] reopens a game if you want to change the last play. Press [b]Opening[/b] twice to start a new game.

[b][size=16sp]12. Button reference[/size][/b]
Light / Red: colour for editing. Add / Remove / Move: what a tap on the board does.
Opening, Clear: set up the board (double tap).
Switch turn: pass the roll to the other side (plays a previewed line).
Reset view: leave a preview.
Eval: neural network or heuristic.
Double / Take / Pass: doubling cube.
Help: this page.
Die 1, Die 2: the roll. Roll dice: random roll.
ANALYZE: best plays for the current position and roll.
Undo move: take back the last move.

[b][size=16sp]13. Troubleshooting[/size][/b]
[b]Nothing happens when I tap a checker.[/b] Check the status line: you may be in Add or Remove mode, the dice may not be chosen, it may be the other side's turn (press Switch turn), a double may be pending, or the game may be over.
[b]"Pick both dice first".[/b] Move mode needs the roll before it can know what is legal.
[b]I cannot double.[/b] Clear the dice first, finish or undo any move, and remember only the cube's owner may redouble.
[b]ANALYZE ignores something.[/b] Make sure the board shows the real position and the right side is on roll; bar checkers are always taken into account.
[b]No neural network.[/b] If net.json is missing the app uses the heuristic evaluator.

[b]Good luck, and enjoy the game![/b]
"""


class BoardView(Widget):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.bind(pos=self.redraw, size=self.redraw)

    # ---- geometry -------------------------------------------------------
    def _geom(self):
        m = max(dp(12), self.height * 0.05)
        x0, y0 = self.x, self.y + m
        w, h = self.width, self.height - 2 * m
        return x0, y0, w, h, m, w / COLS

    @staticmethod
    def _col_of_point(p):
        idx = (p - 13) if p >= 13 else (12 - p)
        return idx if idx < 6 else idx + 1

    # ---- drawing --------------------------------------------------------
    def redraw(self, *_):
        self.canvas.clear()
        if self.width < 10:
            return
        pos = self.app.pos_view
        flip = self.app.flip          # Red to move: engine frame is mirrored
        if flip:
            pos = pos.flipped()       # draw in fixed colours (Light=white)
        x0, y0, w, h, m, cw = self._geom()
        half = h / 2.0
        # five checkers (10 radii) must fit inside half the board height
        r = min(cw * 0.46, half / 11.0)
        with self.canvas:
            Color(*FELT)
            Rectangle(pos=(x0, y0), size=(w, h))
            Color(*BAR)
            Rectangle(pos=(x0 + 6 * cw, y0), size=(cw, h))
            Rectangle(pos=(x0 + 13 * cw, y0), size=(cw, h))
            # triangles + numbers + checkers
            for p in range(1, 25):
                col = self._col_of_point(p)
                cx = x0 + col * cw + cw / 2
                top = p >= 13
                Color(*(TRI_A if p % 2 else TRI_B))
                if top:
                    Triangle(points=[cx - cw / 2 + 2, y0 + h, cx + cw / 2 - 2,
                                     y0 + h, cx, y0 + h - half * 0.85])
                else:
                    Triangle(points=[cx - cw / 2 + 2, y0, cx + cw / 2 - 2, y0,
                                     cx, y0 + half * 0.85])
                # two numberings, fixed on screen: Light's (white) and Red's
                # (red); the side to move is drawn brighter
                ty = (y0 + h + m / 2) if top else (y0 - m / 2)
                for num, tint, mine, dx in (
                        (p, (0.95, 0.95, 0.85), not flip, -0.24),
                        (25 - p, (1.0, 0.45, 0.45), flip, 0.24)):
                    a = 1.0 if mine else 0.42
                    t = _tex(str(num), sp(8), tint + (a,))
                    Color(1, 1, 1, 1)
                    Rectangle(texture=t, size=t.size,
                              pos=(cx + dx * cw - t.width / 2,
                                   ty - t.height / 2))
                n = pos.board[p - 1]
                if n:
                    self._stack(cx, y0, h, r, abs(n), top,
                                LIGHT if n > 0 else RED)
            # bar and tray: one disc with a count
            qy = h / 4.0
            self._badge(x0 + 6.5 * cw, y0 + 3 * qy, r, pos.bar_opp, RED)
            self._badge(x0 + 6.5 * cw, y0 + qy, r, pos.bar_me, LIGHT)
            self._badge(x0 + 13.5 * cw, y0 + 3 * qy, r, pos.off_opp, RED)
            self._badge(x0 + 13.5 * cw, y0 + qy, r, pos.off_me, LIGHT)
            cube_mid = self.app.cube_owner is None or \
                self.app.cube_offer is not None
            for cxx, lab in ((6.5, "BAR"), (13.5, "OFF")):
                if lab == "BAR" and cube_mid:
                    continue            # the cube sits in the middle
                t = _tex(lab, sp(8), (0.9, 0.8, 0.6, 1))
                Color(1, 1, 1, 1)
                Rectangle(texture=t, size=t.size,
                          pos=(x0 + cxx * cw - t.width / 2,
                               y0 + h / 2 - t.height / 2))
            self._cube(x0 + 6.5 * cw, y0, h, cw)
            # legal destinations of the picked-up checker (green)
            if not self.app.previewing:
                for dst in self.app.targets:
                    Color(0.3, 1.0, 0.4, 0.32)
                    if dst == -1:
                        Rectangle(pos=(x0 + 13 * cw, y0 + (half if flip else 0)),
                                  size=(cw, half))
                    else:
                        ad = 23 - dst if flip else dst
                        Rectangle(
                            pos=(x0 + self._col_of_point(ad + 1) * cw,
                                 y0 + (half if ad + 1 >= 13 else 0)),
                            size=(cw, half))
            # highlight the checker picked up in Move mode
            sel = self.app.sel
            if sel is not None and not self.app.previewing:
                kind, i, side = sel
                Color(1, 0.9, 0.2, 0.28)
                if kind == "point":
                    ai = 23 - i if flip else i
                    top = (ai + 1) >= 13
                    Rectangle(pos=(x0 + self._col_of_point(ai + 1) * cw,
                                   y0 + (half if top else 0)),
                              size=(cw, half))
                else:
                    Rectangle(pos=(x0 + (6 if kind == "bar" else 13) * cw,
                                   y0 + (half if flip else 0)),
                              size=(cw, half))

    def _disc(self, cx, cy, r, color):
        Color(0, 0, 0, 0.55)
        Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
        Color(*color)
        Ellipse(pos=(cx - r + 1.5, cy - r + 1.5), size=(2 * r - 3, 2 * r - 3))

    def _stack(self, cx, y0, h, r, n, top, color):
        """Draw ALL n checkers; overlap them when the point is crowded."""
        avail = h / 2.0 * 0.96                  # room measured from the base
        step = 2 * r if 2 * r * n <= avail else (avail - 2 * r) / (n - 1)
        cy = y0
        for k in range(n):
            off = r + k * step
            cy = (y0 + h - off) if top else (y0 + off)
            self._disc(cx, cy, r, color)
        if n > 5:                               # count on the top checker
            t = _tex(str(n), sp(13), INK if color == LIGHT else (1, 1, 1, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=t, size=t.size,
                      pos=(cx - t.width / 2, cy - t.height / 2))

    def _cube(self, cx, y0, h, cw):
        """Doubling cube on the bar column: centred (shows 64), or at the
        owner's end; while a double is pending it sits mid-board, orange."""
        a = self.app
        side = min(cw * 0.78, h / 7.0)
        offer = a.cube_offer is not None
        val = a.cube_val * (2 if offer else 1)
        if offer:
            cy = y0 + h / 2
        elif a.cube_owner is None:
            cy, val = y0 + h / 2, 64
        elif a.cube_owner == "L":
            cy = y0 + side * 0.65
        else:
            cy = y0 + h - side * 0.65
        Color(1.0, 0.6, 0.15, 1) if offer else Color(0.93, 0.93, 0.88, 1)
        Rectangle(pos=(cx - side / 2, cy - side / 2), size=(side, side))
        Color(0.1, 0.1, 0.1, 1)
        t = _tex(str(val), sp(12 if val < 10 else 10), (0.1, 0.1, 0.1, 1))
        Color(1, 1, 1, 1)
        Rectangle(texture=t, size=t.size,
                  pos=(cx - t.width / 2, cy - t.height / 2))

    def _badge(self, cx, cy, r, n, color):
        if n <= 0:
            return
        self._disc(cx, cy, r, color)
        t = _tex(str(n), sp(13), INK)
        Color(1, 1, 1, 1)
        Rectangle(texture=t, size=t.size,
                  pos=(cx - t.width / 2, cy - t.height / 2))

    # ---- touch ----------------------------------------------------------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        # ignore right-click / scroll-wheel events from a desktop mouse
        if getattr(touch, "button", "left") != "left":
            return False
        x0, y0, w, h, m, cw = self._geom()
        col = int((touch.x - x0) // cw)
        col = max(0, min(COLS - 1, col))
        half = "R" if touch.y > y0 + h / 2 else "L"   # which half was tapped
        if col == 6:
            self.app.tap("bar", None, half)
        elif col == 13:
            self.app.tap("off", None, half)
        else:
            idx = col if col < 6 else col - 1       # 0..11 along the row
            top = touch.y > y0 + h / 2
            p = (13 + idx) if top else (12 - idx)
            self.app.tap("point", p - 1)
        return True


class BGApp(App):
    title = "Backgammon Best Move"

    def build(self):
        Window.clearcolor = BG
        if platform in ("win", "linux", "macosx"):
            Window.size = (420, 780)          # phone-shaped preview on a PC
        self.pos_base = bg.opening_position()
        self.pos_view = self.pos_base
        self.previewing = False
        self.flip = False        # True while Red is the side to move
        self.last_grade = ""
        self.cube_val, self.cube_owner = 1, None   # owner: None / "L" / "R"
        self.cube_offer = None      # side ("L"/"R") that has just doubled
        self.cube_result = None     # set when a double is passed
        self.preview_cand = None  # analysis line currently shown on the board
        self.busy = False
        self.cands = []
        self.net = None
        try:
            if os.path.exists(NETFILE):
                self.net = bgnet.load(NETFILE)
                bg.set_net(self.net)
        except Exception:
            self.net = None            # fall back to the heuristic

        root = BoxLayout(orientation="vertical", padding=dp(6),
                         spacing=dp(4))
        self.board = BoardView(self, size_hint_y=0.42)
        root.add_widget(self.board)

        self.sel = None          # checker picked up in Move mode
        self.targets = []        # legal destinations of that checker
        self.turn = None         # bg.Turn: the manual turn being played
        self.rating_token = None  # identifies the rating currently in flight
        self.note = ""           # last "why nothing happened" message
        self.status = Label(text="", size_hint_y=None, height=dp(50),
                            font_size=sp(11), halign="center",
                            valign="middle", markup=True)
        self.status.bind(size=lambda w, s: setattr(w, "text_size", s))
        root.add_widget(self.status)

        # tools: side + add/remove
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.t_light = ToggleButton(text="Light", group="side",
                                    state="down", allow_no_selection=False)
        self.t_red = ToggleButton(text="Red", group="side",
                                  allow_no_selection=False)
        self.t_add = ToggleButton(text="Add", group="mode", state="down",
                                  allow_no_selection=False)
        self.t_rem = ToggleButton(text="Remove", group="mode",
                                  allow_no_selection=False)
        self.t_move = ToggleButton(text="Move", group="mode",
                                   allow_no_selection=False)
        for b in (self.t_light, self.t_red, self.t_add, self.t_rem,
                  self.t_move):
            row.add_widget(b)
        root.add_widget(row)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        for txt, fn in (("Opening", self.ask_opening), ("Clear", self.ask_clear),
                        ("Switch turn", self.do_switch),
                        ("Reset view", self.do_reset_view)):
            b = Button(text=txt)
            b.bind(on_release=lambda _b, f=fn: f())
            row.add_widget(b)
        self.eval_btn = Button(text=self.eval_label())
        self.eval_btn.bind(on_release=lambda *_: self.do_toggle_eval())
        row.add_widget(self.eval_btn)
        root.add_widget(row)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.b_double = Button(text="Double", bold=True,
                               background_color=(0.85, 0.5, 0.1, 1))
        self.b_take = Button(text="Take", bold=True,
                             background_color=(0.2, 0.6, 0.3, 1))
        self.b_pass = Button(text="Pass", bold=True,
                             background_color=(0.7, 0.25, 0.25, 1))
        self.b_help = Button(text="Help", bold=True,
                             background_color=(0.3, 0.45, 0.8, 1))
        for b, fn in ((self.b_double, self.do_double),
                      (self.b_take, self.do_take), (self.b_pass, self.do_pass),
                      (self.b_help, self.show_help)):
            b.bind(on_release=lambda _b, f=fn: f())
            row.add_widget(b)
        root.add_widget(row)

        # dice
        self.dice = {}
        for name in ("d1", "d2"):
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            row.add_widget(Label(text="Die " + name[1], size_hint_x=0.9,
                                 font_size=sp(12)))
            for v in range(1, 7):
                tb = ToggleButton(text=str(v), group=name)
                tb.value = v
                row.add_widget(tb)
            self.dice[name] = row
            root.add_widget(row)

        arow = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
        self.go = Button(text="ANALYZE", bold=True,
                         background_color=(0.1, 0.55, 0.35, 1))
        self.go.bind(on_release=lambda *_: self.do_analyze())
        roll = Button(text="Roll dice", size_hint_x=0.36, bold=True,
                      background_color=(0.25, 0.4, 0.75, 1))
        roll.bind(on_release=lambda *_: self.do_roll())
        undo = Button(text="Undo move", size_hint_x=0.32)
        undo.bind(on_release=lambda *_: self.do_undo())
        arow.add_widget(self.go)
        arow.add_widget(roll)
        arow.add_widget(undo)
        root.add_widget(arow)

        self.results = GridLayout(cols=1, size_hint_y=None, spacing=dp(3))
        self.results.bind(minimum_height=self.results.setter("height"))
        sv = ScrollView(size_hint_y=0.34)
        sv.add_widget(self.results)
        root.add_widget(sv)
        self.say("Set up the board, choose both dice, press ANALYZE.")
        self.refresh()
        for b in (self.t_light, self.t_red, self.t_add, self.t_rem,
                  self.t_move):
            b.bind(state=self.on_tool_change)
        for row in self.dice.values():
            for tb in row.children:
                if isinstance(tb, ToggleButton):
                    tb.bind(state=self.on_dice_change)
        self.root_view, self.help_view = root, None
        return root

    # ---- help page --------------------------------------------------------
    def show_help(self):
        if self.help_view is None:
            box = BoxLayout(orientation="vertical", padding=dp(8),
                            spacing=dp(6))
            sv = ScrollView(do_scroll_x=False)
            lab = Label(text=HELP_TEXT, markup=True, size_hint_y=None,
                        halign="left", valign="top", font_size=sp(14),
                        text_size=(max(Window.width - dp(40), 200), None))
            lab.bind(texture_size=lambda w, v: setattr(w, "height", v[1] + dp(20)))
            Window.bind(width=lambda w, v: setattr(
                lab, "text_size", (max(v - dp(40), 200), None)))
            sv.add_widget(lab)
            box.add_widget(sv)
            close = Button(text="Close help and return to the board",
                           size_hint_y=None, height=dp(52), bold=True,
                           background_color=(0.2, 0.6, 0.3, 1))
            close.bind(on_release=lambda *_: self.close_help())
            box.add_widget(close)
            self.help_view = box
        self._main_widgets = list(reversed(self.root_view.children))
        self.root_view.clear_widgets()
        self.root_view.add_widget(self.help_view)

    def close_help(self):
        self.root_view.clear_widgets()
        for w in self._main_widgets:          # original order, same layout
            self.root_view.add_widget(w)
        self.refresh()

    # ---- helpers --------------------------------------------------------
    def game_over(self, pos=None):
        """None while the game is on; otherwise (winner, points, kind) once a
        side has borne off all 15 checkers (cubeless: 1 / 2 gammon / 3
        backgammon). `pos` is in the mover's frame, like pos_base."""
        if self.cube_result is not None:
            return self.cube_result
        p = self.pos_base if pos is None else pos
        if p.off_me == 15:
            winner, loser_off, loser_bar = self.me_name(), p.off_opp, p.bar_opp
            hit_home = any(x < 0 for x in p.board[0:6])
        elif p.off_opp == 15:
            winner, loser_off, loser_bar = self.opp_name(), p.off_me, p.bar_me
            hit_home = any(x > 0 for x in p.board[18:24])
        else:
            return None
        base, kind = (1, "single game")
        if loser_off == 0:
            base, kind = ((3, "backgammon") if loser_bar > 0 or hit_home
                          else (2, "gammon"))
        return winner, base * self.cube_val, kind

    def result_text(self, pos=None):
        g = self.game_over(pos)
        if g is None:
            return ""
        how = ("after the double was passed" if g[2] == "pass" else
               "a %s%s" % (g[2], " x cube %d" % self.cube_val
                           if self.cube_val > 1 else ""))
        return "GAME OVER: %s wins %d point%s (%s). Press Opening to start " \
               "a new game." % (g[0], g[1], "" if g[1] == 1 else "s", how)

    # ---- doubling cube ---------------------------------------------------
    @staticmethod
    def _name_of(side):
        return "Light" if side == "L" else "Red"

    def side_code(self):
        return "R" if self.flip else "L"

    def cube_text(self):
        if self.cube_owner is None:
            return "Cube: centred (1)"
        return "Cube: %d (%s)" % (self.cube_val, self._name_of(self.cube_owner))

    def cube_reset(self):
        self.cube_val, self.cube_owner = 1, None
        self.cube_offer, self.cube_result = None, None

    def _offer_pending(self):
        if self.cube_offer is None:
            return False
        self.note = ("%s has doubled to %d: %s must press Take or Pass."
                     % (self._name_of(self.cube_offer), self.cube_val * 2,
                        self._name_of("R" if self.cube_offer == "L" else "L")))
        self.sel, self.targets = None, []
        return True

    def can_double(self):
        if self.game_over() or self.cube_offer is not None or self.busy:
            return False
        if self.cube_val >= 64:
            return False
        if self.cube_owner not in (None, self.side_code()):
            return False
        t = self.turn
        return not (t is not None and t.used)

    def do_double(self):
        if self.busy:
            return
        if self.game_over():
            self.note = self.result_text()
        elif self.cube_offer is not None:
            self._offer_pending()
        elif self.cube_val >= 64:
            self.note = "The cube is already at 64."
        elif self.cube_owner not in (None, self.side_code()):
            self.note = ("%s owns the cube, so only %s may redouble."
                         % (self._name_of(self.cube_owner),
                            self._name_of(self.cube_owner)))
        elif self.turn is not None and self.turn.used:
            self.note = ("You can only double before moving. Undo the move "
                         "first.")
        elif self.die("d1") is not None or self.die("d2") is not None:
            self.note = ("Double BEFORE rolling: clear both dice (tap each "
                         "selected die) or press Switch turn first.")
        else:
            self._begin_edit()
            self.cube_offer = self.side_code()
            self.sel, self.targets, self.turn = None, [], None
            who, other = (self._name_of(self.cube_offer),
                          self._name_of("R" if self.cube_offer == "L" else "L"))
            self.say("%s doubles to %d. %s: Take (play on for %d, you own the "
                     "cube) or Pass (lose %d)?" % (who, self.cube_val * 2,
                                                   other, self.cube_val * 2,
                                                   self.cube_val))
            self.note = ""
        self.refresh()

    def do_take(self):
        if self.cube_offer is None:
            self.note = "Nobody has doubled."
            self.refresh()
            return
        doubler = self.cube_offer
        taker = "R" if doubler == "L" else "L"
        self.cube_val *= 2
        self.cube_owner, self.cube_offer = taker, None
        self.say("%s takes. The cube is at %d and %s owns it. %s to roll."
                 % (self._name_of(taker), self.cube_val, self._name_of(taker),
                    self._name_of(doubler)))
        self.refresh()

    def do_pass(self):
        if self.cube_offer is None:
            self.note = "Nobody has doubled."
            self.refresh()
            return
        doubler = self.cube_offer
        self.cube_result = (self._name_of(doubler), self.cube_val, "pass")
        self.cube_offer = None
        self.say(self.result_text())
        self.refresh()

    def me_name(self):
        return "Red" if self.flip else "Light"

    def opp_name(self):
        return "Light" if self.flip else "Red"

    def side(self):
        return "L" if self.t_light.state == "down" else "R"

    def delta(self):
        return 1 if self.t_add.state == "down" else -1

    def mode(self):
        if self.t_move.state == "down":
            return "move"
        return "add" if self.t_add.state == "down" else "remove"

    def on_tool_change(self, *_):
        self.sel, self.targets, self.note = None, [], ""
        self.refresh()

    def on_dice_change(self, *_):
        """A new roll: any manual turn in progress is over."""
        self.cancel_rating()
        self.turn, self.sel, self.targets, self.note = None, None, [], ""
        self.refresh()

    def do_roll(self):
        """Roll two random dice into the dice rows. Moves stay manual: you
        still tap the checkers (or ANALYZE) afterwards."""
        if self.busy:
            self.note = "Wait for the analysis to finish before rolling."
            self.refresh()
            return
        if self.game_over():
            self.note = self.result_text()
            self.refresh()
            return
        if self._offer_pending():
            self.refresh()
            return
        t = self.turn
        if t is not None and t.used:
            self.note = ("This turn is not over: finish or Undo your move, "
                         "then press Switch turn before rolling again."
                         if not t.finished() else
                         "Turn complete: press Switch turn before the next "
                         "roll (or Undo move to change this one).")
            self.refresh()
            return
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        for name, v in (("d1", d1), ("d2", d2)):
            kids = [c for c in self.dice[name].children
                    if isinstance(c, ToggleButton)
                    and getattr(c, "value", None) is not None]
            for c in kids:
                if c.value != v:
                    c.state = "normal"
            for c in kids:
                if c.value == v:
                    c.state = "down"
        self.on_dice_change()               # fresh roll: reset turn state
        self.previewing = False
        self.say("%s rolled %d-%d. Tap a checker to move it, or press "
                 "ANALYZE." % (self.me_name(), d1, d2))
        self.refresh()

    def dice_left(self):
        if self.turn is not None:
            return " ".join(str(d) for d in sorted(self.turn.remaining,
                                                   reverse=True))
        d1, d2 = self.die("d1"), self.die("d2")
        if d1 is None or d2 is None:
            return "-"
        return " ".join(str(d) for d in ([d1] * 4 if d1 == d2 else [d1, d2]))

    def tool_hint(self):
        name = "Light" if self.side() == "L" else "Red"
        m = self.mode()
        if m == "move":
            if self.die("d1") is None or self.die("d2") is None:
                return "Move plays legal moves only: pick both dice first."
            if self.turn is not None and self.turn.used and \
                    self.turn.finished():
                return ("Turn complete. Undo move, or press Switch turn to hand "
                        "over to %s." % self.opp_name())
            if self.sel is not None:
                return ("Tap a green spot to move there (tap the checker "
                        "again to cancel). Dice left: %s." % self.dice_left())
            return ("%s to move: tap a %s checker to see its legal moves. "
                    "Dice left: %s." % (self.me_name(), self.me_name(),
                                        self.dice_left()))
        return "%s %s: tap a point to %s a %s checker." % (
            name, m, m, name)

    def die(self, name):
        for ch in self.dice[name].children:
            if isinstance(ch, ToggleButton) and ch.state == "down":
                return ch.value
        return None

    def say(self, text):
        self.results.clear_widgets()
        lab = Label(text=text, size_hint_y=None, height=dp(60),
                    font_size=sp(13), halign="center", valign="middle")
        lab.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.results.add_widget(lab)

    def refresh(self):
        pos = self.pos_view
        me, opp = bg.pip_counts(pos)
        nh, loss, nb = bg.hit_stats(pos)
        mn, on = self.me_name(), self.opp_name()
        tag = ("  [b]PREVIEW (%s to roll)[/b]" % on) if self.previewing else ""
        probs = bg.validate(pos)
        warn = ("  [color=ff8844]%s[/color]" % "; ".join(probs)) if probs \
            and not self.previewing else ""
        over = self.result_text(self.pos_view)
        if over:
            hint = "[color=ff6666][b]%s[/b][/color]" % over
        elif self.previewing:
            hint = ("Previewing this line. Press Switch turn to PLAY it and "
                    "hand over to %s, or Reset view to cancel." % on)
        elif self.note:
            hint = "[color=ffcc66]%s[/color]" % self.note
        else:
            hint = self.tool_hint()
        self.status.text = (
            "[b]%s[/b]   Pips  %s %d  %s %d   |   %s hits a %s "
            "blot on %d/36 (%.1f%%)   |   %s%s%s\n%s"
            % ("Game over" if over else "%s to move" % mn, mn, me, on, opp,
               on, mn, nh, nh / 0.36, self.cube_text(), tag, warn, hint))
        for b, ok in ((self.b_double, self.can_double()),
                      (self.b_take, self.cube_offer is not None),
                      (self.b_pass, self.cube_offer is not None)):
            b.disabled = not ok
        self.board.redraw()

    # ---- editing --------------------------------------------------------
    def _begin_edit(self):
        if self.previewing:
            self.previewing = False
            self.pos_view = self.pos_base
        return self.pos_base

    def tap(self, kind, idx=None, half=None):
        if self.busy:
            return
        pos = self._begin_edit()
        self.note = ""
        if self.flip:           # board is drawn in fixed colours
            if idx is not None:
                idx = 23 - idx
            if half is not None:
                half = "R" if half == "L" else "L"
        if self.mode() == "move":
            self._tap_move(pos, kind, idx, half)
        else:
            self.sel, self.targets, self.turn = None, [], None
            s, d = self.side(), self.delta()
            if self.flip:
                s = "R" if s == "L" else "L"
            if kind == "point":
                ok = bg.edit_point(pos, idx, s, d)
            elif kind == "bar":
                ok = bg.edit_bar(pos, s, d)
            else:
                ok = bg.edit_off(pos, s, d)
            if not ok:
                self.note = bg.refusal_reason(pos, kind, idx, s, d)
        self.pos_view = self.pos_base
        self.refresh()

    @staticmethod
    def _spot(dst):
        return "off" if dst == -1 else str(dst + 1)

    @staticmethod
    def _reach(t, src):
        """Everywhere the checker on `src` can get with the dice left, using
        one die or several in a row (13/9/8 -> '13/8'). Maps destination to
        the shortest list of single-die steps; every step is a legal move."""
        best = {}

        def walk(cur, path):
            for m in t.legal_moves():
                if m[0] != cur:
                    continue
                step = path + [m]
                if m[1] not in best or len(step) < len(best[m[1]]):
                    best[m[1]] = step
                if m[1] != -1:
                    t.play(m[0], m[1], m[2])
                    walk(m[1], step)
                    t.undo()
        walk(src, [])
        return best

    def _tap_move(self, pos, kind, idx, half):
        """Move mode = real play for Light with the chosen dice. Only legal
        moves are accepted; tap a checker to see where it may go."""
        if self.game_over(pos):
            self.note = self.result_text(pos)
            self.sel, self.targets = None, []
            return
        if self._offer_pending():
            return
        d1, d2 = self.die("d1"), self.die("d2")
        if d1 is None or d2 is None:
            self.note = ("Pick both dice first: Move plays legal moves only, "
                         "so it needs the roll.")
            return
        probs = bg.validate(pos)
        if probs:
            self.note = "Fix the board first: " + "; ".join(probs)
            return
        if self.turn is None:
            self.turn = bg.Turn(pos, d1, d2)
            self.sel, self.targets = None, []
        t = self.turn
        if t.total == 0:
            self.note = "No legal move with %d-%d: you must pass." % (d1, d2)
            return
        if t.finished():
            self.note = ("Turn complete: %s. Undo move to change it, or "
                         "press Switch turn for %s." % (t.notation() or "-",
                                                        self.opp_name()))
            return
        moves = t.legal_moves()
        tapped = idx if kind == "point" else (24 if kind == "bar" else -1)

        # a checker is already picked up: is this a legal place to put it?
        if self.sel is not None:
            src = 24 if self.sel[0] == "bar" else self.sel[1]
            if tapped == src and (kind != "bar" or half == "L"):
                self.sel, self.targets = None, []          # cancel
                return
            cand = [m for m in moves if m[0] == src and m[1] == tapped]
            reach = self._reach(t, src)
            if cand or tapped in reach:
                steps = ([(src, tapped, min(m[2] for m in cand))] if cand
                         else reach[tapped])
                hit = False
                for a, b, die in steps:       # several dice = several steps
                    hit = t.play(a, b, die) or hit
                self.pos_base = t.pos
                self.sel, self.targets = None, []
                if t.finished():
                    self.note = ("Turn complete: %s.%s Undo move to change "
                                 "it, or press Switch turn for %s."
                                 % (t.notation(),
                                    " %s's checker is on the bar."
                                    % self.opp_name() if hit else "",
                                    self.opp_name()))
                    self.rate_turn()
                else:
                    self.note = "Played %s.%s Dice left: %s." % (
                        t.notation(), " Hit!" if hit else "",
                        self.dice_left())
                return
            own = (kind == "point" and pos.board[idx] > 0) or \
                  (kind == "bar" and half == "L" and pos.bar_me > 0)
            if not (own and any(m[0] == tapped for m in moves)):
                opts = ", ".join(
                    "%s (%s)" % (self._spot(d), "+".join(str(x[2]) for x in p))
                    for d, p in sorted(self._reach(t, src).items(),
                                       key=lambda kv: -kv[0]))
                self.note = ("Not legal. This checker can go to: %s."
                             % (opts or "nowhere"))
                return
            # otherwise: the player picked a different movable checker

        # pick a checker up
        if kind == "point":
            v = pos.board[idx]
            if v == 0:
                self.note = "Point %d is empty: tap a %s checker." % (
                    idx + 1, self.me_name())
                return
            if v < 0:
                self.note = ("It is %s's move: %s checkers can't be moved. "
                             "Press Switch turn to hand over."
                             % (self.me_name(), self.opp_name()))
                return
        elif kind == "bar":
            if half == "R" or pos.bar_me <= 0:
                self.note = "There is no %s checker on the bar." % self.me_name()
                return
        else:
            self.note = "Pick up a checker first, then tap the OFF tray."
            return
        dests = [m for m in moves if m[0] == tapped]
        if not dests:
            if pos.bar_me > 0 and tapped != 24:
                self.note = "You must enter your checker from the bar first."
            else:
                self.note = ("That checker has no legal move with the dice "
                             "left (%s)." % self.dice_left())
            return
        self.sel = (kind, idx, "L")
        self.targets = sorted(self._reach(t, tapped))

    def do_undo(self):
        cancelled = self.cancel_rating()
        if self.busy:                       # a full analysis is running
            return
        self.previewing = False
        if self.turn is None or not self.turn.history:
            self.note = "Nothing to undo."
        else:
            self.turn.undo()
            self.pos_base = self.turn.pos
            self.sel, self.targets = None, []
            self.note = "Undid the last move."
        if cancelled:
            self.say("Move again to get a rating, or press ANALYZE.")
        self.pos_view = self.pos_base
        self.refresh()

    def eval_label(self):
        if self.net is None:
            return "Eval: Heuristic"
        return "Eval: Neural" if bg.using_net() else "Eval: Heuristic"

    def do_toggle_eval(self):
        if self.net is None:
            self.say("No net.json found next to main.py, so only the "
                     "heuristic evaluator is available. Train one with "
                     "train.py.")
            return
        bg.set_net(None if bg.using_net() else self.net)
        self.eval_btn.text = self.eval_label()
        self.say("Using the %s evaluator. Press ANALYZE again."
                 % ("neural-network" if bg.using_net() else "heuristic"))

    DOUBLE_TAP = 1.5      # seconds allowed between the two taps

    def _confirmed(self, name, what):
        """Destructive buttons need a quick double tap, so one accidental
        press can't wipe the board. True on the second tap."""
        now = time.time()
        last = getattr(self, "_armed", {}).get(name, -99.0)
        if now - last <= self.DOUBLE_TAP:
            self._armed[name] = -99.0
            return True
        if not hasattr(self, "_armed"):
            self._armed = {}
        self._armed[name] = now
        self.note = "Tap %s again quickly to %s." % (name, what)
        self.refresh()
        return False

    def ask_opening(self, *a):
        if self._confirmed("Opening", "set up the opening position "
                           "(this replaces the current board)"):
            self.do_opening()

    def ask_clear(self, *a):
        if self._confirmed("Clear", "clear the board"):
            self.do_clear()

    def do_opening(self):
        self.pos_base = bg.opening_position()
        self.pos_view, self.previewing = self.pos_base, False
        self.flip, self.last_grade = False, ""
        self.cube_reset()
        self.cancel_rating()
        self.sel, self.targets, self.turn, self.note = None, [], None, ""
        self.say("Opening position loaded.")
        self.refresh()

    def do_clear(self):
        self.cube_reset()
        self.pos_base = bg.Position()
        self.pos_view, self.previewing = self.pos_base, False
        self.cancel_rating()
        self.sel, self.targets, self.turn, self.note = None, [], None, ""
        self.say("Board cleared. Tap points to add checkers (15 each).")
        self.refresh()

    def do_switch(self):
        """Hand the roll to the other player. The board stays exactly as it
        is on screen (colours never change); only the side to move does."""
        if self.busy:
            self.note = "Wait for the analysis to finish, then switch."
            self.refresh()
            return
        if self._offer_pending():
            self.refresh()
            return
        t = self.turn
        if t is not None and t.used and not t.finished() \
                and not self.game_over():
            self.note = ("%s still has dice to play (%s). Finish the move or "
                         "Undo it before switching." % (self.me_name(),
                                                        self.dice_left()))
            self.refresh()
            return
        played = ""
        if self.previewing and self.preview_cand is not None:
            # a line from the analysis is on the board: Switch turn plays it
            c = self.preview_cand
            self.pos_base = c.pos.copy()
            played = "%s played %s. " % (self.me_name(),
                                         c.notation or "(no move)")
            self.previewing = False
        pos = self._begin_edit()
        if self.game_over(pos):          # nobody rolls after the last checker
            self.pos_view, self.preview_cand = self.pos_base, None
            self.turn, self.sel, self.targets, self.note = None, None, [], ""
            self.say("%s%s" % (played, self.result_text(pos)))
            self.refresh()
            return
        self.pos_base = pos.flipped()
        self.pos_view = self.pos_base
        self.preview_cand = None
        self.flip = not self.flip
        self.sel, self.targets, self.turn, self.note = None, [], None, ""
        self.cands = []
        for row in self.dice.values():          # next player rolls afresh
            for tb in row.children:
                if isinstance(tb, ToggleButton):
                    tb.state = "normal"
        self.sel, self.targets, self.turn, self.note = None, [], None, ""
        if self.t_move.state != "down":
            self.t_move.state = "down"
        last = ("\nLast play: %s" % self.last_grade) if self.last_grade else ""
        self.say("%s%s to roll. Pick the dice, then ANALYZE or move the "
                 "checkers yourself.%s" % (played, self.me_name(), last))
        self.refresh()

    do_swap = do_switch              # old name

    def do_reset_view(self):
        self.previewing = False
        self.sel = None
        self.pos_view = self.pos_base
        self.refresh()

    # ---- analysis -------------------------------------------------------
    def do_analyze(self):
        if self.busy:
            return
        if self.turn is not None and self.turn.used:
            self.say("The analysis is for the position BEFORE you move. "
                     "Press Undo move until the board is back at the start.")
            return
        pos = self._begin_edit().copy()
        if self.game_over(pos):
            self.say(self.result_text(pos))
            return
        if self.cube_offer is not None:
            self._offer_pending()
            self.say(self.note)
            return
        d1, d2 = self.die("d1"), self.die("d2")
        if d1 is None or d2 is None:
            self.say("Pick both dice first.")
            return
        probs = bg.validate(pos)
        if probs:
            self.say("Fix the board first:\n" + "; ".join(probs))
            return
        self.busy = True
        self.go.text = "Thinking..."
        self.go.disabled = True
        self.say("Evaluating every legal play against all 21 opposing rolls...")

        def work():
            try:
                c = bg.analyze(pos, d1, d2, depth=2, top_n=8)
                err = None
            except Exception as e:           # keep the UI alive
                c, err = [], repr(e)
            Clock.schedule_once(lambda dt: self.show(c, d1, d2, err))

        threading.Thread(target=work, daemon=True).start()

    def rate_turn(self):
        """Grade the finished manual turn against the engine (background)."""
        t = self.turn
        start, final = t.start.copy(), t.pos.copy()
        d1, d2, used = t.dice[0], t.dice[1], t.used
        token = object()
        self.rating_token = token
        self.busy = True
        self.go.text = "Rating..."
        self.go.disabled = True
        self.say("Rating your play against the engine...")

        def work():
            try:
                r, err = bg.rate_play(start, d1, d2, final), None
                if r is None:
                    err = "could not match your play to a legal play"
            except Exception as e:           # keep the UI alive
                r, err = None, repr(e)
            Clock.schedule_once(
                lambda dt: self.show_rating(token, t, used, r, d1, d2, err))

        threading.Thread(target=work, daemon=True).start()

    def cancel_rating(self):
        """Drop a rating that is still being computed (its result is ignored)."""
        if self.rating_token is None:
            return False
        self.rating_token = None
        self.busy = False
        self.go.text = "ANALYZE"
        self.go.disabled = False
        return True

    def show_rating(self, token, turn, used, rating, d1, d2, err):
        if token is not self.rating_token:       # cancelled: ignore silently
            return
        self.rating_token = None
        if self.turn is not turn or turn.used != used:      # defensive
            self.busy = False
            self.go.text = "ANALYZE"
            self.go.disabled = False
            self.say("Move again to get a rating, or press ANALYZE.")
            return
        if err:
            self.busy = False
            self.go.text = "ANALYZE"
            self.go.disabled = False
            self.say("Could not rate your play: " + err)
            return
        self.show(rating["cands"], d1, d2, None, rating=rating)

    def show(self, cands, d1, d2, err, rating=None):
        self.busy = False
        self.go.text = "ANALYZE"
        self.go.disabled = False
        self.cands = cands
        self.results.clear_widgets()
        if err:
            self.say("Error: " + err)
            return
        if not cands:
            self.say("No legal move with %d-%d: you must pass." % (d1, d2))
            return
        best = cands[0]
        if rating is not None:
            headline, detail = bg.rating_text(rating)
            self.last_grade = "%s %s" % (self.me_name(), headline[0].lower()
                                         + headline[1:])
            colour = {"Best move": "7dff9a", "Essentially equal": "7dff9a",
                      "Good": "c8f08a", "Inaccuracy": "ffd36b",
                      "Mistake": "ff9a5c", "Blunder": "ff6b6b"}.get(
                detail.split(":")[0], "ffffff")
            text = ("[b]%s[/b]\n[color=%s]%s[/color]\nBest: %s (%s for %s). "
                    "Your row is orange; tap any line to preview it."
                    % (headline, colour, detail, best.notation or "(no move)",
                       bg.score_text(best), self.me_name()))
            hh = dp(86)
        else:
            text = ("[b]Best for %s: %s[/b]   (%s)\n"
                    "Tap a line to preview the resulting position."
                    % (self.me_name(), best.notation or "(no move)",
                       bg.score_text(best)))
            hh = dp(52)
        head = Label(
            text=text,
            markup=True, size_hint_y=None, height=hh, font_size=sp(13),
            halign="center", valign="middle")
        head.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.results.add_widget(head)
        for i, c in enumerate(cands[:25], 1):
            shot = ("%d/36 shots" % c.shot_rolls) if c.blots else "safe"
            gap = "" if i == 1 else "  (%s)" % bg.gap_text(cands[0], c)
            mine = rating is not None and c is rating["mine"]
            btn = Button(
                text="%d.  %s%s\n[size=%d]%s%s   |   %s   |   %d blot%s%s"
                     "   |   %s[/size]"
                     % (i, c.notation or "(no move)",
                        "   [b]<- YOUR PLAY[/b]" if mine else "",
                        int(sp(10)),
                        bg.score_text(c), gap, shot, c.blots,
                        "" if c.blots == 1 else "s",
                        ("   |   " + bg.dance_text(c)) if c.dance is not None
                        else "",
                        "2-ply" if c.ply == 2 else "1-ply"),
                markup=True, size_hint_y=None, height=dp(56),
                halign="left", valign="middle", font_size=sp(14),
                background_color=(0.62, 0.38, 0.1, 1) if mine
                else (0.2, 0.34, 0.5, 1) if i == 1
                else (0.18, 0.2, 0.24, 1))
            btn.bind(size=lambda w, s: setattr(w, "text_size",
                                               (s[0] - dp(12), s[1])))
            btn.bind(on_release=lambda _b, cc=c: self.preview(cc))
            self.results.add_widget(btn)

    def preview(self, cand):
        self.preview_cand = cand
        self.previewing = True
        self.pos_view = cand.pos
        self.refresh()


if __name__ == "__main__":
    BGApp().run()
