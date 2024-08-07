import socket
import struct
import time

# การกำหนดค่าการเชื่อมต่อ
HOST = '127.0.0.1'
PORT = 12345

# กำหนดโครงสร้าง header
HEADER_FORMAT = '!IHH'  # unsigned int, unsigned short, unsigned short
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# ประเภทข้อความ
MSG_LOGIN = 1
MSG_LOGIN_RESULT = 2
MSG_NORMAL = 3
MSG_GAME_ACTION = 4
MSG_GAME_RESULT = 5
MSG_LIST_ROOMS = 6
MSG_JOIN_ROOM = 7
MSG_PLAYER_QUIT = 8
# เกม Rock Paper Scissors
GAME_CHOICES = ['rock', 'paper', 'scissors']

def create_header(message_type, payload_length):
    version = 1
    return struct.pack(HEADER_FORMAT, version, message_type, payload_length)

def parse_header(header_data):
    return struct.unpack(HEADER_FORMAT, header_data)

def send_message(sock, message_type, payload):
    header = create_header(message_type, len(payload))
    sock.sendall(header + payload.encode())
    
    response_header = sock.recv(HEADER_SIZE)
    version, resp_type, resp_length = parse_header(response_header)
    
    response_payload = sock.recv(resp_length).decode()
    
    return version, resp_type, response_payload

def login(sock):
    username = input("Username: ")
    password = input("Password: ")
    login_payload = f"{username},{password}"
    
    version, resp_type, response = send_message(sock, MSG_LOGIN, login_payload)
    print(response)
    
    return "Login successful" in response

def list_and_choose_room(sock):
    version, resp_type, response = send_message(sock, MSG_LIST_ROOMS, "")
    available_rooms = response.split(',')
    if not available_rooms or available_rooms[0] == '':
        print("No available rooms. Creating a new room.")
        return "create"

    print("Available rooms:")
    for room in available_rooms:
        print(f"Room {room}")
    
    while True:
        choice = input("Enter room number to join, or press Enter to create a new room: ")
        if choice == "":
            return "create"
        if choice in available_rooms:
            return choice
        print("Invalid room number. Please try again.")

def play_game(sock):
    print("Waiting for the game to start...")
    while True:
        version, resp_type, response = send_message(sock, MSG_GAME_ACTION, "check_status")
        if "Game is ready to start" in response:
            print("Game is starting!")
            break
        elif "Waiting for another player" in response:
            print("Still waiting for another player...")
            time.sleep(5)  # รอ 5 วินาทีก่อนเช็คสถานะอีกครั้ง
        else:
            print(response)
            return

    while True:
        action = input("Enter your choice (rock/paper/scissors) or 'quit' to exit: ")
        if action.lower() == 'quit':
            send_message(sock, MSG_PLAYER_QUIT, "")
            break
        if action in GAME_CHOICES:
            version, resp_type, response = send_message(sock, MSG_GAME_ACTION, action)
            if resp_type == MSG_NORMAL:
                print(response)  # "Waiting for other player's choice..."
                print("Waiting for the result...")
                # รอผลลัพธ์จากเซิร์ฟเวอร์
                version, resp_type, result = receive_message(sock)
                if resp_type == MSG_GAME_RESULT:
                    print(result)
                    continue_play = input("Do you want to play another round? (y/n): ")
                    if continue_play.lower() != 'y':
                        send_message(sock, MSG_PLAYER_QUIT, "")
                        break
                elif resp_type == MSG_NORMAL:
                    print(result)  # อาจจะเป็นข้อความว่าผู้เล่นอีกคนออกจากเกม
                    wait_new_player = input("Do you want to wait for a new player? (y/n): ")
                    if wait_new_player.lower() != 'y':
                        send_message(sock, MSG_PLAYER_QUIT, "")
                        break
            elif resp_type == MSG_GAME_RESULT:
                print(response)
                continue_play = input("Do you want to play another round? (y/n): ")
                if continue_play.lower() != 'y':
                    send_message(sock, MSG_PLAYER_QUIT, "")
                    break
        else:
            print("Invalid choice. Please choose rock, paper, or scissors.")
    print("You have left the game.")

def receive_message(sock):
    header_data = sock.recv(HEADER_SIZE)
    version, message_type, payload_length = parse_header(header_data)
    payload = sock.recv(payload_length).decode()
    return version, message_type, payload

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"เชื่อมต่อกับเซิร์ฟเวอร์ที่ {HOST}:{PORT}")
            
            logged_in = False
            while not logged_in:
                logged_in = login(s)
                if not logged_in:
                    print("Login failed. Please try again.")
            
            print("You are now logged in!")
            room_choice = list_and_choose_room(s)
            version, resp_type, response = send_message(s, MSG_JOIN_ROOM, str(room_choice))

            print(response)

            if "Joined room" in response or "Created and joined room" in response:
                print(response)
                play_game(s)
            else:
                print("Failed to join or create a room.")
            
        except ConnectionRefusedError:
            print("ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้")
        except ConnectionResetError:
            print("การเชื่อมต่อถูกปิดโดยเซิร์ฟเวอร์")
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
        finally:
            print("ปิดการเชื่อมต่อ")

if __name__ == "__main__":
    main()