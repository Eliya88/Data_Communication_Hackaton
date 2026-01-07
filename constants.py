# Shared constants for the UDP communication protocol to both client and server.

# Protocol Identifiers
MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122

# Message Types
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

# Game Results (Server -> Client)

RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

# Data constraints
TEAM_NAME_LEN = 32
