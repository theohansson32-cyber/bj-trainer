import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

# =========================
# Card / Hand utilities
# =========================

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_VALUES = {
    "A": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 10, "Q": 10, "K": 10,
}

def hand_value(cards: List[str]) -> Tuple[int, bool]:
    """Return (total, is_soft). is_soft True if an Ace is counted as 11."""
    total = sum(CARD_VALUES[c] for c in cards)
    aces = cards.count("A")
    # Adjust for aces
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    # Soft if there's at least one ace still counted as 11
    is_soft = ("A" in cards) and (sum(CARD_VALUES[c] for c in cards) != total + 10 * cards.count("A"))
    # Above line is tricky; compute soft properly:
    # Soft if any ace can be 11 without bust -> total <= 21 and at least one ace and total != hard_total
    hard_total = sum(1 if c == "A" else CARD_VALUES[c] for c in cards)
    is_soft = ("A" in cards) and (total != hard_total)
    return total, is_soft

def is_blackjack(cards: List[str]) -> bool:
    return len(cards) == 2 and set(cards) == {"A", "10"} or \
           len(cards) == 2 and ("A" in cards) and (any(c in ["10", "J", "Q", "K"] for c in cards))

def can_split(cards: List[str]) -> bool:
    if len(cards) != 2:
        return False
    # treat 10/J/Q/K as same rank for split strategy?
    # Basic strategy usually considers all 10-value cards as "10".
    def split_rank(c):
        return "10" if c in ["10","J","Q","K"] else c
    return split_rank(cards[0]) == split_rank(cards[1])

def normalize_rank(c: str) -> str:
    return "10" if c in ["10","J","Q","K"] else c

def dealer_up_value(card: str) -> int:
    c = normalize_rank(card)
    if c == "A":
        return 11
    return CARD_VALUES[c]

def pretty_hand(cards: List[str]) -> str:
    return " ".join(cards)

# =========================
# Deck (optional for "normal" random mode)
# =========================

class Shoe:
    def __init__(self, decks: int = 6):
        self.decks = decks
        self.cards = []
        self._build()

    def _build(self):
        self.cards = []
        for _ in range(self.decks):
            for r in RANKS:
                # 4 suits each
                self.cards.extend([r]*4)
        random.shuffle(self.cards)

    def draw(self) -> str:
        if len(self.cards) < 52:  # reshuffle threshold
            self._build()
        return self.cards.pop()

# =========================
# Basic Strategy (S17, 6D, DAS)
# Actions: H, S, D, P (split)
# =========================

def basic_strategy_action(player_cards: List[str], dealer_up: str, can_double: bool = True, can_split_now: bool = True) -> str:
    """
    Return one of: 'H', 'S', 'D', 'P'
    Assumes: S17, 6-deck, DAS, no surrender
    """
    up = normalize_rank(dealer_up)
    upv = 11 if up == "A" else CARD_VALUES[up]

    # 1) Splits
    if can_split_now and can_split(player_cards):
        pr = normalize_rank(player_cards[0])

        # Pair strategy (common S17 DAS)
        if pr == "A":
            return "P"
        if pr == "8":
            return "P"
        if pr == "10":
            return "S"
        if pr == "9":
            return "P" if up in ["2","3","4","5","6","8","9"] else "S"
        if pr == "7":
            return "P" if up in ["2","3","4","5","6","7"] else "H"
        if pr == "6":
            return "P" if up in ["2","3","4","5","6"] else "H"
        if pr == "5":
            # treat as hard 10 -> double vs 2-9
            return "D" if up in ["2","3","4","5","6","7","8","9"] and can_double else "H"
        if pr == "4":
            return "P" if up in ["5","6"] else "H"
        if pr in ["2","3"]:
            return "P" if up in ["2","3","4","5","6","7"] else "H"

    total, soft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in player_cards])

    # 2) Soft hands
    if soft:
        # Soft totals: A2=13 ... A9=20
        if total <= 17:  # A2-A6
            # Double on A2-A3 vs 5-6; A4-A5 vs 4-6; A6 vs 3-6 (S17 DAS)
            if can_double:
                if total in [13,14] and up in ["5","6"]:
                    return "D"
                if total in [15,16] and up in ["4","5","6"]:
                    return "D"
                if total == 17 and up in ["3","4","5","6"]:
                    return "D"
            return "H"
        if total == 18:  # A7
            if can_double and up in ["3","4","5","6"]:
                return "D"
            if up in ["2","7","8"]:
                return "S"
            return "H"  # vs 9,10,A
        if total == 19:  # A8
            if can_double and up == "6":
                return "D"
            return "S"
        if total >= 20:  # A9, A10
            return "S"

    # 3) Hard hands
    if total <= 8:
        return "H"
    if total == 9:
        return "D" if (up in ["3","4","5","6"] and can_double) else "H"
    if total == 10:
        return "D" if (up in ["2","3","4","5","6","7","8","9"] and can_double) else "H"
    if total == 11:
        return "D" if can_double and up != "A" else "H"  # (many charts: double vs A too in some rules; keep simple)
    if total == 12:
        return "S" if up in ["4","5","6"] else "H"
    if 13 <= total <= 16:
        return "S" if up in ["2","3","4","5","6"] else "H"
    return "S"  # 17+

# =========================
# Training scenario generator
# =========================

@dataclass
class Weights:
    hard: int = 1
    soft: int = 1
    pair: int = 1  # split hands

def random_dealer_up() -> str:
    # Use 10 as representative for any 10-value
    up = random.choice(["2","3","4","5","6","7","8","9","10","A"])
    return up

def gen_soft_hand() -> List[str]:
    # Generate A + x where x 2..9 (avoid A,A which is pair)
    x = random.choice(["2","3","4","5","6","7","8","9"])
    return ["A", x]

def gen_pair_hand() -> List[str]:
    # Generate a pair (including 10-value pair)
    r = random.choice(["A","2","3","4","5","6","7","8","9","10"])
    return [r, r]

def gen_hard_hand() -> List[str]:
    # Generate a two-card hard total (no Ace counted as 11)
    # We'll avoid A as first approximation.
    # Create totals from 5..20 excluding those that force soft.
    # We'll sample two cards from 2..10 with replacement, rejecting very low repetition.
    while True:
        c1 = random.choice(["2","3","4","5","6","7","8","9","10"])
        c2 = random.choice(["2","3","4","5","6","7","8","9","10"])
        total = CARD_VALUES[c1] + CARD_VALUES[c2]
        if 5 <= total <= 20:
            return [c1, c2]

def pick_training_hand(weights: Weights) -> Tuple[List[str], str, str]:
    """
    Returns (player_cards, dealer_up, category)
    category in {'hard','soft','pair'}
    """
    choices = (["hard"]*weights.hard) + (["soft"]*weights.soft) + (["pair"]*weights.pair)
    cat = random.choice(choices)
    dealer_up = random_dealer_up()
    if cat == "soft":
        return gen_soft_hand(), dealer_up, "soft"
    if cat == "pair":
        return gen_pair_hand(), dealer_up, "pair"
    return gen_hard_hand(), dealer_up, "hard"

# =========================
# Gameplay loop (single hand)
# =========================

def parse_action(inp: str) -> Optional[str]:
    inp = inp.strip().upper()
    mapping = {
        "H": "H", "HIT": "H",
        "S": "S", "STAND": "S",
        "D": "D", "DOUBLE": "D",
        "P": "P", "SPLIT": "P",
        "Q": "Q", "QUIT": "Q",
        "?": "?"
    }
    return mapping.get(inp)

def allowed_actions(player_cards: List[str], has_hit: bool) -> List[str]:
    # Basic: double and split only allowed as first decision (no hit yet)
    acts = ["H", "S"]
    if not has_hit and len(player_cards) == 2:
        acts.append("D")
        if can_split(player_cards):
            acts.append("P")
    return acts

def dealer_play(shoe: Shoe, dealer_cards: List[str]) -> List[str]:
    # S17: stand on all 17 including soft 17
    while True:
        total, soft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in dealer_cards])
        if total < 17:
            dealer_cards.append(shoe.draw())
            continue
        if total == 17 and soft:
            # S17 => stand
            return dealer_cards
        return dealer_cards

def settle(player_cards: List[str], dealer_cards: List[str]) -> str:
    pt, _ = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in player_cards])
    dt, _ = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in dealer_cards])
    if pt > 21:
        return "LOSS (bust)"
    if dt > 21:
        return "WIN (dealer bust)"
    if pt > dt:
        return "WIN"
    if pt < dt:
        return "LOSS"
    return "PUSH"

def run_one_hand(weights: Weights, shoe: Shoe, force_training: bool = True) -> bool:
    """
    Plays one training hand and returns True if user matched basic strategy
    on the first decision.
    """
    if force_training:
        player_cards, dealer_up, category = pick_training_hand(weights)
        dealer_cards = [dealer_up, shoe.draw()]  # hole card random
    else:
        # fully random from shoe
        player_cards = [shoe.draw(), shoe.draw()]
        dealer_cards = [shoe.draw(), shoe.draw()]
        dealer_up = dealer_cards[0]
        category = "random"

    # If blackjack, just show and skip quiz (or still quiz: usually stand)
    if is_blackjack(player_cards):
        print(f"\nDin hand: {pretty_hand(player_cards)} (BLACKJACK)")
        print(f"Dealer: {dealer_up} ?")
        print("Blackjack – ingen strategy-quiz här. (Tryck Enter)")
        input()
        return True

    print("\n==============================")
    print(f"Kategori: {category}")
    print(f"Din hand: {pretty_hand(player_cards)}")
    print(f"Dealer visar: {dealer_up}")
    print("Actions: H=Hit, S=Stand, D=Double, P=Split, Q=Quit, ?=visa basic")
    print("==============================")

    has_hit = False
    first_decision = True
    matched_basic = True

    while True:
        acts = allowed_actions(player_cards, has_hit)
        action = None
        while action is None:
            raw = input(f"Välj ({'/'.join(acts)}): ")
            pa = parse_action(raw)
            if pa == "Q":
                raise SystemExit
            if pa == "?":
                suggested = basic_strategy_action(player_cards, dealer_up,
                                                  can_double=("D" in acts),
                                                  can_split_now=("P" in acts))
                print(f"Basic strategy säger: {suggested}")
                continue
            if pa in acts:
                action = pa
            else:
                print("Ogiltigt val.")

        if first_decision:
            suggested = basic_strategy_action(player_cards, dealer_up,
                                              can_double=("D" in acts),
                                              can_split_now=("P" in acts))
            matched_basic = (action == suggested)
            if matched_basic:
                print("✅ Rätt enligt basic strategy.")
            else:
                print(f"❌ Fel. Basic strategy: {suggested} (du valde {action})")
            first_decision = False

        if action == "S":
            break

        if action == "H":
            player_cards.append(shoe.draw())
            has_hit = True
            total, soft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in player_cards])
            print(f"Du drar: {player_cards[-1]}  -> {pretty_hand(player_cards)} (total {total}{' soft' if soft else ''})")
            if total > 21:
                print("Du bustar!")
                break
            continue

        if action == "D":
            # one card then stand
            player_cards.append(shoe.draw())
            total, soft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in player_cards])
            print(f"Double: du drar {player_cards[-1]} -> {pretty_hand(player_cards)} (total {total}{' soft' if soft else ''})")
            break

        if action == "P":
            # For training: we let you practice decision; full split tree is more complex.
            # We'll resolve by playing only ONE of the split hands to keep it simple.
            print("Split valt. (Träningsläge: vi spelar bara vänsterhanden fullt ut.)")
            left = [player_cards[0], shoe.draw()]
            # Right hand ignored for simplicity; focus on decision making.
            player_cards = left
            has_hit = False
            print(f"Ny hand: {pretty_hand(player_cards)} vs dealer {dealer_up}")
            continue

    # Dealer plays if player not bust
    print(f"\nDealer hand: {pretty_hand(dealer_cards)}")
    dealer_cards = dealer_play(shoe, dealer_cards)
    dt, dsoft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in dealer_cards])
    print(f"Dealer spelar klart: {pretty_hand(dealer_cards)} (total {dt}{' soft' if dsoft else ''})")

    result = settle(player_cards, dealer_cards)
    pt, psoft = hand_value([normalize_rank(c) if c in ["J","Q","K"] else c for c in player_cards])
    print(f"Din total: {pt}{' soft' if psoft else ''} -> Resultat: {result}")

    return matched_basic

# =========================
# Main trainer
# =========================

def main():
    print("Blackjack Basic Strategy Trainer (S17, 6D, DAS, no surrender)")
    print("Du spelar en hand i taget och får feedback på första beslutet.\n")

    shoe = Shoe(decks=6)

    # Default: equal weights
    weights = Weights(hard=2, soft=2, pair=2)

    # Quick weight setup
    print("Sätt hur ofta du vill se olika handtyper (högre = oftare).")
    try:
        weights.hard = int(input("Vikt hard hands (t.ex. 2): ") or "2")
        weights.soft = int(input("Vikt soft hands (t.ex. 2): ") or "2")
        weights.pair = int(input("Vikt splits/pairs (t.ex. 2): ") or "2")
    except ValueError:
        print("Fel format, kör med standardvikter 2/2/2.")
        weights = Weights(hard=2, soft=2, pair=2)

    # Mode
    mode = input("Vill du forcera träningshänder? (J/n): ").strip().lower()
    force_training = (mode != "n")

    correct = 0
    total = 0

    print("\nStart! (Skriv Q när som helst för att avsluta.)")
    while True:
        try:
            ok = run_one_hand(weights, shoe, force_training=force_training)
            total += 1
            if ok:
                correct += 1
            acc = (correct / total) * 100
            print(f"\nScore: {correct}/{total} = {acc:.1f}% rätt på första beslutet")
        except SystemExit:
            print("\nAvslutar.")
            break

if __name__ == "__main__":
    main()