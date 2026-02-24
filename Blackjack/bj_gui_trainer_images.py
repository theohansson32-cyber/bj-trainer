import os
import random
import tkinter as tk
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Pillow for image loading/scaling
from PIL import Image, ImageTk

# =========================
# Card / Hand utilities
# =========================

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["S", "H", "D", "C"]  # Spades, Hearts, Diamonds, Clubs

CARD_VALUES = {
    "A": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10,
}

def normalize_rank(c: str) -> str:
    return "10" if c in ["10", "J", "Q", "K"] else c

def hand_value(cards: List[str]) -> Tuple[int, bool]:
    """cards are like 'AS', '10H', 'QD' etc. Returns (total, is_soft)."""
    ranks = []
    for card in cards:
        r = card[:-1]  # everything except last char is rank
        ranks.append(r)

    total = 0
    for r in ranks:
        total += 11 if r == "A" else CARD_VALUES[r]
    aces = ranks.count("A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    hard_total = sum(1 if r == "A" else CARD_VALUES[r] for r in ranks)
    is_soft = ("A" in ranks) and (total != hard_total)
    return total, is_soft

def can_split(cards: List[str]) -> bool:
    if len(cards) != 2:
        return False
    r1 = cards[0][:-1]
    r2 = cards[1][:-1]
    # consider 10/J/Q/K as same rank for splits (basic strategy usually treats 10-values together)
    def split_rank(r):
        return "10" if r in ["10", "J", "Q", "K"] else r
    return split_rank(r1) == split_rank(r2)

# =========================
# Basic Strategy (S17, 6D, DAS, no surrender)
# Actions: H, S, D, P
# =========================

def basic_strategy_action(player_cards: List[str], dealer_up: str, can_double: bool, can_split_now: bool) -> str:
    up_rank = dealer_up[:-1]
    up = "10" if up_rank in ["10","J","Q","K"] else up_rank

    # Splits
    if can_split_now and can_split(player_cards):
        pr = player_cards[0][:-1]
        pr = "10" if pr in ["10","J","Q","K"] else pr
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
        return "S"

    # Hard totals
    if total <= 8: return "H"
    if total == 9:  return "D" if can_double and up in ["3","4","5","6"] else "H"
    if total == 10: return "D" if can_double and up in ["2","3","4","5","6","7","8","9"] else "H"
    if total == 11: return "D" if can_double and up != "A" else "H"
    if total == 12: return "S" if up in ["4","5","6"] else "H"
    if 13 <= total <= 16: return "S" if up in ["2","3","4","5","6"] else "H"
    return "S"

# =========================
# Training scenario generator (weighted)
# =========================

@dataclass
class Weights:
    hard: int = 2
    soft: int = 2
    pair: int = 2

def random_card(rank: Optional[str] = None) -> str:
    r = rank if rank else random.choice(RANKS)
    s = random.choice(SUITS)
    return f"{r}{s}"

def random_dealer_up() -> str:
    # use realistic random upcard with suit
    r = random.choice(["2","3","4","5","6","7","8","9","10","A","J","Q","K"])
    return random_card(r)

def gen_soft_hand() -> List[str]:
    # A + 2..9 (avoid AA)
    return [random_card("A"), random_card(random.choice(["2","3","4","5","6","7","8","9"]))]

def gen_pair_hand() -> List[str]:
    r = random.choice(["A","2","3","4","5","6","7","8","9","10","J","Q","K"])
    return [random_card(r), random_card(r)]

def gen_hard_hand() -> List[str]:
    # two cards without A to avoid soft
    while True:
        c1 = random_card(random.choice(["2","3","4","5","6","7","8","9","10","J","Q","K"]))
        c2 = random_card(random.choice(["2","3","4","5","6","7","8","9","10","J","Q","K"]))
        # compute rank values
        r1 = "10" if c1[:-1] in ["10","J","Q","K"] else c1[:-1]
        r2 = "10" if c2[:-1] in ["10","J","Q","K"] else c2[:-1]
        total = CARD_VALUES[r1] + CARD_VALUES[r2]
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
# Image loading
# =========================

class CardImageLoader:
    def __init__(self, folder: str = "cards", card_w: int = 90, card_h: int = 130):
        self.folder = folder
        self.card_w = card_w
        self.card_h = card_h
        self.cache: dict[str, ImageTk.PhotoImage] = {}

    def get(self, card_code: str) -> Optional[ImageTk.PhotoImage]:
        """
        card_code like 'AS', '10H', 'QD'
        expects file like 'AS.png' in folder
        """
        if card_code in self.cache:
            return self.cache[card_code]

        path_png = os.path.join(self.folder, f"{card_code}.png")
        if not os.path.exists(path_png):
            return None

        img = Image.open(path_png).convert("RGBA")
        img = img.resize((self.card_w, self.card_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        self.cache[card_code] = tk_img
        return tk_img

# =========================
# GUI App
# =========================

class BJTrainerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Blackjack Basic Strategy Trainer (Images)")
        self.root.configure(padx=16, pady=16)

        self.loader = CardImageLoader(folder="cards", card_w=90, card_h=130)

        self.weights = Weights(2, 2, 2)
        self.player_cards: List[str] = []
        self.dealer_up: str = ""
        self.category: str = ""
        self.has_hit: bool = False
        self.locked: bool = False

        self.correct = 0
        self.total = 0

        self._build_ui()
        self.new_hand()

    def _build_ui(self):
        tk.Label(self.root, text="Blackjack Trainer", font=("Helvetica", 18, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")

        self.score_var = tk.StringVar(value="Score: 0/0 (0.0%)")
        tk.Label(self.root, textvariable=self.score_var, font=("Helvetica", 11)).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 12))

        tk.Label(self.root, text="Dealer (upcard):", font=("Helvetica", 12, "bold")).grid(row=2, column=0, sticky="w")
        self.dealer_frame = tk.Frame(self.root)
        self.dealer_frame.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 14))

        tk.Label(self.root, text="Du:", font=("Helvetica", 12, "bold")).grid(row=4, column=0, sticky="w")
        self.player_frame = tk.Frame(self.root)
        self.player_frame.grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 6))

        self.info_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.info_var, font=("Helvetica", 11)).grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 10))

        self.feedback_var = tk.StringVar(value="Välj ett beslut.")
        self.feedback_lbl = tk.Label(self.root, textvariable=self.feedback_var, font=("Helvetica", 12))
        self.feedback_lbl.grid(row=7, column=0, columnspan=4, sticky="w", pady=(0, 12))

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

        tk.Label(self.root, text="Träningsvikter (högre = oftare):", font=("Helvetica", 12, "bold")).grid(row=10, column=0, columnspan=4, sticky="w", pady=(18, 6))

        self.hard_var = tk.IntVar(value=self.weights.hard)
        self.soft_var = tk.IntVar(value=self.weights.soft)
        self.pair_var = tk.IntVar(value=self.weights.pair)

        self._spin("Hard", self.hard_var, 11, 0)
        self._spin("Soft", self.soft_var, 11, 1)
        self._spin("Pairs", self.pair_var, 11, 2)

        tk.Button(self.root, text="Apply", command=self.apply_weights).grid(row=11, column=3, sticky="w")

        # Small hint
        tk.Label(self.root, text="Tips: Lägg kortbilder som 'AS.png', '10H.png' osv i mappen ./cards", font=("Helvetica", 9)).grid(
            row=12, column=0, columnspan=4, sticky="w", pady=(14, 0)
        )

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

        # Dealer
        self._card_widget(self.dealer_frame, self.dealer_up).pack(side="left", padx=6)

        # Player
        for c in self.player_cards:
            self._card_widget(self.player_frame, c).pack(side="left", padx=6)

        total, soft = hand_value(self.player_cards)
        split_txt = "Kan splitta" if can_split(self.player_cards) else ""
        self.info_var.set(f"Kategori: {self.category} | Total: {total}{' (soft)' if soft else ''} | {split_txt}")

    def _card_widget(self, parent: tk.Widget, card_code: str) -> tk.Frame:
        """
        Show image if exists, else fallback to a simple text card.
        """
        f = tk.Frame(parent, width=95, height=140, bg="darkgreen")
        f.pack_propagate(False)

        img = self.loader.get(card_code)
        if img is not None:
            lbl = tk.Label(f, image=img, bg="darkgreen")
            lbl.image = img  # keep reference
            lbl.pack(expand=True)
        else:
            # fallback
            inner = tk.Frame(f, bg="white", highlightbackground="#222", highlightthickness=2)
            inner.pack(expand=True, fill="both", padx=6, pady=6)
            tk.Label(inner, text=card_code, bg="white", fg="black", font=("Helvetica", 16, "bold")).pack(expand=True)

        return f

    def _set_buttons_state(self):
        can_double_now = (not self.has_hit and len(self.player_cards) == 2)
        can_split_now = (not self.has_hit and len(self.player_cards) == 2 and can_split(self.player_cards))

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
        self.locked = True
        self._set_buttons_state()

    def _update_score(self):
        acc = (self.correct / self.total) * 100 if self.total else 0.0
        self.score_var.set(f"Score: {self.correct}/{self.total} ({acc:.1f}%)")

    def _action_name(self, a: str) -> str:
        return {"H":"Hit", "S":"Stand", "D":"Double", "P":"Split"}.get(a, a)

def main():
    root = tk.Tk()
    BJTrainerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()