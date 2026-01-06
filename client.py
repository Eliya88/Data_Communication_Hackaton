import socket
import struct
from constants import MAGIC_COOKIE, PAYLOAD_TYPE, UDP_PORT


def pack_client_decision(decision):
    """
    Client -> Server (10 bytes): Cookie(4), Type(1), Decision(5)
    """
    # Decision must be 5 bytes: "Hittt" or "Stand"
    return struct.pack("!IB5s", MAGIC_COOKIE, PAYLOAD_TYPE, decision)


def unpack_server_payload(data):
    """
    Server -> Client (9 bytes): Cookie(4), Type(1), Result(1), Rank(2), Suit(1)
    """
    if len(data) < 9: return None
    cookie, mtype, result, rank, suit = struct.unpack("!IBBHB", data)
    return result, rank, suit


def get_suit_char(suit_int):
    return ["H", "D", "C", "S"][suit_int]


def get_rank_str(rank_int):
    if rank_int == 1: return "Ace"
    if rank_int == 11: return "Jack"
    if rank_int == 12: return "Queen"
    if rank_int == 13: return "King"
    return str(rank_int)

def calculate_hand(ranks):
    """
    Calculate the total value of a hand based on card ranks.
    :param ranks: list of card ranks (integers)
    :return: total value of the hand (integer)
    """
    total = 0
    for r in ranks:
        if r == 1:
            total += 11  # Ace
        elif r >= 11:
            total += 10  # J, Q, K
        else:
            total += r  # 2-10
    return total


def client_main(name="Team_Agado"):
    team_name = name

    # Enable reuse port for testing multiple clients on same machine
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        # Some OS (like Windows) don't support SO_REUSEPORT, use SO_REUSEADDR
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    udp_sock.bind(("", UDP_PORT))

    print("Client started, listening for offer requests...")

    while True:
        # 1. Wait for Offer
        data, addr = udp_sock.recvfrom(1024)
        # Offer: Cookie(4), Type(1), Port(2), Name(32) = 39 bytes
        if len(data) < 39: continue

        cookie, mtype, server_port, server_name = struct.unpack("!IBH32s", data[:39])
        if cookie != MAGIC_COOKIE or mtype != 0x2:
            continue

        print(f"Received offer from {addr[0]}, attempting to connect...")

        # 2. Connect TCP
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((addr[0], server_port))

            # 3. Send Request
            # Ask user for rounds
            try:
                rounds = int(input("How many rounds you want to play? "))
            except:
                rounds = 1

            # Request: Cookie(4), Type(1), Rounds(1), Name(32)
            name_bytes = team_name.encode('utf-8') + b'\x00' * (32 - len(team_name))
            req_pkt = struct.pack("!IBB32s", MAGIC_COOKIE, 0x3, rounds, name_bytes)
            tcp_sock.sendall(req_pkt)

            game_history = []
            # --- Game Loop ---
            for r in range(rounds):
                print(f"\n--- Round {r + 1} ---")

                player_ranks = []
                dealer_ranks = []

                # Receive initial cards (Player 1, Player 2, Dealer 1)
                # We expect 3 packets of 9 bytes each
                for i in range(2):
                    data = tcp_sock.recv(9)
                    res, rank, suit = unpack_server_payload(data)
                    print(f"Your card: {get_rank_str(rank)} of {get_suit_char(suit)}")
                    if i < 2:
                        player_ranks.append(rank)
                    if i == 2:
                        dealer_ranks.append(rank)

                print(f"Your hand total: {calculate_hand(player_ranks)}")

                data = tcp_sock.recv(9)
                res, rank, suit = unpack_server_payload(data)
                print(f"Dealer card: {get_rank_str(rank)} of {get_suit_char(suit)}")

                # Player turn
                game_over = False
                while not game_over:
                    # Check if server already sent "Loss" (e.g. from previous hit busting)
                    if res != 0:
                        game_over = True
                        break

                    choice = input("Type 'h' to Hit, 's' to Stand: ").lower()
                    if choice == 'h':
                        decision = b"Hittt"
                        tcp_sock.sendall(pack_client_decision(decision))

                        # Get response (Card or Result)
                        data = tcp_sock.recv(9)
                        res, rank, suit = unpack_server_payload(data)

                        if rank != 0:
                            print(f"You drew: {get_rank_str(rank)} of {get_suit_char(suit)}")

                    elif choice == 's':
                        decision = b"Stand"
                        tcp_sock.sendall(pack_client_decision(decision))
                        break  # Exit user input loop, wait for dealer


                # Wait for Dealer sequence and final result
                while not game_over:
                    data = tcp_sock.recv(9)
                    if not data: break
                    res, rank, suit = unpack_server_payload(data)

                    if res != 0:  # Game ended (Win/Loss/Tie)
                        if res == 2:
                            print(f"Dealer have total value of {calculate_hand(dealer_ranks)}")
                            print("You Lost!")
                        elif res == 3:
                            print(f"Dealer have total value of {calculate_hand(dealer_ranks)}")
                            print("You Won!")
                        elif res == 1:
                            print(f"Dealer have total value of {calculate_hand(dealer_ranks)}")
                            print("Tie!")
                        game_over = True
                    else:
                        # Dealer drew a card
                        if len(dealer_ranks) == 1:
                            print(f"Dealer reveals hidden card: {get_rank_str(rank)} of {get_suit_char(suit)}")
                        else:
                            print(f"Dealer draw: {get_rank_str(rank)} of {get_suit_char(suit)}")

                        dealer_ranks.append(rank)


            print("All rounds finished. Disconnecting.")
            tcp_sock.close()
            # Loop back to UDP listening

        except Exception as e:
            print(f"Connection error: {e}")
            if 'tcp_sock' in locals(): tcp_sock.close()


if __name__ == "__main__":
    client_main(input("Enter your team name: "))
