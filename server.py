import socket
import struct
import csv
import threading
import random

# การกำหนดค่าเซิร์ฟเวอร์
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

# เกม Rock Paper Scissors
GAME_CHOICES = ['rock', 'paper', 'scissors']
game_rooms = {}  # {room_id: {'players': [player1, player2], 'choices': {}, 'status': 'waiting'/'playing'}}

def create_header(message_type, payload_length):
    version = 1
    return struct.pack(HEADER_FORMAT, version, message_type, payload_length)

def parse_header(header_data):
    return struct.unpack(HEADER_FORMAT, header_data)

def load_users():
    users = {}
    with open('users.csv', 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # ข้าม header
        for row in csv_reader:
            users[row[0]] = row[1]
    return users

def check_login(username, password, users):
    return username in users and users[username] == password

users = load_users()
active_users = {}  # เก็บข้อมูล user ที่ active อยู่

def get_available_rooms():
    available_rooms = []
    for room_id, room in game_rooms.items():
        if len(room['players']) < 2:
            available_rooms.append(room_id)
    return available_rooms

def create_or_join_game(username, room_id=None):
    if room_id:
        if room_id in game_rooms and len(game_rooms[room_id]['players']) < 2:
            game_rooms[room_id]['players'].append(username)
            if len(game_rooms[room_id]['players']) == 2:
                game_rooms[room_id]['status'] = 'playing'
            return room_id, game_rooms[room_id]['status']
        else:
            return None, None
    else:
        new_room_id = max(game_rooms.keys()) + 1 if game_rooms else 1
        game_rooms[new_room_id] = {'players': [username], 'choices': {}, 'status': 'waiting'}
        return new_room_id, 'waiting'

def handle_game_action(username, action, room_id):
    room = game_rooms.get(room_id)
    if not room:
        return "Invalid room"
    
    if username not in room['players']:
        return "You are not in this game room"
    
    if room['status'] != 'playing':
        return "Waiting for another player to join."
    
    if action == "check_status":
        if room['status'] == 'playing':
            return "Game is ready to start!"
        else:
            return "Waiting for another player to join."
    
    if action not in GAME_CHOICES:
        return "Invalid choice. Please choose rock, paper, or scissors."
    
    room['choices'][username] = action
    
    if len(room['choices']) == 2:
        return determine_winner(room)
    else:
        return "Waiting for other player's choice..."

def determine_winner(room):
    players = room['players']
    choices = room['choices']
    
    if choices[players[0]] == choices[players[1]]:
        result = "It's a tie!"
    elif (
        (choices[players[0]] == 'rock' and choices[players[1]] == 'scissors') or
        (choices[players[0]] == 'paper' and choices[players[1]] == 'rock') or
        (choices[players[0]] == 'scissors' and choices[players[1]] == 'paper')
    ):
        result = f"{players[0]} wins!"
    else:
        result = f"{players[1]} wins!"
    
    room['choices'] = {}  # Reset choices for next round
    return result

def handle_client(conn, addr):
    print(f"เชื่อมต่อใหม่จาก {addr}")
    logged_in_user = None
    user_room = None
    
    try:
        while True:
            try:
                header_data = conn.recv(HEADER_SIZE)
                if not header_data or len(header_data) < HEADER_SIZE:
                    break
                
                version, message_type, payload_length = parse_header(header_data)
                payload = conn.recv(payload_length).decode()
                
                if message_type == MSG_LOGIN:
                    username, password = payload.split(',')
                    login_success = check_login(username, password, users)
                    if login_success:
                        response = "Login successful"
                        logged_in_user = username
                        active_users[addr] = username
                        print(f"User '{username}' logged in")
                    else:
                        response = "Login failed"
                    
                    header = create_header(MSG_LOGIN_RESULT, len(response))
                    conn.sendall(header + response.encode())
                
                elif message_type == MSG_LIST_ROOMS:
                    available_rooms = get_available_rooms()
                    response = ','.join(map(str, available_rooms))
                    header = create_header(MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
                
                elif message_type == MSG_JOIN_ROOM:
                    if logged_in_user:
                        room_id = int(payload)
                        joined_room, status = create_or_join_game(logged_in_user, room_id)
                        if joined_room:
                            user_room = joined_room
                            if status == 'playing':
                                response = f"Joined room {user_room}. Game is ready to start!"
                            else:
                                response = f"Joined room {user_room}. Waiting for another player."
                        else:
                            response = "Failed to join room"
                    else:
                        response = "Please login first"
                    header = create_header(MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
                
                elif message_type == MSG_GAME_ACTION:
                    if logged_in_user and user_room:
                        result = handle_game_action(logged_in_user, payload, user_room)
                        print(f"Game action from {logged_in_user} in room {user_room}: {payload}")
                        print(f"Result: {result}")
                        header = create_header(MSG_GAME_RESULT, len(result))
                        conn.sendall(header + result.encode())
                    else:
                        response = "You need to login and join a game room first"
                        header = create_header(MSG_NORMAL, len(response))
                        conn.sendall(header + response.encode())
                
                elif message_type == MSG_NORMAL:
                    if logged_in_user:
                        print(f"ข้อความจาก {logged_in_user} ({addr}): {payload}")
                        response = f"Server received: {payload}"
                    else:
                        print(f"ข้อความจากผู้ใช้ที่ไม่ได้ login ({addr}): {payload}")
                        response = "Please login first"
                    
                    header = create_header(MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
            
            except ConnectionResetError:
                print(f"การเชื่อมต่อถูกปิดอย่างไม่คาดคิดจาก {addr}")
                break
            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {e}")
                break
    
    finally:
        if logged_in_user:
            del active_users[addr]
            if user_room and user_room in game_rooms:
                game_rooms[user_room]['players'].remove(logged_in_user)
                if not game_rooms[user_room]['players']:
                    del game_rooms[user_room]
            print(f"User '{logged_in_user}' logged out from {addr}")
        print(f"ปิดการเชื่อมต่อจาก {addr}")
        conn.close()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"เซิร์ฟเวอร์ TCP กำลังรับฟังที่ {HOST}:{PORT}")
    
    while True:
        conn, addr = s.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()