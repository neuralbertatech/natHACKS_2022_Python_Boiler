from threading import Thread
import socket
import time

imu_dict = {
    0: {
        'address' : '192.168.0.117',
        'port' : '3331',
        # 'is_ready' : True,
        # 'is_read' : False,
        # 'local_start_time' : None,
        # 'local_end_time' : None,
        # 'count' : 0,
        # 'data': []
    },  
    1: {
        'address' : '192.168.0.170',
        'port' : '3332',
        # 'is_ready' : True,
        # 'is_read' : False,
        # 'local_start_time' : None,
        # 'local_end_time' : None,
        # 'count' : 0,
        # 'data': []
    }, 
    2: {
        'address' : '192.168.0.129',
        'port' : '3333',
        # 'is_ready' : True,
        # 'is_read' : False,
        # 'local_start_time' : None,
        # 'local_end_time' : None,
        # 'count' : 0,
        # 'data': []
    },  
}

# udp protocol
udp = socket.SOCK_DGRAM
#net address family: ip_v4
afm = socket.AF_INET

sock = socket.socket(afm,udp)

server_address = '0.0.0.0'
server_port = 3333
server = (server_address, server_port)

sock.bind(server)
print("Listening on " + server_address + ":" + str(server_port))

state = 0
imu_count = 3
ready_array = ["False"] * imu_count

# init_packet = b"5000"
client_address = '192.168.0.129'
client_port = server_port

client_address = (client_address, client_port)

running = True

def recv(stop):
    while True:
        msg_recv = sock.recvfrom(250)
        print(msg_recv)
        if stop():
            break

def send(stop):
    while True:
        msg = input("Tx: ")
        sock.sendto(msg.encode(),client_address)
        # sock.sendto(init_packet,client_address)
        if stop():
            break

stop = False

recv_thread = Thread(target = recv, args =(lambda : stop, ))
send_thread = Thread(target = send, args =(lambda : stop, ))

recv_thread.start()
send_thread.start()

time.sleep(100000)

stop = True

# recv_thread.join()j
send_thread.join()

print("threads shut down")

# Explore UDP Buffer
# 4000,100x,100,100
# 5000 - start
# 6000, 1001
# 7000

#### within the function that starts the send threads - need to define different states
#### pass socket, dict, client address

''' functions dynamically created
https://stackoverflow.com/questions/13184281/python-dynamic-function-creation-with-custom-names

def function_builder(args):
    def function(more_args):
       #do stuff based on the values of args
    return function

my_dynamic_functions = {}
my_dynamic_functions[dynamic_name] = function_builder(some_dynamic_args)

#then use it somewhere else
my_dynamic_functions[dynamic_name](the_args)

'''


# while True:
#     if state == 0:
#         sent = sock.sendto(init_packet, client_address)



    # if state == 0:
    #     for x in range(imu_count):
    #         # print("debug")
    #         payload, client_address = sock.recvfrom(1000) # blocking call 
    #         # print("Echoing data back to " + str(client_address))
    #         print(payload)
    #         state += 1
    # if state == 1:
        # sent = sock.sendto(init_packet, client_address)

        


# step 1 is to decouple the send and receiving 
# step 2 async - reference embody
# step 3 have dict of multiple ports (perhaps port/servers)
# step 4 abstracting a single class, gets passed a dict of ports, init, add start/trig inject methods that iter through all ports, background thread that add to dict 
# step 5 add to the IMU_baseline


# https://stackoverflow.com/questions/48506460/python-simple-socket-client-server-using-asyncio 