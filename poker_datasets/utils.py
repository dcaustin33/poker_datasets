import numpy as np
from pokerkit import Automation, HandHistory, Mode, NoLimitTexasHoldem


def create_state(
    small_blind: int,
    starting_stacks: list[int],
    player_count: int,
) -> NoLimitTexasHoldem:
    """
    We assume big blind is 2x small blind and min bet is big blind

    We also assume stacks are in order of sb first, bb second, etc.
    6 players is the max for now
    """

    big_blind = 2 * small_blind
    return NoLimitTexasHoldem.create_state(
        automations=(
            Automation.ANTE_POSTING,
            Automation.BET_COLLECTION,
            Automation.BLIND_OR_STRADDLE_POSTING,
            Automation.HAND_KILLING,
            Automation.CHIPS_PUSHING,
            Automation.CHIPS_PULLING,
            Automation.CARD_BURNING,
            Automation.RUNOUT_COUNT_SELECTION,
            Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
        ),
        ante_trimming_status=False,
        raw_antes={},
        raw_blinds_or_straddles=[small_blind, big_blind],
        min_bet=big_blind,
        raw_starting_stacks=starting_stacks,
        player_count=player_count,
        mode=Mode.CASH_GAME,
    )
    
    
def create_hand_history(
    actions: list[str],
    starting_stacks: list[int],
    blinds_or_straddles: list[int],
) -> HandHistory:
    """
    Creates a hand histor for poker bench
    """
    return HandHistory(
        variant="NT",
        actions=actions,
        antes=[0] * starting_stacks.count(0),
        starting_stacks=starting_stacks,
        blinds_or_straddles=blinds_or_straddles,
        players = [f"p{i + 1}" for i in range(len(starting_stacks))],
    )


def translate_action_into_state(
    action: str, state: NoLimitTexasHoldem
) -> NoLimitTexasHoldem:
    """
    Translate an action into a state
    """
    split_action = action.split(" ")
    if split_action[0] == "d":
        # we know we are dealing hole cards or flop
        if split_action[1] == "dh":
            state.deal_hole(split_action[3])
        elif split_action[1] == "db":
            if state.all_in_status:
                while True:
                    try:
                        state.show_or_muck_hole_cards()
                    except Exception as e:
                        break
                        
                while not state.can_burn_card():
                    state.select_runout_count(None)
            # state.burn_card("??") This should be done automatically now
            state.deal_board(split_action[2])
        else:
            raise ValueError(f"Invalid action: {action}")
    elif "p" in split_action[0]:
        # this should be a single action unless cbr which should have a number after
        if split_action[1] == "fold" or split_action[1] == "f":
            state.fold()
        elif split_action[1] == "cbr":
            state.complete_bet_or_raise_to(float(split_action[2]))
        elif split_action[1] == "cc":
            state.check_or_call()
        else:
            raise ValueError(f"Invalid action: {action}")
    else:
        raise ValueError(f"Invalid action: {action}")
    return state

def filter_sm_actions(actions: list[str], phh_file: bool = False) -> list[str]:
    """
    Filter out small actions
    """
    final_actions = []
    for action in actions:
        if "sm" not in action:
            if phh_file and "cbr" in action:
                action_value = float(action.split(" ")[2]) / 100
                action = action.replace(f" {action.split(' ')[2]}", f" {action_value}")
            final_actions.append(action)
    return final_actions

def verify_hand(
    actions: list[str], small_blind: int, starting_stacks: list[int], player_count: int
) -> bool:
    """
    Verify that the actions are valid for the given state
    """
    state = create_state(
        small_blind, starting_stacks, player_count
    )
    filtered_actions = filter_sm_actions(actions)
    for action in filtered_actions:
        try:
            state = translate_action_into_state(action, state)
        except Exception as e:
            return False
    return True

def dense_near_zero(N: int, p: float = 3) -> list[float]:
    """
    Create a dense list of numbers near zero
    """
    i = np.arange(N+1)  # includes 0 to N
    return (i / N) ** p