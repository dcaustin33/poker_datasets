from typing import Dict, List, Tuple

from pokerkit import HandHistory
from utils import create_state, translate_action_into_state, filter_sm_actions


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
    for part in parts:
        if part.startswith("p"):
            return int(part[1:])
    raise ValueError(f"Player number not found in action: {action}")


def get_current_situation(state, player_number: int) -> str:
    """"""
    return (
        f"Pot size: {state.total_pot_amount}, needed bet: {state.checking_or_calling_amount}, "
        f"minimum raise: {state.min_completion_betting_or_raising_to_amount}, my stack: {state.stacks[player_number - 1]}"
    )


def convert_hand_to_narrative2(
    hand_history: HandHistory, player_number: int, special_action_word: str = "ACTION"
) -> str:
    """"""
    state = create_state(
        hand_history.blinds_or_straddles[0],
        hand_history.starting_stacks,
        len(hand_history.players),
    )
    filtered_actions = filter_sm_actions(hand_history.actions)
    my_cards = []
    for action in filtered_actions:
        if action.startswith("d dh") and extract_player_number(action) == player_number:
            my_cards = parse_cards(action.split()[-1])
            break

    if my_cards == [("?", "?"), ("?", "?")]:
        return ""

    narrative = []
    narrative.append(
        f"There are {len(hand_history.players)} players at the table, I am player {player_number}."
    )
    narrative.append(
        f"The starting stacks: {', '.join(map(str, hand_history.starting_stacks))}."
    )
    narrative.append(
        f"The current small blind and big blind is {hand_history.blinds_or_straddles[0]} and {hand_history.blinds_or_straddles[1]}."
    )
    narrative.append(
        f"My cards: {format_cards(my_cards)}. And the following is the action sequence:"
    )

    for action in filtered_actions:
        if action.startswith("d dh"):
            state = translate_action_into_state(action, state)
            continue
        if action.startswith(f"p{player_number}"):
            narrative.append(get_current_situation(state, player_number))
            narrative.append(
                f"My action: {special_action_word} {action.replace(f'p{player_number} ', '')}"
            )
        else:
            narrative.append(action)
        state = translate_action_into_state(action, state)

    return "\n".join(narrative)
