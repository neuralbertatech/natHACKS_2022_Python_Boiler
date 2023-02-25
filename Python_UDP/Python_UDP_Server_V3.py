# import socket

# # bind all IP
# HOST = '0.0.0.0' 
# # Listen on Port 
# PORT = 8090 
# #Size of receive buffer   
# BUFFER_SIZE = 1024    
# # Create a TCP/IP socket
# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# # Bind the socket to the host and port
# s.bind((HOST, PORT))
# while True:
#     #   print ("Waiting for client...")

#     # Receive BUFFER_SIZE bytes data
#     # data is a list with 2 elements
#     # first is data
#     #second is client address
#     data = s.recvfrom(BUFFER_SIZE)
#     if data:
#         #print received data
#         print('Client to Server: ' , data)
#         # Convert to upper case and send back to Client
#         s.sendto(data[0].upper(), data[1])
# # Close connection
# s.close()


#########################################
# very simple and short upd-receiver found here
# https://www.studytonight.com/network-programming-in-python/working-with-udp-sockets#

# import socket

# sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)      # For UDP

# udp_host = socket.gethostname()		        # Host IP
# udp_port = 3333			                # specified port to connect

# #print type(sock) ============> 'type' can be used to see type
# 				# of any variable ('sock' here)
# sock.bind((udp_host,udp_port))

# while True:
#   print ("Waiting for client...")
#   data,addr = sock.recvfrom(32)	        #receive data from client
#   Msg = data.decode('ascii')
#   print ("Received Messages: #",Msg,"# from",addr)


##########################################

# import socket 

# localIP     = "192.168.16.65"
# localPort   = 8091
# bufferSize  = 1024

# msgFromServer       = "Hello UDP Client"
# bytesToSend         = str.encode(msgFromServer)

# # Create a datagram socket
# UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# # Bind to address and ip
# UDPServerSocket.bind((localIP, localPort))
# print("UDP server up and listening")

# # Listen for incoming datagrams
# while(True):

#     bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)

#     message = bytesAddressPair[0]

#     address = bytesAddressPair[1]

#     clientMsg = "Message from Client:{}".format(message)
#     clientIP  = "Client IP Address:{}".format(address)
    
#     print(clientMsg)
#     print(clientIP)

#     # Sending a reply to client

#     UDPServerSocket.sendto(bytesToSend, address)

###############################

# This python script listens on UDP port 3333 
# for messages from the ESP32 board and prints them
# import socket
# import sys

# try :
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# except:
#     print('Failed to create socket.')
#     sys.exit()

# try:
#     s.bind(('', 3333))
# except:
#     print('Bind failed. ')
#     sys.exit()
     
# print('Server listening')

# while 1:
#     d = s.recvfrom(1024)
#     data = d[0]
     
#     if not data: 
#         break
    
#     print(data.strip())
    
# s.close()


##################################

# import socket

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# server_address = '0.0.0.0'
# server_port = 3333

# server = (server_address, server_port)
# sock.bind(server)
# print("Listening on " + server_address + ":" + str(server_port))


# state = 0

# imu_count = 1

# ready_array = ["False"] * imu_count

# imu_dict = {
#     0: {
#         'is_ready' : True,
#         'is_read' : False,
#         'local_start_time' : None,
#         'local_end_time' : None,
#         'count' : 0,
#         'data': []
#     },   
# }

# client_address = ('192.168.1.34', 3333)

# init_packet = b"5001"

# while True:
#     if state == 0:
#         sent = sock.sendto(init_packet, client_address)



#     # if state == 0:
#     #     for x in range(imu_count):
#     #         # print("debug")
#     #         payload, client_address = sock.recvfrom(1000) # blocking call 
#     #         # print("Echoing data back to " + str(client_address))
#     #         print(payload)
#     #         state += 1
#     # if state == 1:
#         sent = sock.sendto(init_packet, client_address)

        


# step 1 is to decouple the send and receiving 
# step 2 async - reference embody
# step 3 have dict of multiple ports (perhaps port/servers)
# step 4 abstracting a single class, gets passed a dict of ports, init, add start/trig inject methods that iter through all ports, background thread that add to dict 
# step 5 add to the IMU_baseline


# https://stackoverflow.com/questions/48506460/python-simple-socket-client-server-using-asyncio 




import socket
from threading import Thread
from time import sleep
import sys

exit = False

def rxThread(server_address,server_port):
    global exit
    
    #Generate a UDP socket
    rxSocket = socket.socket(socket.AF_INET, #Internet
                             socket.SOCK_DGRAM) #UDP
                             
    #Bind to any available address on port *portNum*
    rxSocket.bind((server_address,server_port))
    
    #Prevent the socket from blocking until it receives all the data it wants
    #Note: Instead of blocking, it will throw a socket.error exception if it
    #doesn't get any data
    
    rxSocket.setblocking(0)
    
    print("RX: Receiving data on UDP port " + str(server_port))
    print("")
    
    while not exit:
        try:
            #Attempt to receive up to 1024 bytes of data
            data,addr = rxSocket.recvfrom(1024) 
            #Echo the data back to the sender
            rxSocket.sendto(str(data),addr)

        except socket.error:
            #If no data is received, you get here, but it's not an error
            #Ignore and continue
            pass

        sleep(.1)
    
def txThread(portNum):
    global exit
    
    
def main(args):    
    global exit
    print("UDP Tx/Rx Example application")
    print("Press Ctrl+C to exit")
    print("")

    client_ip = '192.168.1.34'
    server_address = '0.0.0.0'
    server_port = 3333
    
    udpRxThreadHandle = Thread(target=rxThread,args=(server_address,server_port,))    
    udpRxThreadHandle.start()
        
    sleep(.1)
    
    #Generate a transmit socket object
    txSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    
    #Do not block when looking for received data (see above note)
    txSocket.setblocking(0) 
   
    print("Transmitting to 127.0.0.1 port " + str(server_port))
    print("Type anything and press Enter to transmit")
    while True:
        try:
             #Retrieve input data 
            txChar = input("TX: ")
            
            #Transmit data to the local server on the agreed-upon port
            txSocket.sendto(bytes(txChar),(server_address,server_port))
            
            #Sleep to allow the other thread to process the data
            sleep(.2)
            
            #Attempt to receive the echo from the server
            data, addr = txSocket.recvfrom(1024)
            
            print("RX: " + str(data))

        except socket.error as e:    
            #If no data is received you end up here, but you can ignore
            #the error and continue
            pass   
        except KeyboardInterrupt:
            exit = True
            print("Received Ctrl+C... initiating exit")
            break
        sleep(.1)
         
    udpRxThreadHandle.join()
        
    return

if __name__=="__main__":
    main(sys.argv[1:0])    