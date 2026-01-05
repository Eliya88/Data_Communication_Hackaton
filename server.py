from constants import MAGIC_COOKIE, PAYLOAD_TYPE, UDP_PORT
import socket
import struct
import threading
import time
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional


# --- Constants ---
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
SERVER_NAME_LEN = 32
CLIENT_NAME_LEN = 32

ROUND_NOT_OVER = 0x0
TIE = 0x1
LOSS = 0x2
WIN = 0x3
SUITS = ["H", "D", "C", "S"]

@dataclass(frozen=True)
class Card:
    rank: int
    suit: int

    def value(self) -> int:
        if self.rank == 1: return 11
        if self.rank >= 11: return 10
        return self.rank

    def __str__(self) -> str:
        rank_str = {1: "A", 11: "J", 12: "Q", 13: "K"}.get(self.rank, str(self.rank))
        return f"{rank_str}{SUITS[self.suit]}"


# --- Helpers ---
def make_shuffled_deck() -> List[Card]:
    deck = [Card(r, s) for s in range(4) for r in range(1, 14)]
    random.shuffle(deck)
    return deck


def pack_fixed_name(name: str, length: int) -> bytes:
    b = name.encode("utf-8", errors="ignore")[:length]
    return b + b"\x00" * (length - len(b))


def parse_request(data: bytes) -> Optional[Tuple[int, str]]:
    try:
        cookie, mtype, rounds, name = struct.unpack("!IBB32s", data)
        if cookie != MAGIC_COOKIE or mtype != REQUEST_TYPE: return None
        return rounds, name.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
    except struct.error:
        return None


def pack_payload(decision_5: bytes, result: int, card: Optional[Card]) -> bytes:
    rank, suit = (card.rank, card.suit) if card else (0, 0)
    return struct.pack("!IB5sBHB", MAGIC_COOKIE, PAYLOAD_TYPE, decision_5, result, rank, suit)


def recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    chunks = []
    got = 0
    while got < n:
        try:
            part = sock.recv(n - got)
            if not part: return None
            chunks.append(part)
            got += len(part)
        except socket.timeout:
            return None
    return b"".join(chunks)


def hand_total(hand: List[Card]) -> int:
    return sum(c.value() for c in hand)


# --- Server Logic ---
def udp_offer_broadcaster(tcp_port: int, server_name: str, stop_event: threading.Event):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    pkt = struct.pack("!IBH32s", MAGIC_COOKIE, OFFER_TYPE, tcp_port, pack_fixed_name(server_name, 32))
    while not stop_event.is_set():
        try:
            s.sendto(pkt, ("<broadcast>", UDP_PORT))
        except OSError:
            pass
        time.sleep(1.0)
    s.close()


def handle_client(conn: socket.socket, addr: Tuple[str, int], server_name: str):
    conn.settimeout(10.0)
    try:
        req_data = recv_exact(conn, 38)
        parsed = parse_request(req_data) if req_data else None
        if not parsed: return
        rounds, client_name = parsed
        print(f"[{addr[0]}] Connected: {client_name}, {rounds} rounds")

        for r in range(1, rounds + 1):
            deck = make_shuffled_deck()
            player, dealer = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]
            # Initial deal
            for c in [player[0], player[1], dealer[0]]:
                conn.sendall(pack_payload(b"-----", ROUND_NOT_OVER, c))

            # Player turn
            while hand_total(player) <= 21:
                incoming = recv_exact(conn, 14)
                if not incoming: break
                decision = struct.unpack("!IB5sBHB", incoming)[2].strip(b"\x00")
                if decision == b"Hittt":
                    c = deck.pop()
                    player.append(c)
                    conn.sendall(pack_payload(b"-----", ROUND_NOT_OVER, c))
                else:
                    break

            # Dealer turn and results
            if hand_total(player) <= 21:
                conn.sendall(pack_payload(b"-----", ROUND_NOT_OVER, dealer[1]))
                while hand_total(dealer) < 17:
                    c = deck.pop()
                    dealer.append(c)
                    conn.sendall(pack_payload(b"-----", ROUND_NOT_OVER, c))

            p_sum, d_sum = hand_total(player), hand_total(dealer)
            res = WIN if (p_sum <= 21 and (d_sum > 21 or p_sum > d_sum)) else (TIE if p_sum == d_sum else LOSS)
            conn.sendall(pack_payload(b"-----", res, None))
    finally:
        conn.close()


def main():
    # קבלת שם הצוות מהמשתמש
    server_name = input("Enter server team name: ").strip() or "ServerTeam"

    # יצירת TCP Socket והצמדה לפורט פנוי (0 אומר למערכת לבחור עבורנו)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 0))
    sock.listen()

    # חילוץ הפורט שנבחר וה-IP של המכונה
    port = sock.getsockname()[1]
    try:
        # ניסיון להשיג את ה-IP המקומי של המחשב
        ip_address = socket.gethostbyname(socket.gethostname())
    except:
        ip_address = "127.0.0.1"  # גיבוי למקרה של תקלה בזיהוי השם

    # הדפסה לפי הפורמט המדויק שנדרש במטלה
    print(f"Server started, listening on IP address {ip_address}, TCP port {port}")

    # התחלת שליחת ה-Offers ב-Thread נפרד
    stop = threading.Event()
    threading.Thread(target=udp_offer_broadcaster, args=(port, server_name, stop), daemon=True).start()

    # לולאת קבלת לקוחות
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr, server_name), daemon=True).start()

if __name__ == "__main__":
    main()
