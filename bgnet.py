"""bgnet.py -- neural-network position evaluator (pure Python, no NumPy).

This module is what the phone app uses. Training lives in train.py (NumPy).

Viewpoint convention
--------------------
The network always sees the position from the side that is ON ROLL
(that side's checkers are positive, exactly like bgengine.Position).
It outputs five probabilities for the side on roll:

    o0 = P(win)
    o1 = P(win a gammon or better)
    o2 = P(win a backgammon)
    o3 = P(lose a gammon or worse)
    o4 = P(lose a backgammon)

Cubeless equity (points per game) = (2*o0 - 1) + (o1 - o3) + (o2 - o4)

Inputs: 198 numbers (a TD-Gammon-style encoding). Almost all are zero, so the
forward pass only touches the non-zero ones ("sparse"), which keeps pure
Python fast enough for the 2-ply search on a phone.
"""
import json
import math
from operator import mul

import bgengine as bg

N_IN = 198
N_OUT = 5


# --------------------------------------------------------------------------
# Feature encoding
# --------------------------------------------------------------------------
def encode(pos):
    """Sparse features of `pos` for the side on roll -> (indices, values).

    0..95    my checkers, 4 units per point:  >=1, >=2, >=3, (n-3)/2
    96..191  opponent checkers, same layout
    192/193  my bar / opp bar  (n/2)
    194/195  my off / opp off  (n/15)
    196      contact still exists (1.0)
    197      pip-count lead (opp - me)/50, clipped to +-3
    """
    idx = []
    val = []
    b = pos.board
    me_pips = 25 * pos.bar_me
    opp_pips = 25 * pos.bar_opp
    max_me = 24 if pos.bar_me else -1
    min_opp = -1 if pos.bar_opp else 99
    for i in range(24):
        v = b[i]
        if v == 0:
            continue
        if v > 0:
            base = i * 4
            n = v
            me_pips += (i + 1) * n
            if i > max_me:
                max_me = i
        else:
            base = 96 + i * 4
            n = -v
            opp_pips += (24 - i) * n
            if i < min_opp:
                min_opp = i
        idx.append(base)
        val.append(1.0)
        if n >= 2:
            idx.append(base + 1)
            val.append(1.0)
            if n >= 3:
                idx.append(base + 2)
                val.append(1.0)
                if n > 3:
                    idx.append(base + 3)
                    val.append((n - 3) / 2.0)
    if pos.bar_me:
        idx.append(192)
        val.append(pos.bar_me / 2.0)
    if pos.bar_opp:
        idx.append(193)
        val.append(pos.bar_opp / 2.0)
    if pos.off_me:
        idx.append(194)
        val.append(pos.off_me / 15.0)
    if pos.off_opp:
        idx.append(195)
        val.append(pos.off_opp / 15.0)
    if max_me > min_opp:
        idx.append(196)
        val.append(1.0)
    d = (opp_pips - me_pips) / 50.0
    if d:
        idx.append(197)
        val.append(max(-3.0, min(3.0, d)))
    return idx, val


# --------------------------------------------------------------------------
# Probabilities, equity, terminal positions
# --------------------------------------------------------------------------
def equity(o):
    """Cubeless equity for the side on roll from the 5 probabilities."""
    return (2.0 * o[0] - 1.0) + (o[1] - o[3]) + (o[2] - o[4])


def flip_probs(o):
    """The same position described by the OTHER side (self-inverse)."""
    return [1.0 - o[0], o[3], o[4], o[1], o[2]]


def terminal_points(pos):
    """Points won (1, 2 or 3) by 'me' (positive side) in a finished game."""
    if pos.off_opp > 0:
        return 1.0
    if pos.bar_opp or any(pos.board[i] < 0 for i in range(6)):
        return 3.0
    return 2.0


# --------------------------------------------------------------------------
# Pure-Python network
# --------------------------------------------------------------------------
class PyNet:
    def __init__(self, W1, b1, W2, b2, meta=None):
        self.W1 = W1                      # N_IN lists of H floats
        self.b1 = b1                      # H floats
        self.W2T = [list(col) for col in zip(*W2)]   # N_OUT lists of H floats
        self.b2 = b2                      # N_OUT floats
        self.hidden = len(b1)
        self.meta = meta or {}

    def probs(self, pos):
        idx, val = encode(pos)
        h = self.b1
        W1 = self.W1
        for i, v in zip(idx, val):
            row = W1[i]
            if v == 1.0:
                h = [a + r for a, r in zip(h, row)]
            else:
                h = [a + v * r for a, r in zip(h, row)]
        h = [math.tanh(x) for x in h]
        out = []
        for b, w in zip(self.b2, self.W2T):
            z = b + sum(map(mul, h, w))
            z = -30.0 if z < -30.0 else (30.0 if z > 30.0 else z)
            out.append(1.0 / (1.0 + math.exp(-z)))
        return out

    def evaluate(self, pos, me_on_roll):
        """Same contract as bgengine.heuristic_evaluate: equity for 'me'."""
        if pos.off_me >= 15:
            return terminal_points(pos)
        if pos.off_opp >= 15:
            return -terminal_points(pos.flipped())
        if me_on_roll:
            return equity(self.probs(pos))
        return -equity(self.probs(pos.flipped()))


def load(path):
    """Load a net exported by train.py (net.json)."""
    with open(path) as f:
        d = json.load(f)
    if len(d["W1"]) != N_IN:
        raise ValueError("net.json has %d inputs, expected %d"
                         % (len(d["W1"]), N_IN))
    return PyNet(d["W1"], d["b1"], d["W2"], d["b2"], d.get("meta"))
