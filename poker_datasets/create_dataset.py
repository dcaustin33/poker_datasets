import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import tqdm
from hand_to_text import convert_hand_to_narrative2
from pokerbench_translator import (
    create_pokerkit_state_postflop,
    create_pokerkit_state_preflop,
)
from pokerkit import HandHistory
from utils import verify_hand


def process_phh_file(file_info):
    """Process a single .phh file and return narratives for all players"""
    phh_path, root = file_info
    narratives = []

    try:
        # Read the hand history
        with open(phh_path, "rb") as f:
            hand_history = HandHistory.load(f)

        # Verify the hand
        if not verify_hand(
            hand_history.actions,
            hand_history.blinds_or_straddles[0],
            hand_history.starting_stacks,
        ):
            return narratives

        # Process all players for this hand
        for player_number in range(1, 7):
            narrative = convert_hand_to_narrative2(hand_history, player_number)
            if narrative:  # Only add non-empty narratives
                narratives.append(narrative)

    except Exception as e:
        print(f"Error processing {phh_path}: {e}")

    return narratives


def create_pluribus_dataset(path_to_pluribus_hands: str, max_workers: int = 4):
    """
    Multithreaded version of create_pluribus_dataset

    Args:
        path_to_pluribus_hands: Path to directory containing .phh files
        max_workers: Number of threads to use for parallel processing
    """
    # First, collect all .phh files
    phh_files = []
    for root, dirs, files in os.walk(path_to_pluribus_hands):
        for file in files:
            if file.endswith(".phh"):
                phh_path = os.path.join(root, file)
                phh_files.append((phh_path, root))

    print(f"Found {len(phh_files)} .phh files to process")

    text_narratives = []

    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_phh_file, file_info): file_info
            for file_info in phh_files
        }

        # Collect results with progress bar
        for future in tqdm.tqdm(
            as_completed(future_to_file),
            total=len(phh_files),
            desc="Processing .phh files",
        ):
            try:
                narratives = future.result()
                text_narratives.extend(narratives)
            except Exception as e:
                file_info = future_to_file[future]
                print(f"Error processing {file_info[0]}: {e}")

    return text_narratives


def process_dataframe_row(args):
    """Process a single dataframe row and return the narrative"""
    idx, row, pokerbench_preflop, pokerbench_postflop = args

    try:
        if pokerbench_postflop:
            hand_history, player_number = create_pokerkit_state_postflop(row)
            if not verify_hand(
                hand_history.actions,
                hand_history.blinds_or_straddles[0],
                hand_history.starting_stacks,
            ):
                return None
            return convert_hand_to_narrative2(hand_history, player_number)

        elif pokerbench_preflop:
            hand_history, player_number = create_pokerkit_state_preflop(row)
            if not verify_hand(
                hand_history.actions,
                hand_history.blinds_or_straddles[0],
                hand_history.starting_stacks,
            ):
                return None
            return convert_hand_to_narrative2(hand_history, player_number)

    except Exception as e:
        print(f"Error processing row {idx}: {e}")
        return None


def convert_dataframe_to_narratives(
    df: pd.DataFrame,
    pokerbench_preflop: bool = False,
    pokerbench_postflop: bool = False,
    max_workers: int = 4,
) -> list[str]:
    """
    Multithreaded version that takes in one of the pokerbench datasets and returns
    a list of text narratives that can be used to train a model.

    Args:
        df: DataFrame to process
        pokerbench_preflop: Whether to process as preflop data
        pokerbench_postflop: Whether to process as postflop data
        max_workers: Number of threads to use for parallel processing
    """
    assert (
        pokerbench_preflop or pokerbench_postflop
    ), "Must have one of pokerbench_preflop, pokerbench_postflop"
    assert not (
        pokerbench_preflop and pokerbench_postflop
    ), "Cannot have both pokerbench_preflop and pokerbench_postflop"

    # Prepare arguments for each row
    row_args = [
        (idx, df.iloc[idx], pokerbench_preflop, pokerbench_postflop)
        for idx in range(len(df))
    ]

    text_narratives = []

    # Process rows in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(process_dataframe_row, args): args[0] for args in row_args
        }

        # Collect results with progress bar
        for future in tqdm.tqdm(
            as_completed(future_to_idx),
            total=len(row_args),
            desc="Processing dataframe rows",
        ):
            try:
                narrative = future.result()
                if narrative:  # Only add non-None narratives
                    text_narratives.append(narrative)
            except Exception as e:
                idx = future_to_idx[future]
                print(f"Error processing row {idx}: {e}")

    return text_narratives


def create_combined_dataset(
    path_to_pokerbench_preflop_train: str = None,
    path_to_pokerbench_postflop_train: str = None,
    path_to_pokerbench_preflop_test: str = None,
    path_to_pokerbench_postflop_test: str = None,
    path_to_pluribus_hands: str = None,
    pluribus_percentage_train: float = 1.0,
    max_workers: int = 4,
    output_path_train: str = None,
    output_path_test: str = None,
) -> list[str]:
    """
    Demonstration function showing how to use the multithreaded dataset creation functions.

    Args:
        path_to_pokerbench_preflop: Path to pokerbench preflop CSV file
        path_to_pokerbench_postflop: Path to pokerbench postflop CSV file
        path_to_pluribus_hands: Path to directory containing .phh files
        max_workers: Number of threads to use for parallel processing
        output_path: Optional path to save the combined narratives as JSON

    Returns:
        List of all text narratives from all datasets
    """
    all_train_narratives = []
    all_test_narratives = []

    # Process pokerbench preflop data
    if path_to_pokerbench_preflop_train:
        print("Processing pokerbench preflop data...")
        df_preflop = pd.read_csv(path_to_pokerbench_preflop_train)
        preflop_narratives = convert_dataframe_to_narratives(
            df_preflop, pokerbench_preflop=True, max_workers=max_workers
        )
        all_train_narratives.extend(preflop_narratives)
        print(f"Added {len(preflop_narratives)} preflop train narratives")

    # Process pokerbench postflop data
    if path_to_pokerbench_postflop_train:
        print("Processing pokerbench postflop data...")
        df_postflop = pd.read_csv(path_to_pokerbench_postflop_train)
        postflop_narratives = convert_dataframe_to_narratives(
            df_postflop, pokerbench_postflop=True, max_workers=max_workers
        )
        all_train_narratives.extend(postflop_narratives)
        print(f"Added {len(postflop_narratives)} postflop train narratives")

    # Process pokerbench preflop data

    if path_to_pokerbench_preflop_test:
        print("Processing pokerbench preflop test data...")
        df_preflop = pd.read_csv(path_to_pokerbench_preflop_test)
        preflop_narratives = convert_dataframe_to_narratives(
            df_preflop, pokerbench_preflop=True, max_workers=max_workers
        )
        all_test_narratives.extend(preflop_narratives)
        print(f"Added {len(preflop_narratives)} preflop test narratives")

    if path_to_pokerbench_postflop_test:
        print("Processing pokerbench postflop test data...")
        df_postflop = pd.read_csv(path_to_pokerbench_postflop_test)
        postflop_narratives = convert_dataframe_to_narratives(
            df_postflop, pokerbench_postflop=True, max_workers=max_workers
        )
        all_test_narratives.extend(postflop_narratives)
        print(f"Added {len(postflop_narratives)} postflop test narratives")

    # Process pluribus hand histories
    if path_to_pluribus_hands:
        print("Processing pluribus hand histories...")
        pluribus_narratives = create_pluribus_dataset(
            path_to_pluribus_hands, max_workers=max_workers
        )
        if pluribus_percentage_train < 1.0:
            random.shuffle(pluribus_narratives)
            train_number = int(len(pluribus_narratives) * pluribus_percentage_train)
            all_train_narratives.extend(pluribus_narratives[:train_number])
            all_test_narratives.extend(pluribus_narratives[train_number:])
            print(
                f"Added {train_number} train narratives "
                f"and {len(pluribus_narratives) - train_number} test narratives"
            )

    # Optionally save to file
    if output_path_train:
        print(f"Saving {len(all_train_narratives)} narratives to {output_path_train}")
        with open(output_path_train, "w", encoding="utf-8") as f:
            json.dump(all_train_narratives, f, indent=2, ensure_ascii=False)

    if output_path_test:
        print(f"Saving {len(all_test_narratives)} narratives to {output_path_test}")
        with open(output_path_test, "w", encoding="utf-8") as f:
            json.dump(all_test_narratives, f, indent=2, ensure_ascii=False)

    print(f"Total narratives created: {len(all_train_narratives) + len(all_test_narratives)}")
    return all_train_narratives, all_test_narratives


if __name__ == "__main__":
    # Example usage

    path_to_pokerbench_preflop_train = "/Users/derek/Desktop/poker_datasets/datasets/preflop_60k_train_set_game_scenario_information.csv"
    path_to_pokerbench_preflop_test = "/Users/derek/Desktop/poker_datasets/datasets/preflop_1k_test_set_game_scenario_information.csv"
    path_to_pokerbench_postflop_train = "/Users/derek/Desktop/poker_datasets/datasets/postflop_500k_train_set_game_scenario_information.csv"
    path_to_pokerbench_postflop_test = "/Users/derek/Desktop/poker_datasets/datasets/postflop_10k_test_set_game_scenario_information.csv"
    path_to_pluribus_hands = "/Users/derek/Desktop/phh-dataset/data/pluribus"
    max_workers = os.cpu_count()
    pluribus_percentage_train = 0.8
    output_path_train = "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_train.json"
    output_path_test = "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_test.json"

    example_narratives = create_combined_dataset(
        path_to_pokerbench_preflop_train,
        path_to_pokerbench_postflop_train,
        path_to_pokerbench_preflop_test,
        path_to_pokerbench_postflop_test,
        path_to_pluribus_hands,
        max_workers=max_workers,
        output_path_train=output_path_train,
        output_path_test=output_path_test,
    )
