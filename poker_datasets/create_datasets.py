import json
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import tqdm
from hand_to_text import (
    convert_hand_to_narrative2,
    convert_hand_to_narrative_instruction_tuned,
)
from pokerbench_translator import (
    create_pokerkit_state_postflop,
    create_pokerkit_state_preflop,
)
from pokerkit import HandHistory
from utils import verify_hand, filter_sm_actions


def process_phh_file(file_info, instruction_tuned=False):
    """Process a single .phh file and return narratives or decision points for all players"""
    phh_path, root = file_info
    results = []

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
            return results

        filtered_actions = filter_sm_actions(hand_history.actions, phh_file=True)

        # Process all players for this hand
        for player_number in range(1, 7):
            if instruction_tuned:
                # Get instruction tuning data (returns tuple of lists)
                instruction_data = convert_hand_to_narrative_instruction_tuned(
                    hand_history, player_number, phh_file=True
                )
                if (
                    instruction_data and len(instruction_data[0]) > 0
                ):  # Check if we have data
                    instructions, responses, values = instruction_data
                    # Create JSON objects for each decision point
                    for i in range(len(instructions)):
                        results.append(
                            {
                                "instruction": instructions[i],
                                "response": responses[i],
                                "value": values[i],
                                "filtered_actions": filtered_actions,
                            }
                        )
            else:
                # Get pretraining narrative (returns tuple of narrative and values)
                narrative_data = convert_hand_to_narrative2(
                    hand_history, player_number, phh_file=True
                )
                if narrative_data and narrative_data[0]:  # Check if we have a narrative
                    narrative, values = narrative_data
                    results.append(
                        {
                            "text": narrative,
                            "values": values,
                            "filtered_actions": filtered_actions,
                        }
                    )

    except Exception as e:
        print(f"Error processing {phh_path}: {e}")

    return results


def create_pluribus_dataset(
    path_to_pluribus_hands: str,
    max_workers: int = 4,
    instruction_tuned: bool = False,
    test_percentage: float = 0.0,
):
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

    train_narratives = []
    test_narratives = []

    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_phh_file, file_info, instruction_tuned): file_info
            for file_info in phh_files
        }

        # Collect results with progress bar
        for future in tqdm.tqdm(
            as_completed(future_to_file),
            total=len(phh_files),
            desc="Processing .phh files",
        ):
            try:
                results = future.result()
                if random.random() < test_percentage:
                    test_narratives.extend(results)
                else:
                    train_narratives.extend(results)
            except Exception as e:
                file_info = future_to_file[future]
                print(f"Error processing {file_info[0]}: {e}")

    return train_narratives, test_narratives


def process_dataframe_row(args):
    """Process a single dataframe row and return the narrative or decision points"""
    idx, row, pokerbench_preflop, pokerbench_postflop, instruction_tuned = args

    try:
        if pokerbench_postflop:
            hand_history, player_number = create_pokerkit_state_postflop(row)
            if not verify_hand(
                hand_history.actions,
                hand_history.blinds_or_straddles[0],
                hand_history.starting_stacks,
            ):
                return None
            filtered_actions = filter_sm_actions(hand_history.actions)

            if instruction_tuned:
                instruction_data = convert_hand_to_narrative_instruction_tuned(
                    hand_history, player_number
                )
                if instruction_data and len(instruction_data[0]) > 0:
                    instructions, responses, values = instruction_data
                    results = []
                    for i in range(len(instructions)):
                        results.append(
                            {
                                "instruction": instructions[i],
                                "response": responses[i],
                                "value": values[i],
                                "filtered_actions": filtered_actions,
                            }
                        )
                    return results
                return None
            else:
                narrative_data = convert_hand_to_narrative2(hand_history, player_number)
                if narrative_data and narrative_data[0]:
                    narrative, values = narrative_data
                    return {
                        "text": narrative,
                        "values": values,
                        "filtered_actions": filtered_actions,
                    }
                return None

        elif pokerbench_preflop:
            hand_history, player_number = create_pokerkit_state_preflop(row)
            if not verify_hand(
                hand_history.actions,
                hand_history.blinds_or_straddles[0],
                hand_history.starting_stacks,
            ):
                return None
            filtered_actions = filter_sm_actions(hand_history.actions)

            if instruction_tuned:
                instruction_data = convert_hand_to_narrative_instruction_tuned(
                    hand_history, player_number
                )
                if instruction_data and len(instruction_data[0]) > 0:
                    instructions, responses, values = instruction_data
                    results = []
                    for i in range(len(instructions)):
                        results.append(
                            {
                                "instruction": instructions[i],
                                "response": responses[i],
                                "value": values[i],
                                "filtered_actions": filtered_actions,
                            }
                        )
                    return results
                return None
            else:
                narrative_data = convert_hand_to_narrative2(hand_history, player_number)
                if narrative_data and narrative_data[0]:
                    narrative, values = narrative_data
                    return {
                        "text": narrative,
                        "values": values,
                        "filtered_actions": filtered_actions,
                    }
                return None

    except Exception as e:
        print(f"Error processing row {idx}: {e}")
        return None


def convert_dataframe_to_narratives(
    df: pd.DataFrame,
    pokerbench_preflop: bool = False,
    pokerbench_postflop: bool = False,
    max_workers: int = 4,
    instruction_tuned: bool = False,
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
        (idx, df.iloc[idx], pokerbench_preflop, pokerbench_postflop, instruction_tuned)
        for idx in range(len(df))
    ]

    text_narratives = []

    # Process rows in parallel
    import pdb

    pdb.set_trace()
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
                result = future.result()
                if result:  # Only add non-None results
                    if instruction_tuned and isinstance(result, list):
                        # For instruction tuned, result is a list of decision points
                        text_narratives.extend(result)
                    elif isinstance(result, list):
                        # For pretraining from some sources, result might be a list
                        text_narratives.extend(result)
                    else:
                        # For pretraining, result is a single JSON object
                        text_narratives.append(result)
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
    instruction_tuned: bool = False,
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
            df_preflop,
            pokerbench_preflop=True,
            max_workers=max_workers,
            instruction_tuned=instruction_tuned,
        )
        all_train_narratives.extend(preflop_narratives)
        print(f"Added {len(preflop_narratives)} preflop train narratives")

    # Process pokerbench postflop data
    if path_to_pokerbench_postflop_train:
        print("Processing pokerbench postflop data...")
        df_postflop = pd.read_csv(path_to_pokerbench_postflop_train)
        postflop_narratives = convert_dataframe_to_narratives(
            df_postflop,
            pokerbench_postflop=True,
            max_workers=max_workers,
            instruction_tuned=instruction_tuned,
        )
        all_train_narratives.extend(postflop_narratives)
        print(f"Added {len(postflop_narratives)} postflop train narratives")

    # Process pokerbench preflop data

    if path_to_pokerbench_preflop_test:
        print("Processing pokerbench preflop test data...")
        df_preflop = pd.read_csv(path_to_pokerbench_preflop_test)
        preflop_narratives = convert_dataframe_to_narratives(
            df_preflop,
            pokerbench_preflop=True,
            max_workers=max_workers,
            instruction_tuned=instruction_tuned,
        )
        all_test_narratives.extend(preflop_narratives)
        print(f"Added {len(preflop_narratives)} preflop test narratives")

    if path_to_pokerbench_postflop_test:
        print("Processing pokerbench postflop test data...")
        df_postflop = pd.read_csv(path_to_pokerbench_postflop_test)
        postflop_narratives = convert_dataframe_to_narratives(
            df_postflop,
            pokerbench_postflop=True,
            max_workers=max_workers,
            instruction_tuned=instruction_tuned,
        )
        all_test_narratives.extend(postflop_narratives)
        print(f"Added {len(postflop_narratives)} postflop test narratives")

    # Process pluribus hand histories
    if path_to_pluribus_hands:
        print("Processing pluribus hand histories...")
        pluribus_train_narratives, pluribus_test_narratives = create_pluribus_dataset(
            path_to_pluribus_hands,
            max_workers=max_workers,
            instruction_tuned=instruction_tuned,
            test_percentage=1 - pluribus_percentage_train,
        )
        all_train_narratives.extend(pluribus_train_narratives)
        all_test_narratives.extend(pluribus_test_narratives)
        print(
            f"Added {len(pluribus_train_narratives)} train narratives "
            f"and {len(pluribus_test_narratives)} test narratives"
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

    print(
        f"Total narratives created: {len(all_train_narratives) + len(all_test_narratives)}"
    )
    return all_train_narratives, all_test_narratives


if __name__ == "__main__":
    # Example usage

    path_to_pokerbench_preflop_train = "/Users/derek/Desktop/poker_datasets/datasets/preflop_60k_train_set_game_scenario_information.csv"
    path_to_pokerbench_postflop_train = "/Users/derek/Desktop/poker_datasets/datasets/postflop_500k_train_set_game_scenario_information.csv"
    path_to_pokerbench_preflop_test = "/Users/derek/Desktop/poker_datasets/datasets/preflop_1k_test_set_game_scenario_information.csv"
    path_to_pokerbench_postflop_test = "/Users/derek/Desktop/poker_datasets/datasets/postflop_10k_test_set_game_scenario_information.csv"

    # these are for if we want a quick test
    # path_to_pokerbench_preflop_train = "/Users/derek/Desktop/poker_datasets/datasets/preflop_1k_test_set_game_scenario_information.csv"
    # path_to_pokerbench_postflop_train = "/Users/derek/Desktop/poker_datasets/datasets/postflop_10k_test_set_game_scenario_information.csv"

    path_to_pluribus_hands = "/Users/derek/Desktop/phh-dataset/data/pluribus"
    max_workers = os.cpu_count()
    pluribus_percentage_train = 0.8
    output_path_train = (
        "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_it_train.json"
    )
    output_path_test = (
        "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_it_test.json"
    )
    instruction_tuned = True

    example_narratives = create_combined_dataset(
        path_to_pokerbench_preflop_train=path_to_pokerbench_preflop_train,
        path_to_pokerbench_postflop_train=path_to_pokerbench_postflop_train,
        path_to_pokerbench_preflop_test=path_to_pokerbench_preflop_test,
        path_to_pokerbench_postflop_test=path_to_pokerbench_postflop_test,
        path_to_pluribus_hands=path_to_pluribus_hands,
        max_workers=max_workers,
        output_path_train=output_path_train,
        output_path_test=output_path_test,
        instruction_tuned=instruction_tuned,
        pluribus_percentage_train=pluribus_percentage_train,
    )
