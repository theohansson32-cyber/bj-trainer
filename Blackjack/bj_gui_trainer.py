import random
import tkinter as tk
from dataclasses import dataclass
from typing import List, Tuple

# =========================
# Card / Hand utilities
# =========================

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_VALUES = {
    "A": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10,
}

def normalize_rank(c: str) -> str:
    return "10" if c in ["10", "J", "Q", "K"] else c

def hand_value(cards: List[str]) -> Tuple[int, bool]:
    """Return (total, is_soft)."""
    # Use normalized ranks for value
    vals = [normalize_rank(c) for c in cards]
    total = sum(11 if c == "A" else CARD_VALUES[c] for c in vals)
    aces = vals.count("A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    hard_total = sum(1 if c == "A" else CARD_VALUES[c] for c in vals)
    is_soft = ("A" in vals) and (total != hard_total)
    return total, is_soft

def can_split(cards: List[str]) -> bool:
    if len(cards) != 2:
        return False
    a = normalize_rank(cards[0])
    b = normalize_rank(cards[1])
    return a == b

# =========================
# Basic Strategy (S17, 6D, DAS, no surrender)
# =========================

def basic_strategy_action(player_cards: List[str], dealer_up: str, can_double: bool, can_split_now: bool) -> str:
    up = normalize_rank(dealer_up)

    # Splits
    if can_split_now and can_split(player_cards):
        pr = normalize_rank(player_cards[0])
        if pr == "A": return "P"
        if pr == "8": return "P"
        if pr == "10": return "S"
        if pr == "9":  return "P" if up in ["2","3","4","5","6","8","9"] else "S"
        if pr == "7":  return "P" if up in ["2","3","4","5","6","7"] else "H"
        if pr == "6":  return "P" if up in ["2","3","4","5","6"] else "H"
        if pr == "5":  return "D" if can_double and up in ["2","3","4","5","6","7","8","9"] else "H"
        if pr == "4":  return "P" if up in ["5","6"] else "H"
        if pr in ["2","3"]:
            return "P" if up in ["2","3","4","5","6","7"] else "H"

    total, soft = hand_value(player_cards)

    # Soft totals
    if soft:
        if total <= 17:
            if can_double:
                if total in [13,14] and up in ["5","6"]: return "D"
                if total in [15,16] and up in ["4","5","6"]: return "D"
                if total == 17 and up in ["3","4","5","6"]: return "D"
            return "H"
        if total == 18:
            if can_double and up in ["3","4","5","6"]: return "D"
            if up in ["2","7","8"]: return "S"
            return "H"
        if total == 19:
            if can_double and up == "6": return "D"
            return "S"
        return "S"  # 20+

    # Hard totals
    if total <= 8: return "H"
    if total == 9:  return "D" if can_double and up in ["3","4","5","6"] else "H"
    if total == 10: return "D" if can_double and up in ["2","3","4","5","6","7","8","9"] else "H"
    if total == 11: return "D" if can_double and up != "A" else "H"
    if total == 12: return "S" if up in ["4","5","6"] else "H"
    if 13 <= total <= 16: return "S" if up in ["2","3","4","5","6"] else "H"
    return "S"

# =========================
# Training scenario generator
# =========================

@dataclass
class Weights:
    hard: int = 2
    soft: int = 2
    pair: int = 2

def random_dealer_up() -> str:
    return random.choice(["2","3","4","5","6","7","8","9","10","A"])

def gen_soft_hand() -> List[str]:
    return ["A", random.choice(["2","3","4","5","6","7","8","9"])]

def gen_pair_hand() -> List[str]:
    r = random.choice(["A","2","3","4","5","6","7","8","9","10"])
    return [r, r]

def gen_hard_hand() -> List[str]:
    while True:
        c1 = random.choice(["2","3","4","5","6","7","8","9","10"])
        c2 = random.choice(["2","3","4","5","6","7","8","9","10"])
        total = CARD_VALUES[c1] + CARD_VALUES[c2]
        if 5 <= total <= 20:
            return [c1, c2]

def pick_training_hand(weights: Weights) -> Tuple[List[str], str, str]:
    pool = (["hard"] * max(0, weights.hard)) + (["soft"] * max(0, weights.soft)) + (["pair"] * max(0, weights.pair))
    if not pool:
        pool = ["hard"]
    cat = random.choice(pool)
    dealer = random_dealer_up()
    if cat == "soft":
        return gen_soft_hand(), dealer, "soft"
    if cat == "pair":
        return gen_pair_hand(), dealer, "pair"
    return gen_hard_hand(), dealer, "hard"

# =========================
# GUI App
# =========================

class BJTrainerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Blackjack Basic Strategy Trainer")

        self.weights = Weights(2, 2, 2)
        self.player_cards: List[str] = []
        self.dealer_up: str = "?"
        self.category: str = ""
        self.has_hit: bool = False
        self.locked: bool = False  # lock input after answer

        self.correct = 0
        self.total = 0

        self._build_ui()
        self.new_hand()

    def _build_ui(self):
        self.root.configure(padx=16, pady=16)

        title = tk.Label(self.root, text="Blackjack Trainer", font=("Helvetica", 18, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w")

        # Score
        self.score_var = tk.StringVar(value="Score: 0/0 (0.0%)")
        score = tk.Label(self.root, textvariable=self.score_var, font=("Helvetica", 11))
        score.grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 12))

        # Dealer
        dealer_lbl = tk.Label(self.root, text="Dealer (upcard):", font=("Helvetica", 12, "bold"))
        dealer_lbl.grid(row=2, column=0, sticky="w")

        self.dealer_frame = tk.Frame(self.root)
        self.dealer_frame.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 14))

        # Player
        player_lbl = tk.Label(self.root, text="Du:", font=("Helvetica", 12, "bold"))
        player_lbl.grid(row=4, column=0, sticky="w")

        self.player_frame = tk.Frame(self.root)
        self.player_frame.grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 6))

        self.info_var = tk.StringVar(value="")
        info = tk.Label(self.root, textvariable=self.info_var, font=("Helvetica", 11))
        info.grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 10))

        # Feedback
        self.feedback_var = tk.StringVar(value="Välj ett beslut.")
        self.feedback_lbl = tk.Label(self.root, textvariable=self.feedback_var, font=("Helvetica", 12))
        self.feedback_lbl.grid(row=7, column=0, columnspan=4, sticky="w", pady=(0, 12))

        # Buttons
        self.btn_hit = tk.Button(self.root, text="Hit", width=10, command=lambda: self.choose("H"))
        self.btn_stand = tk.Button(self.root, text="Stand", width=10, command=lambda: self.choose("S"))
        self.btn_double = tk.Button(self.root, text="Double", width=10, command=lambda: self.choose("D"))
        self.btn_split = tk.Button(self.root, text="Split", width=10, command=lambda: self.choose("P"))

        self.btn_hit.grid(row=8, column=0, sticky="w", padx=(0, 8))
        self.btn_stand.grid(row=8, column=1, sticky="w", padx=(0, 8))
        self.btn_double.grid(row=8, column=2, sticky="w", padx=(0, 8))
        self.btn_split.grid(row=8, column=3, sticky="w")

        self.btn_new = tk.Button(self.root, text="Ny hand", width=10, command=self.new_hand)
        self.btn_show = tk.Button(self.root, text="Visa basic", width=10, command=self.show_basic)
        self.btn_new.grid(row=9, column=0, sticky="w", pady=(10, 0), padx=(0, 8))
        self.btn_show.grid(row=9, column=1, sticky="w", pady=(10, 0))

        # Weights controls
        ctrl = tk.Label(self.root, text="Träningsvikter (högre = oftare):", font=("Helvetica", 12, "bold"))
        ctrl.grid(row=10, column=0, columnspan=4, sticky="w", pady=(18, 6))

        self.hard_var = tk.IntVar(value=self.weights.hard)
        self.soft_var = tk.IntVar(value=self.weights.soft)
        self.pair_var = tk.IntVar(value=self.weights.pair)

        self._spin("Hard", self.hard_var, 11, 0)
        self._spin("Soft", self.soft_var, 11, 1)
        self._spin("Pairs", self.pair_var, 11, 2)

        apply_btn = tk.Button(self.root, text="Apply", command=self.apply_weights)
        apply_btn.grid(row=11, column=3, sticky="w")

    def _spin(self, label: str, var: tk.IntVar, row: int, col: int):
        frame = tk.Frame(self.root)
        frame.grid(row=row, column=col, sticky="w", padx=(0, 10))
        tk.Label(frame, text=label).pack(side="left")
        tk.Spinbox(frame, from_=0, to=20, width=5, textvariable=var).pack(side="left", padx=(6, 0))

    def apply_weights(self):
        self.weights = Weights(self.hard_var.get(), self.soft_var.get(), self.pair_var.get())
        self.feedback_var.set("Vikter uppdaterade. Tryck 'Ny hand'.")

    def _render_cards(self):
        for w in self.dealer_frame.winfo_children():
            w.destroy()
        for w in self.player_frame.winfo_children():
            w.destroy()

        # Dealer card
        self._card_widget(self.dealer_frame, self.dealer_up).pack(side="left", padx=6)

        # Player cards
        for c in self.player_cards:
            self._card_widget(self.player_frame, c).pack(side="left", padx=6)

        total, soft = hand_value(self.player_cards)
        self.info_var.set(f"Kategori: {self.category} | Total: {total}{' (soft)' if soft else ''} | {'Kan splitta' if can_split(self.player_cards) else ''}")

    def _card_widget(self, parent: tk.Widget, rank: str) -> tk.Frame:
        # Simple "card" look
        f = tk.Frame(parent, width=60, height=90, bg="white", highlightbackground="#222", highlightthickness=2)
        f.pack_propagate(False)
        txt = tk.Label(f, text=rank, bg="white", fg="black", font=("Helvetica", 16, "bold"))
        txt.pack(expand=True)
        return f

    def _set_buttons_state(self):
        # Allowed: double and split only before any hit and only with 2 cards
        can_double_now = (not self.has_hit and len(self.player_cards) == 2)
        can_split_now = (not self.has_hit and len(self.player_cards) == 2 and can_split(self.player_cards))

        # lock after answer if you want "one decision only"
        if self.locked:
            for b in [self.btn_hit, self.btn_stand, self.btn_double, self.btn_split]:
                b.configure(state="disabled")
            return

        self.btn_hit.configure(state="normal")
        self.btn_stand.configure(state="normal")
        self.btn_double.configure(state="normal" if can_double_now else "disabled")
        self.btn_split.configure(state="normal" if can_split_now else "disabled")

    def new_hand(self):
        self.player_cards, self.dealer_up, self.category = pick_training_hand(self.weights)
        self.has_hit = False
        self.locked = False
        self.feedback_var.set("Välj ett beslut.")
        self._render_cards()
        self._set_buttons_state()

    def show_basic(self):
        can_double_now = (not self.has_hit and len(self.player_cards) == 2)
        can_split_now = (not self.has_hit and len(self.player_cards) == 2 and can_split(self.player_cards))
        sug = basic_strategy_action(self.player_cards, self.dealer_up, can_double_now, can_split_now)
        self.feedback_var.set(f"Basic strategy: {self._action_name(sug)}")

    def choose(self, action: str):
        if self.locked:
            return

        can_double_now = (not self.has_hit and len(self.player_cards) == 2)
        can_split_now = (not self.has_hit and len(self.player_cards) == 2 and can_split(self.player_cards))
        sug = basic_strategy_action(self.player_cards, self.dealer_up, can_double_now, can_split_now)

        self.total += 1
        if action == sug:
            self.correct += 1
            self.feedback_var.set(f"✅ Rätt! Basic: {self._action_name(sug)}")
        else:
            self.feedback_var.set(f"❌ Fel. Basic: {self._action_name(sug)} (du valde {self._action_name(action)})")

        self._update_score()

        # For this trainer: lock after FIRST decision (as you requested)
        self.locked = True
        self._set_buttons_state()

    def _update_score(self):
        acc = (self.correct / self.total) * 100 if self.total else 0.0
        self.score_var.set(f"Score: {self.correct}/{self.total} ({acc:.1f}%)")

    def _action_name(self, a: str) -> str:
        return {"H":"Hit", "S":"Stand", "D":"Double", "P":"Split"}.get(a, a)

def main():
    root = tk.Tk()
    app = BJTrainerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()