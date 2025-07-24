from hand_to_text import convert_hand_to_narratives


# Mock HandHistory class for testing
class MockHandHistory:
    def __init__(self):
        self.players = ["Player1", "Player2", "Player3"]
        self.starting_stacks = [10000, 10000, 10000]
        self.finishing_stacks = [10250, 9750, 10000]
        self.blinds_or_straddles = [50, 100]
        self.actions = [
            "d dh p1 AcKh",  # Player 1 gets Ace of clubs, King of hearts
            "d dh p2 QdJc",  # Player 2 gets Queen of diamonds, Jack of clubs
            "d dh p3 2h3s",  # Player 3 gets 2 of hearts, 3 of spades
            "p1 cbr 250",    # Player 1 raises to 250
            "p2 cc",         # Player 2 calls
            "p3 f",          # Player 3 folds
            "d db AcKh7s",   # Flop: Ace of clubs, King of hearts, 7 of spades
            "p1 cbr 500",    # Player 1 raises to 500
            "p2 cc",         # Player 2 calls
            "d db 9d",       # Turn: 9 of diamonds
            "p1 cbr 1000",   # Player 1 raises to 1000
            "p2 f",          # Player 2 folds
        ]

def test_hand_to_text():
    # Create mock hand history
    hand_history = MockHandHistory()
    
    # Convert to narratives
    narratives = convert_hand_to_narratives(hand_history)
    
    # Print narratives for each player
    for player_num, narrative in narratives.items():
        print(f"\n{'='*50}")
        print(f"PLAYER {player_num} PERSPECTIVE")
        print(f"{'='*50}")
        print(narrative)
        print(f"{'='*50}")

if __name__ == "__main__":
    test_hand_to_text() 