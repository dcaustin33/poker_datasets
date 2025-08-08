import pandas as pd
from pokerkit import HandHistory
from pydantic import BaseModel

position_to_number = {"SB": 0, "BB": 1, "UTG": 2, "HJ": 3, "CO": 4, "BTN": 5}
number_to_position = {v: k for k, v in position_to_number.items()}
poker_bench_action = {
    "call": "cc",
}


class PokerBenchState(BaseModel):
    acting_actor: int
    other_actor: int

    def in_position(self) -> bool:
        return self.acting_actor > self.other_actor

    def get_in_position_player(self) -> str:
        if self.in_position():
            return self.acting_actor
        else:
            return self.other_actor

    def get_not_in_position_player(self) -> str:
        if self.in_position():
            return self.other_actor
        else:
            return self.acting_actor


def get_last_person_to_act_preflop(preflop_action: str) -> int:
    """
    Based on the preflop action this should return
    the position of the last person to act
    """
    # indicates nobody has acted yet so it is like the BB has acted
    if pd.isna(preflop_action):
        return 1

    try:
        last_actor = preflop_action.split("/")[-2]
        return position_to_number[last_actor]
    except IndexError:
        raise ValueError("No last actor found")


def get_other_actor(preflop_action: str) -> int:
    """
    Based on the preflop action this should return
    the position of the other actor
    """
    last_actor = get_last_person_to_act_preflop(preflop_action)
    # have to navigate backwards to see who is still in the game
    for i in range(len(preflop_action.split("/")) - 1, -1, -1):
        if (
            preflop_action.split("/")[i] in position_to_number
            and position_to_number[preflop_action.split("/")[i]] != last_actor
        ):
            return position_to_number[preflop_action.split("/")[i]]
    raise ValueError("No other actor found")


def get_all_preflop_actors(preflop_action: str, my_pos: str) -> PokerBenchState:
    """
    Based on the preflop action this should return
    all the actors in the preflop action
    """
    last_person_to_act = get_last_person_to_act_preflop(preflop_action)
    other_actor = get_other_actor(preflop_action)
    if my_pos == "OOP":
        return PokerBenchState(
            acting_actor=min(other_actor, last_person_to_act) + 1,
            other_actor=max(other_actor, last_person_to_act) + 1,
        )
    return PokerBenchState(
        acting_actor=max(other_actor, last_person_to_act) + 1,
        other_actor=min(other_actor, last_person_to_act) + 1,
    )


def deal_hole_cards_without_state(hero_pos: str, cards: str) -> list[str]:
    """
    Deals cards to everyone wtih ??? except the hero
    """
    actions = []
    for i in range(6):
        if i != position_to_number[hero_pos]:
            actions.append(f"d dh p{i+1} ????")
        else:
            actions.append(f"d dh p{i+1} {cards}")
    return actions


def chunk_by_two(input_str):
    parts = input_str.split("/")
    return ["/".join(parts[i : i + 2]) for i in range(0, len(parts), 2)]


def parse_individual_action(preflop_action: str) -> str:
    """
    Based on the preflop action this should return
    the action for the preflop
    """
    if "call" in preflop_action:
        return "cc"
    elif "bb" in preflop_action:
        return f"cbr {float(preflop_action.split('bb')[0])}"
    elif "allin" in preflop_action:
        return f"cbr 100"
    elif "CHECK" in preflop_action or "CALL" in preflop_action:
        return "cc"
    elif "BET" in preflop_action:
        return f"cbr {float(preflop_action.split('_')[-1])}"
    elif "RAISE" in preflop_action:
        return f"cbr {float(preflop_action.split('_')[-1])}"
    elif "fold" in preflop_action:
        return "f"
    else:
        raise ValueError(f"Unknown action: {preflop_action}")


def preflop_actions(current_actions: list[str], preflop_action: str) -> list[str]:
    """
    Based on the current actions and the preflop action this should return
    the actions for the preflop in the phh format

    So we start with player 3
    """
    chunked_preflop_action = chunk_by_two(preflop_action)
    players_folded = []
    players_active = []

    for i in range(len(chunked_preflop_action)):
        person = chunked_preflop_action[i].split("/")[0]
        action = chunked_preflop_action[i].split("/")[1]
        for player_num in range(2, 8):
            player_num = player_num % 6

            if number_to_position[player_num] == person:
                current_actions.append(
                    f"p{player_num + 1} {parse_individual_action(action)}"
                )
                players_active.append(player_num)
                break
            else:
                if (
                    player_num not in players_folded
                    and player_num not in players_active
                ):
                    current_actions.append(f"p{player_num + 1} f")
                    players_folded.append(player_num)
    return current_actions


def deal_board_cards(current_actions: list[str], board_cards: str) -> list[str]:
    """
    Based on the current actions this should return
    the actions for the flop
    """
    current_actions.append(f"d db {board_cards}")
    return current_actions


def parse_postflop_actions(
    current_actions: list[str],
    postflop_action: str,
    player_in_position: int,
    player_not_in_position: int,
) -> list[str]:
    """
    Based on the current actions and the postflop action this should return
    the actions for the postflop in the phh format
    """
    chunked_actions = postflop_action.split("/")
    for action in chunked_actions:
        person = action.split("_")[0]
        action = "_".join(action.split("_")[1:])
        if person == "OOP":
            current_actions.append(
                f"p{player_not_in_position} {parse_individual_action(action)}"
            )
        elif person == "IP":
            current_actions.append(
                f"p{player_in_position} {parse_individual_action(action)}"
            )
        else:
            raise ValueError(f"Unknown person: {person}")

    return current_actions


def add_correct_decision(
    current_actions: list[str], correct_decision: str, player_number: int
) -> list[str]:
    """
    Based on the current actions and the correct decision this should return
    the actions for the correct decision
    """
    if "call" in correct_decision.lower():
        current_actions.append(f"p{player_number} cc")
    elif "fold" in correct_decision.lower():
        current_actions.append(f"p{player_number} f")
    elif "check" in correct_decision.lower():
        current_actions.append(f"p{player_number} cc")
    elif "bet" in correct_decision.lower():
        current_actions.append(
            f"p{player_number} cbr {float(correct_decision.split(' ')[1])}"
        )
    elif "raise" in correct_decision.lower():
        current_actions.append(
            f"p{player_number} cbr {float(correct_decision.split(' ')[1])}"
        )
    elif "bb" in correct_decision.lower():
        current_actions.append(f"p{player_number} cbr {float(correct_decision[:-2])}")
    else:
        raise ValueError(f"Unknown correct decision: {correct_decision}")
    return current_actions


def create_hand_history(actions: list[str]) -> HandHistory:
    """
    Creates a hand histor for poker bench
    """
    return HandHistory(
        variant="NT",
        actions=actions,
        antes=[0, 0, 0, 0, 0, 0],
        starting_stacks=[100, 100, 100, 100, 100, 100],
        blinds_or_straddles=[0.5, 1],
        players=["SB", "BB", "UTG", "HJ", "CO", "BTN"],
    )
    



def parse_preflop_actions_multiple_actors(
    current_actions: list[str], preflop_action: str, hero_pos: str, num_players: int=6, preflop_only: bool=False
) -> list[str]:
    """
    Based on the current actions and the preflop action this should return
    the actions for the preflop in the phh format

    Ok so basically we should keep a list of actors who have folded - if we get to the next action
    and the person we think should be going is not there then they have folded,
    otherwise we append the action like normal.

    Preflop only indicates that betting is going on in preflop and we should not
    fold the rest of the players. Otherwise any that do not appear we will fold.
    """
    if pd.isna(preflop_action):
        chunked_preflop_action = []
    else:
        chunked_preflop_action = chunk_by_two(preflop_action)
    players_folded = []
    players_active = []

    expected_order = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]

    for i in range(len(chunked_preflop_action)):
        person = chunked_preflop_action[i].split("/")[0]
        action = chunked_preflop_action[i].split("/")[1]

        player_num = position_to_number[person]

        for expected_pos in expected_order:
            expected_player_num = position_to_number[expected_pos]

            if (
                expected_player_num in players_active
                or expected_player_num in players_folded
            ):
                continue

            if expected_pos == person:
                break

            # this is assuming there is no fold readout which I think is accurate
            if expected_player_num not in players_folded:
                current_actions.append(f"p{expected_player_num + 1} f")
                players_folded.append(expected_player_num)

        current_actions.append(f"p{player_num + 1} {parse_individual_action(action)}")
        players_active.append(player_num)

    # Add fold actions for any remaining players who haven't acted but come before hero
    # (only add folds before hero position for training data correctness)
    # Only add folds if players were supposed to act before hero based on the action sequence
    hero_player_num = position_to_number[hero_pos]

    # Check if the hero has actually acted yet in the sequence
    hero_has_acted = hero_player_num in players_active

    # Only add folds for players who should have acted before the hero if hero hasn't acted yet
    # If hero has acted, don't add any additional folds as the sequence is complete
    if not hero_has_acted:
        for expected_pos in expected_order:
            # Stop when we reach the hero position
            if expected_pos == hero_pos:
                break

            expected_player_num = position_to_number[expected_pos]
            if (
                expected_player_num not in players_active
                and expected_player_num not in players_folded
            ):
                current_actions.append(f"p{expected_player_num + 1} f")
                players_folded.append(expected_player_num)

    if not preflop_only:
        last_person_to_act = get_last_person_to_act_preflop(preflop_action)
        for i in range(num_players):
            # adds 1 as that person has acted
            i = (i + last_person_to_act + 1) % 6
            if i not in players_active and i not in players_folded:
                current_actions.append(f"p{i + 1} f")
                players_folded.append(i)

    return current_actions


def create_pokerkit_state_postflop(row: pd.Series) -> tuple[HandHistory, int]:
    """
    Based on the row this should return a pokerkit state

    It will deal ??? to everyone except the hero
    Starting stacks are 100
    big blinds are 1
    small blinds are 0.5.
    We will not have the end winnings as that is to tough to tell.
    We will append the correct decision to the state.
    """
    poker_bench_state = get_all_preflop_actors(
        row["preflop_action"], row["hero_position"]
    )
    actions = deal_hole_cards_without_state(
        number_to_position[poker_bench_state.acting_actor-1], row["holding"]
    )
    actions = parse_preflop_actions_multiple_actors(
        actions,
        row["preflop_action"],
        number_to_position[poker_bench_state.acting_actor-1],
    )
    actions = deal_board_cards(actions, row["board_flop"])

    flop_action_row = row["postflop_action"].split("dealcards")[0].rstrip("/")

    actions = parse_postflop_actions(
        actions,
        flop_action_row,
        poker_bench_state.get_in_position_player(),
        poker_bench_state.get_not_in_position_player(),
    )

    if len(row["postflop_action"].split("dealcards")) < 2:
        actions = add_correct_decision(
            actions, row["correct_decision"], poker_bench_state.acting_actor
        )
        return create_hand_history(actions), poker_bench_state.acting_actor

    turn_action_row = (
        row["postflop_action"].split("dealcards")[1].rstrip("/").lstrip("/")[3:]
    )
    actions = deal_board_cards(actions, row["board_turn"])
    actions = parse_postflop_actions(
        actions,
        turn_action_row,
        poker_bench_state.get_in_position_player(),
        poker_bench_state.get_not_in_position_player(),
    )

    if len(row["postflop_action"].split("dealcards")) < 3:
        actions = add_correct_decision(
            actions, row["correct_decision"], poker_bench_state.acting_actor
        )
        return create_hand_history(actions), poker_bench_state.acting_actor

    river_action_row = (
        row["postflop_action"].split("dealcards")[2].rstrip("/").lstrip("/")[3:]
    )
    actions = deal_board_cards(actions, row["board_river"])
    actions = parse_postflop_actions(
        actions,
        river_action_row,
        poker_bench_state.get_in_position_player(),
        poker_bench_state.get_not_in_position_player(),
    )
    actions = add_correct_decision(
        actions, row["correct_decision"], poker_bench_state.acting_actor
    )

    return create_hand_history(actions), poker_bench_state.acting_actor


def create_pokerkit_state_preflop(row: pd.Series) -> tuple[HandHistory, int]:
    """
    Based on the row this should return a pokerkit state

    It will deal ??? to everyone except the hero
    Starting stacks are 100
    big blinds are 1
    small blinds are 0.5.
    We will not have the end winnings as that is to tough to tell.
    We will append the correct decision to the state.
    """
    actions = deal_hole_cards_without_state(row["hero_pos"], row["hero_holding"])
    actions = parse_preflop_actions_multiple_actors(
        actions, row["prev_line"], row["hero_pos"], preflop_only=True
    )
    actions = add_correct_decision(
        actions, row["correct_decision"], position_to_number[row["hero_pos"]] + 1
    )
    return create_hand_history(actions), position_to_number[row["hero_pos"]] + 1
