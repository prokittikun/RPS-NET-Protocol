import socket
import struct
import csv
import threading
import var as v

# การกำหนดค่าเซิร์ฟเวอร์
HOST = '127.0.0.1'
PORT = 12345

# กำหนดโครงสร้าง header
# v.SERVER_HEADER_FORMAT = '!IHHI'  # unsigned int, unsigned short, unsigned short
# HEADER_SIZE = struct.calcsize(v.SERVER_HEADER_FORMAT)
# CLIENT_HEADER_FORMAT = '!IHH'
# CLIENT_HEADER_SIZE = struct.calcsize(CLIENT_HEADER_FORMAT)

# ประเภทข้อความ
# v.MSG_LOGIN = 1
# v.MSG_LOGIN_RESULT = 2
# v.MSG_NORMAL = 3
# v.MSG_GAME_ACTION = 4
# v.MSG_GAME_RESULT = 5
# v.MSG_LIST_ROOMS = 6
# v.MSG_JOIN_ROOM = 7
# v.MSG_PLAYER_QUIT = 8

# เกม Rock Paper Scissors
# GAME_CHOICES = ['rock', 'paper', 'scissors']
game_rooms = {}  # {room_id: {'players': [player1, player2], 'choices': {}, 'status': 'waiting'/'playing'}}



def create_header(message_type, payload_length, status_code=200):
    version = 1
    return struct.pack(v.SERVER_HEADER_FORMAT, version, message_type, payload_length, status_code)

def parse_header(header_data):
    return struct.unpack(v.CLIENT_HEADER_FORMAT, header_data)

def load_users():
    users = {}
    with open('users.csv', 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        for row in csv_reader:
            users[row[0]] = row[1]
    return users

def save_user(username, password):
    with open('users.csv', 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([username, password])

def handle_register(payload):
    username, password = payload.split(',')
    if username in users:
        return "Username already exists", 409 
    else:
        save_user(username, password)
        users[username] = password  
        return "Registration successful", 201  
    
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

def create_new_room(username):
    new_room_id = max(game_rooms.keys()) + 1 if game_rooms else 1
    game_rooms[new_room_id] = {'players': [username], 'choices': {}, 'status': 'waiting'}
    return new_room_id

def join_game(username, room_id=None):
    if room_id:
        if room_id in game_rooms and len(game_rooms[room_id]['players']) < 2:
            game_rooms[room_id]['players'].append(username)
            if len(game_rooms[room_id]['players']) == 2:
                game_rooms[room_id]['status'] = 'playing'
            return room_id, game_rooms[room_id]['status']
        else:
            return None, None

def handle_game_action(username, action, room_id):
    room = game_rooms.get(room_id)
    if not room:
        return "Invalid room", [username]
    
    if username not in room['players']:
        return "You are not in this game room", [username]
    
    if room['status'] != 'playing':
        return "Waiting for another player to join.", [username]
    
    if action == "check_status":
        if room['status'] == 'playing':
            return "Game is ready to start!", [username]
        else:
            return "Waiting for another player to join.", [username]
        
    if action not in v.GAME_CHOICES:
        return "Invalid choice. Please choose rock, paper, or scissors.", [username]
    
    room['choices'][username] = action
    
    if len(room['choices']) == 1:
        return "Waiting for other player's choice...", [username]
    elif len(room['choices']) == 2:
        result = determine_winner(room)
        room['choices'] = {}  # Reset choices for next round
        return result, room['players']

def determine_winner(room):
    players = room['players']
    choices = room['choices']
    
    result = f"Game result:\n{players[0]}: {choices[players[0]]}\n{players[1]}: {choices[players[1]]}\n"
    
    if choices[players[0]] == choices[players[1]]:
        result += "It's a tie!"
    elif (
        (choices[players[0]] == 'rock' and choices[players[1]] == 'scissors') or
        (choices[players[0]] == 'paper' and choices[players[1]] == 'rock') or
        (choices[players[0]] == 'scissors' and choices[players[1]] == 'paper')
    ):
        result += f"{players[0]} wins!"
    else:
        result += f"{players[1]} wins!"
    
    # room['choices'] = {}  # Reset choices for next round
    return result

def handle_client(conn, addr):
    print(f"เชื่อมต่อใหม่จาก {addr}")
    logged_in_user = None
    user_room = None
    
    try:
        while True:
            try:
                header_data = conn.recv(v.CLIENT_HEADER_SIZE)
                if not header_data or len(header_data) < v.CLIENT_HEADER_SIZE:
                    print(f"Invalid header from {addr}. Closing connection.")
                    break
                
                version, message_type, payload_length = parse_header(header_data)
                payload = conn.recv(payload_length).decode()
                
                if message_type == v.MSG_LOGIN:
                    username, password = payload.split(',')
                    login_success = check_login(username, password, users)
                    if login_success:
                        response = "Login successful"
                        logged_in_user = username
                        active_users[conn] = username
                        print(f"User '{username}' logged in")
                        status_code = 200
                    else:
                        response = "Login failed"
                        status_code = 401
                    
                    header = create_header(v.MSG_LOGIN_RESULT, len(response), status_code)
                    conn.sendall(header + response.encode())
                elif message_type == v.MSG_REGISTER:
                    response, status_code = handle_register(payload)
                    header = create_header(v.MSG_NORMAL, len(response), status_code)
                    conn.sendall(header + response.encode())
                elif message_type == v.MSG_LIST_ROOMS:
                    available_rooms = get_available_rooms()
                    response = ','.join(map(str, available_rooms))
                    header = create_header(v.MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
                
                elif message_type == v.MSG_JOIN_ROOM:
                    if logged_in_user:
                        if payload == "create":
                            user_room = create_new_room(logged_in_user)
                            response = f"Created and joined room {user_room}. Waiting for another player."
                        else:
                            room_id = int(payload)
                            joined_room, status = join_game(logged_in_user, room_id)
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
                    header = create_header(v.MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
                
                elif message_type == v.MSG_GAME_ACTION:
                    if logged_in_user:
                        user_room = None
                        for room_id, room in game_rooms.items():
                            if logged_in_user in room['players']:
                                user_room = room_id
                                break
                        
                        if user_room is not None:
                            result, players_to_notify = handle_game_action(logged_in_user, payload, user_room)
                            print(f"Game action from {logged_in_user} in room {user_room}: {payload}")
                            
                            if len(players_to_notify) == 2: 
                                print(f"Result: {result}")
                                for player in players_to_notify:
                                    player_conn = next((conn for conn, user in active_users.items() if user == player), None)
                                    if player_conn:
                                        header = create_header(v.MSG_GAME_RESULT, len(result))
                                        player_conn.sendall(header + result.encode())
                            else:  
                                header = create_header(v.MSG_NORMAL, len(result))
                                conn.sendall(header + result.encode())
                        else:
                            response = "You need to join a game room first"
                            header = create_header(v.MSG_NORMAL, len(response))
                            conn.sendall(header + response.encode())
                    else:
                        response = "You need to login first"
                        header = create_header(v.MSG_NORMAL, len(response))
                        conn.sendall(header + response.encode())
                
                elif message_type == v.MSG_NORMAL:
                    if logged_in_user:
                        print(f"ข้อความจาก {logged_in_user} ({addr}): {payload}")
                        response = f"Server received: {payload}"
                        status_code = 200
                    else:
                        print(f"ข้อความจากผู้ใช้ที่ไม่ได้ login ({addr}): {payload}")
                        response = "Please login first"
                        status_code = 401
                    
                    header = create_header(v.MSG_NORMAL, len(response), status_code)
                    conn.sendall(header + response.encode())
                elif message_type == v.MSG_PLAYER_QUIT:
                    if logged_in_user and user_room:
                        room = game_rooms[user_room]
                        room['players'].remove(logged_in_user)
                        if len(room['players']) == 1:
                            remaining_player = room['players'][0]
                            remaining_conn = next((c for c, u in active_users.items() if u == remaining_player), None)
                            if remaining_conn:
                                quit_message = f"{logged_in_user} has left the game. Waiting for a new player..."
                                header = create_header(v.MSG_NORMAL, len(quit_message))
                                remaining_conn.sendall(header + quit_message.encode())
                        elif len(room['players']) == 0:
                            del game_rooms[user_room]
                        response = "You have left the game."
                    else:
                        response = "You are not in a game."
                    header = create_header(v.MSG_NORMAL, len(response))
                    conn.sendall(header + response.encode())
                    # break  # ออกจากลูป while เพื่อปิดการเชื่อมต่อ
            except ConnectionResetError:
                print(f"การเชื่อมต่อถูกปิดอย่างไม่คาดคิดจาก {addr}")
                break
            except Exception as e:
                print(f"เกิดข้อผิดพลาด: {e}")
                break
    
    finally:
        if logged_in_user:
            del active_users[conn]
            if user_room and user_room in game_rooms:
                room = game_rooms[user_room]
                if logged_in_user in room['players']:
                    room['players'].remove(logged_in_user)
                    if len(room['players']) == 1:
                        remaining_player = room['players'][0]
                        remaining_conn = next((c for c, u in active_users.items() if u == remaining_player), None)
                        if remaining_conn:
                            quit_message = f"{logged_in_user} has disconnected. Waiting for a new player..."
                            header = create_header(v.MSG_NORMAL, len(quit_message))
                            remaining_conn.sendall(header + quit_message.encode())
                    elif len(room['players']) == 0:
                        del game_rooms[user_room]
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
