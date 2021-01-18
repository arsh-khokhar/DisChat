import socket
import sys
import select
import json

CHAT_NODE_ADDR = '127.0.0.1'
CHAT_NODE_PORT = 15020

argsFromCLI = sys.argv

if len(argsFromCLI) < 2:
    print("\nNot enough arguments!")
    print("Usage: \n  python3 client.py <Username> [optional: chatnode port to connect to]\n")
    sys.exit(1)

elif len(argsFromCLI) == 2:
    USER_NAME = argsFromCLI[1]

elif len(argsFromCLI) == 3:
    if not argsFromCLI[2].isdigit():
        print("\nChatnode port must be an integer!")
        print("Usage: \n  python3 client.py <Username> [optional: chatnode port to connect to]\n")
        sys.exit(1)
    USER_NAME = argsFromCLI[1]
    CHAT_NODE_PORT = int(argsFromCLI[2])

elif len(argsFromCLI) > 3:
    print("\nToo many arguments!")
    print("Usage: \n  python3 client.py <Username> [optional: chatnode port to connect to]\n")
    sys.exit(1)

mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

inputs = [mySocket, sys.stdin]
outputs = [mySocket]

mySocket.connect((CHAT_NODE_ADDR, CHAT_NODE_PORT))
print("Successfully connected to the chat node at {0} on port {1}".format(CHAT_NODE_ADDR, CHAT_NODE_PORT))

try:
    while True:
        readable, writeable, exceptional = select.select(inputs, outputs, inputs)
        
        myNewMsg = None
        
        for s in readable:
            if s is mySocket:
                try:
                    data = s.recv(1024).decode()
                    
                    if len(data) == 0: # cheking if the chatnode has closed the connection
                        print("\nConnection closed by the chat node.")
                        mySocket.close()
                        sys.exit(0)
                    
                    print()
                    print(data.strip()) # printing the new message
                
                except Exception as e:
                    print("Non decodable message received. Ignoring...")
            
            elif s is sys.stdin: # if stdin is readble, it means the user has typed a new message
                myNewMsg = sys.stdin.readline()

        for s in writeable:
            # If there's a new message, send it to the chatnode
            if s is mySocket and myNewMsg is not None:
                s.send(json.dumps({"user": USER_NAME, "message": myNewMsg}).encode())

except KeyboardInterrupt:
    # closing the connection on Keyboard interrupt
    print("\nClosing the connection with the chat node...")
    mySocket.close()
    print("Closed the connection successfully.")
    sys.exit(0)

finally:
    mySocket.close()