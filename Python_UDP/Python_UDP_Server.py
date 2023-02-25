import socket
import time 

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = '0.0.0.0'
server_port = 3333

server = (server_address, server_port)
sock.bind(server)
print("Listening on " + server_address + ":" + str(server_port))

client_address = '192.168.0.129'
client_port = server_port

client_address = (client_address, client_port)

message = b"Hello from Server!"

while True:
    time.sleep(1)
    # print("debug")
    payload, client_address = sock.recvfrom(1000) # blocking call 
    # # print("Echoing data back to " + str(client_address))
    # print(payload)

    print(client_address)
    # print(type(client_address))
    # print(client_address)

    sent = sock.sendto(message, client_address)
    print(sent)

# step 1 is to decouple the send and receiving 
# step 2 async - reference embody
# step 3 have dict of multiple ports (perhaps port/servers)
# step 4 abstracting a single class, gets passed a dict of ports, init, add start/trig inject methods that iter through all ports, background thread that add to dict 
# step 5 add to the IMU_baseline

# https://stackoverflow.com/questions/48506460/python-simple-socket-client-server-using-asyncio 