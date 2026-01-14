# Shared constants for the UDP communication protocol to both client and server.

# Protocol Identifiers
MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122

# Message Types
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

# Result codes
ROUND_NOT_OVER = 0x0
TIE = 0x1
LOSS = 0x2
WIN = 0x3

class Colors:
    """
    ANSI color codes for terminal output.
    """
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

def get_suit_char(suit_int):
    """
    Returns the suit name with appropriate color coding.
    :param suit_int: Integer representing the suit (0-3)
    :return: Colored suit name string
    """
    suits = ["Heart", "Diamond", "Clubs", "Spades"]
    name = suits[suit_int]

    # Color coding: Red for Hearts and Diamonds, Blue for Clubs and Spades
    if suit_int == 0 or suit_int == 1:  # Heart, Diamond
        return f"{Colors.RED}{name}{Colors.RESET}"
    else:  # Clubs, Spades
        return f"{Colors.BLUE}{name}{Colors.RESET}"
