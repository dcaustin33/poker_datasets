import os

import tqdm
from pokerkit import HandHistory


def open_phh(phh_path: str) -> HandHistory:
    with open(phh_path, "rb") as file:
        hh = HandHistory.load(file)
        return hh

def check_starting_stacks(hand_history: HandHistory, file_path: str, stack_size: int = 10000):
    if hasattr(hand_history, 'starting_stacks') and hand_history.starting_stacks:
        for stack in hand_history.starting_stacks:
            if stack != stack_size:
                print(f"Non-{stack_size} starting stack in: {file_path}")
                print(f"Stack: {stack}")
                print("-" * 50)

def check_for_symbols(hand_history: HandHistory, file_path: str):
    """
    Check if 'PB' or 'SD' symbols appear in any of the hand history actions.
    If found, print the action string and file path.
    
    Args:
        hand_history: The HandHistory object
        file_path: Path to the .phh file
    """
    for action in hand_history.actions:
        if ' pb ' in action.lower() or ' sd ' in action.lower():
            print(f"Found symbol in: {file_path}")
            print(f"Action: {action}")
            print("-" * 50)


def navigate_all_pluribus(pluribus_path: str):
    """
    Recursively navigate through all subdirectories in the pluribus path
    and process all .phh files found.
    
    Args:
        pluribus_path: Root path to start navigation from
    """
    # Walk through all subdirectories
    for root, dirs, files in tqdm.tqdm(os.walk(pluribus_path)):
        # Filter for .phh files
        phh_files = [f for f in files if f.endswith('.phh')]
        
        for phh_file in phh_files:
            full_path = os.path.join(root, phh_file)
            try:
                hand_history = open_phh(full_path)
                check_for_symbols(hand_history, full_path)
                check_starting_stacks(hand_history, full_path)
            except Exception as e:
                print(f"Error processing {full_path}: {e}")


if __name__ == "__main__":
    navigate_all_pluribus("")