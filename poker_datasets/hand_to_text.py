from typing import Dict, List, Tuple

from pokerkit import HandHistory


def parse_cards(cards_string: str) -> List[Tuple[str, str]]:
    """Parse card string like 'AcKh' into list of readable cards"""
    cards = []
    i = 0
    if cards_string == "????":
        return [("?", "?"), ("?", "?")]
    while i < len(cards_string):
        if i + 1 < len(cards_string):
            rank = cards_string[i]
            suit = cards_string[i + 1]
            cards.append((rank, suit))
            i += 2
        else:
            break
    return cards


def format_cards(card_list: List[Tuple[str, str]]) -> str:
    """Convert list of (rank, suit) tuples to readable format"""
    rank_map = {
        "A": "ace",
        "K": "king",
        "Q": "queen",
        "J": "jack",
        "T": "ten",
        "9": "nine",
        "8": "eight",
        "7": "seven",
        "6": "six",
        "5": "five",
        "4": "four",
        "3": "three",
        "2": "two",
    }

    suit_map = {"h": "hearts", "d": "diamonds", "c": "clubs", "s": "spades"}

    formatted_cards = []
    for rank, suit in card_list:
        rank_name = rank_map.get(rank, rank)
        suit_name = suit_map.get(suit, suit)
        formatted_cards.append(f"{rank_name} of {suit_name}")

    return ", ".join(formatted_cards)


def parse_deal_action(action: str) -> Tuple[int, List[Tuple[str, str]]]:
    """Parse deal action like 'd dh p1 AcKh' to extract player and cards"""
    parts = action.split()
    player_part = parts[2]  # 'p1'
    player_num = int(player_part[1:])  # extract number from 'p1'
    cards_string = parts[3]  # 'AcKh'
    cards = parse_cards(cards_string)
    return player_num, cards


def parse_community_cards(action: str) -> List[Tuple[str, str]]:
    """Parse community card action like 'd db AcKh7s' to extract cards"""
    parts = action.split()
    cards_string = parts[2]  # cards after 'd db'
    return parse_cards(cards_string)


def extract_player_number(action: str) -> int:
    """Extract player number from action like 'p3 f'"""
    parts = action.split()
    player_part = parts[0]  # 'p3'
    return int(player_part[1:])  # extract number


def convert_actions_to_text(
    actions: List[str], round_name: str = "preflop", big_blind: int = None
) -> str:
    """Convert list of actions to natural language"""
    action_texts = []

    # Track if any raises have occurred so far in this round
    raise_occurred = False

    # Track the current bet level for preflop big blind check detection
    current_bet_level = big_blind if round_name == "preflop" and big_blind else 0

    for action in actions:
        parts = action.split()
        player_num = int(parts[0][1:])  # extract from 'p3'
        action_type = parts[1]

        if action_type == "f":
            action_texts.append(f"player {player_num} fold")
        elif action_type == "cc":

            if round_name in ["flop", "turn", "river"] and not raise_occurred:
                action_texts.append(f"player {player_num} check")
            elif round_name == "preflop" and not raise_occurred and big_blind:
                action_texts.append(f"player {player_num} check")
            else:
                action_texts.append(f"player {player_num} call")

        elif action_type == "cbr":
            amount = float(parts[2])
            action_texts.append(f"player {player_num} raise to {amount}")

            if round_name == "preflop":
                if amount > current_bet_level:
                    raise_occurred = True
            else:
                raise_occurred = True
        elif action_type == "pb":
            action_texts.append(f"player {player_num} bring in")
        else:
            # Handle other action types as needed
            action_texts.append(f"player {player_num} {action_type}")

    return ", ".join(action_texts)


def convert_hand_to_narratives(hand_history: HandHistory) -> Dict[int, str]:
    """Convert HandHistory object to natural language narratives for each player"""
    # Parse initial data
    player_count = len(hand_history.players)
    starting_stacks = hand_history.starting_stacks
    finishing_stacks = getattr(hand_history, "finishing_stacks", None)
    small_blind = hand_history.blinds_or_straddles[0]
    big_blind = hand_history.blinds_or_straddles[1]

    # Extract hole cards for each player
    hole_cards = {}
    for action in hand_history.actions:
        if action.startswith("d dh"):
            player_num, cards = parse_deal_action(action)
            hole_cards[player_num] = cards

    # Group actions by betting rounds
    betting_rounds = {"preflop": [], "flop": [], "turn": [], "river": []}
    community_cards = {"flop": [], "turn": [], "river": []}

    current_round = "preflop"
    for action in hand_history.actions:
        if action.startswith("d db"):  # community cards
            cards = parse_community_cards(action)
            if len(cards) == 3:
                current_round = "flop"
                community_cards["flop"] = cards
            elif current_round == "flop":
                current_round = "turn"
                community_cards["turn"] = cards
            else:
                current_round = "river"
                community_cards["river"] = cards
        elif not action.startswith("d dh"):  # betting action (skip hole card deals)
            betting_rounds[current_round].append(action)

    # Track who's still active and when they folded
    active_players = set(range(1, player_count + 1))
    fold_rounds = {}  # player -> round they folded

    for round_name, actions in betting_rounds.items():
        for action in actions:
            if action.split()[1] == "f":  # fold action
                player = extract_player_number(action)
                if player in active_players:
                    active_players.remove(player)
                    fold_rounds[player] = round_name

    narratives = {}

    # Generate narrative for each player
    for player_num in range(1, player_count + 1):
        narrative = []
        if hole_cards[player_num] == [("?", "?"), ("?", "?")]:
            continue

        # Header
        narrative.append(
            f"There are {player_count} players at the table, I am player {player_num}."
        )
        narrative.append(
            f"The starting stacks: {', '.join(map(str, starting_stacks))}."
        )
        narrative.append(
            f"The current small blind and big blind is {small_blind} and {big_blind}."
        )
        narrative.append(f"My cards: {format_cards(hole_cards[player_num])}.")

        # If player folded, skip to end after showing actions up to fold
        if player_num in fold_rounds:
            fold_round = fold_rounds[player_num]

            # Show actions up to and including the fold
            for round_name in ["preflop", "flop", "turn", "river"]:
                if betting_rounds[round_name]:  # only show rounds that have actions
                    if round_name != "preflop" and community_cards[round_name]:
                        narrative.append(
                            f"The {round_name}: {format_cards(community_cards[round_name])}."
                        )

                    actions_text = convert_actions_to_text(
                        betting_rounds[round_name], round_name, big_blind
                    )
                    narrative.append(f"The {round_name} actions: {actions_text}.")

                    if round_name == fold_round:
                        break
        else:
            # Show all rounds for active players
            for round_name in ["preflop", "flop", "turn", "river"]:
                if betting_rounds[round_name]:  # only show rounds that have actions
                    if round_name != "preflop" and community_cards[round_name]:
                        narrative.append(
                            f"The {round_name}: {format_cards(community_cards[round_name])}."
                        )

                    actions_text = convert_actions_to_text(
                        betting_rounds[round_name], round_name, big_blind
                    )
                    narrative.append(f"The {round_name} actions: {actions_text}.")

        # Only add final cards reveal and winnings if finishing_stacks is available
        if finishing_stacks is not None:
            # Final cards reveal
            narrative.append("")
            narrative.append("Final hole cards:")
            for p_num in range(1, player_count + 1):
                if p_num == player_num:
                    continue
                player_name = hand_history.players[p_num - 1]
                cards_text = format_cards(hole_cards[p_num])
                narrative.append(f"Player {p_num} ({player_name}): {cards_text}")

            # Winnings
            winnings = (
                finishing_stacks[player_num - 1] - starting_stacks[player_num - 1]
            )
            narrative.append(f"My winnings from the hand: {winnings}")

        narratives[player_num] = "\n".join(narrative)

    return narratives
