import socket
import struct
import time
import var as v
# การกำหนดค่าการเชื่อมต่อ
HOST = '127.0.0.1'
PORT = 12345

# กำหนดโครงสร้าง header
# v.CLIENT_HEADER_FORMAT = '!IHH'  # unsigned int, unsigned short, unsigned short
# SERVER_HEADER_FORMAT = '!IHHI'
# HEADER_SIZE = struct.calcsize(v.CLIENT_HEADER_FORMAT)
# v.SERVER_HEADER_SIZE = struct.calcsize(v.SERVER_HEADER_FORMAT)

# ประเภทข้อความ
# v.MSG_LOGIN = 1
# v.MSG_LOGIN_RESULT = 2
# v.MSG_NORMAL = 3
# v.MSG_GAME_ACTION = 4
# v.MSG_GAME_RESULT = 5
# v.MSG_LIST_ROOMS = 6
# v.MSG_JOIN_ROOM = 7
# v.MSG_PLAYER_QUIT = 8
# GAME_CHOICES = ['rock', 'paper', 'scissors']

def create_header(message_type, payload_length):
    version = 1
    return struct.pack(v.CLIENT_HEADER_FORMAT, version, message_type, payload_length)

def parse_header(header_data):
    return struct.unpack(v.SERVER_HEADER_FORMAT, header_data)

def send_message(sock, message_type, payload):
    header = create_header(message_type, len(payload))
    sock.sendall(header + payload.encode())
    response_header = sock.recv(v.SERVER_HEADER_SIZE)
    version, resp_type, resp_length, status_code = parse_header(response_header)
    response_payload = sock.recv(resp_length).decode()
    
    return version, resp_type, status_code, response_payload

def login(sock):
    username = input("Username: ")
    password = input("Password: ")
    login_payload = f"{username},{password}"
    
    version, resp_type, status_code, response = send_message(sock, v.MSG_LOGIN, login_payload)
    print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
    return "Login successful" in response

def list_and_choose_room(sock):
    version, resp_type, status_code, response = send_message(sock, v.MSG_LIST_ROOMS, "")
    print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
    # print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
    available_rooms = response.split(',')
    if not available_rooms or available_rooms[0] == '':
        print("\nNo available rooms.")
        while True:
            choice = input("Press Enter to create a new room or 'back' to menu: ")
            if choice == "":
                return "create"
            if choice == "back":
                return "back"
            print("Invalid command. Please try again.")

    else:
        print("\nAvailable rooms:")
        print("=" * 30)  # Horizontal line for separation
        for idx, room in enumerate(available_rooms, start=1):
            print(f"Room {room}")
        print("=" * 30)  # Horizontal line for separation
        
        while True:
            choice = input("Enter room number to join, or press Enter to create a new room or 'back' to menu: ")
            if choice == "":
                return "create"
            if choice == "back":
                return "back"
            if choice in available_rooms:
                return choice
            print("Invalid room number. Please try again.")

def play_game(sock):
    print("Waiting for the game to start...")
    while True:
        version, resp_type, status_code, response = send_message(sock, v.MSG_GAME_ACTION, "check_status")
        if "Game is ready to start" in response:
            print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
            print("Game is starting!")
            break
        elif "Waiting for another player" in response:
            print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
            print("Still waiting for another player...")
            time.sleep(5)  # รอ 5 วินาทีก่อนเช็คสถานะอีกครั้ง
        else:
            print(response)
            return

    while True:
        action = input("Enter your choice (rock/paper/scissors) or 'quit' to exit: ")
        if action.lower() == 'quit':
            send_message(sock, v.MSG_PLAYER_QUIT, "")
            break
        if action in v.GAME_CHOICES:
            version, resp_type, status_code, response = send_message(sock, v.MSG_GAME_ACTION, action)
            if resp_type == v.MSG_NORMAL:
                print(response)  # "Waiting for other player's choice..."
                print("Waiting for the result...")
                # รอผลลัพธ์จากเซิร์ฟเวอร์
                version, resp_type, status_code, result = receive_message(sock)
                if resp_type == v.MSG_GAME_RESULT:
                    print(result)
                    continue_play = input("Do you want to play another round? (y/n): ")
                    if continue_play.lower() != 'y':
                        send_message(sock, v.MSG_PLAYER_QUIT, "")
                        break
                elif resp_type == v.MSG_NORMAL:
                    print(result)  # อาจจะเป็นข้อความว่าผู้เล่นอีกคนออกจากเกม
                    wait_new_player = input("Do you want to wait for a new player? (y/n): ")
                    if wait_new_player.lower() != 'y':
                        send_message(sock, v.MSG_PLAYER_QUIT, "")
                        break
            elif resp_type == v.MSG_GAME_RESULT:
                print(response)
                continue_play = input("Do you want to play another round? (y/n): ")
                if continue_play.lower() != 'y':
                    send_message(sock, v.MSG_PLAYER_QUIT, "")
                    break
        else:
            print("Invalid choice. Please choose rock, paper, or scissors.")
    print("You have left the game.")

def register(sock):
    username = input("Enter new username: ")
    password = input("Enter new password: ")
    register_payload = f"{username},{password}"
    
    version, resp_type, status_code, response = send_message(sock, v.MSG_REGISTER, register_payload)
    print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
    return status_code == 201
def receive_message(sock):
    header_data = sock.recv(v.SERVER_HEADER_SIZE)
    version, message_type, payload_length, status_code = parse_header(header_data)
    payload = sock.recv(payload_length).decode()
    return version, message_type, status_code, payload

def print_menu():
    print("+----------------------------+")
    print("|        Main Menu           |")
    print("+----------------------------+")
    print("| 1. Register                |")
    print("| 2. Login                   |")
    print("| 3. List rooms              |")
    print("| 4. Quit                    |")
    print("+----------------------------+")
    
def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"เชื่อมต่อกับเซิร์ฟเวอร์ที่ {HOST}:{PORT}")
            
            logged_in = False
            while True:
                print_menu()
                choice = input("Enter your choice: ")

                if choice == "1":
                    registered = register(s)
                    if registered:
                        print("Registration successful. You can now log in.")
                    else:
                        print("Registration failed. Please try again.")
                elif choice == "2":
                    logged_in = login(s)
                    if not logged_in:
                        print("Login failed. Please try again.")
                elif choice == "3":
                    if not logged_in:
                        print("You need to log in first.")
                    else:
                        room_choice = list_and_choose_room(s)
                        if room_choice == "back":
                            continue
                        
                        version, resp_type, status_code, response = send_message(s, v.MSG_JOIN_ROOM, str(room_choice))

                        if "Joined room" in response or "Created and joined room" in response:
                            print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
                            play_game(s)
                        else:
                            print("Failed to join or create a room.")
                elif choice == "4":
                    print("Exiting the program. Goodbye!")
                    break
                else:
                    print("Invalid choice. Please select 1, 2, 3, or 4.")
            # logged_in = False
            # while not logged_in:
            #     logged_in = login(s)
            #     if not logged_in:
            #         print("Login failed. Please try again.")
            
            # print("You are now logged in!")
            # room_choice = list_and_choose_room(s)
            # version, resp_type, status_code, response = send_message(s, v.MSG_JOIN_ROOM, str(room_choice))

            # if "Joined room" in response or "Created and joined room" in response:
            #     print(f"\nRPS-Net: {status_code} - {v.STATUS_CODES[status_code]} - {response}")
            #     play_game(s)
            # else:
            #     print("Failed to join or create a room.")
            
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