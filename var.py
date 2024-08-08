import struct

CLIENT_HEADER_FORMAT = '!IHH'  # unsigned int, unsigned short, unsigned short
SERVER_HEADER_FORMAT = '!IHHI'
CLIENT_HEADER_SIZE = struct.calcsize(CLIENT_HEADER_FORMAT)
SERVER_HEADER_SIZE = struct.calcsize(SERVER_HEADER_FORMAT)

# ประเภทข้อความ
MSG_LOGIN = 1
MSG_LOGIN_RESULT = 2
MSG_NORMAL = 3
MSG_GAME_ACTION = 4
MSG_GAME_RESULT = 5
MSG_LIST_ROOMS = 6
MSG_JOIN_ROOM = 7
MSG_PLAYER_QUIT = 8
MSG_REGISTER = 9
GAME_CHOICES = ['rock', 'paper', 'scissors']

STATUS_CODES = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    409: "Conflict",
    500: "Internal Server Error"
}