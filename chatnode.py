import socket
import sys
import select
import time
import json
import argparse
import logging
import traceback    # for tracing back exceptions
from zeroconf import ServiceBrowser, Zeroconf, IPVersion, ServiceInfo

# MyListener class for zeroconf
class MyListener:
    
    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))
        info = zeroconf.get_service_info(type, name)
        for key in list(peers_with_timestamps.keys()):
            if peers_with_timestamps[key][1] == name:
                print("Removing {0} from known peers list...".format(name))
                del peers_with_timestamps[key]
        print("\nKnown peers: {0}\n".format(list(peers_with_timestamps.keys())))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print("Service %s added, service info: %s" % (name, info))
        if not (socket.inet_ntoa(info.addresses[0]) == socket.gethostbyname(socket.gethostname()) and info.port == EXTERN_PORT):
            peers_with_timestamps[(socket.inet_ntoa(info.addresses[0]), info.port)] = [getMyCurrentTime(), name]
        print("\nKnown peers: {0}\n".format(list(peers_with_timestamps.keys())))
    
    def update_service(self, zeroconf, type, name):
        #just to avoid the warning from zeroconf
        return

def sendPingToPeer(peerAddress):
    """method responsible for sending a ping to the peer

    Args:
        peerAddress (tuple): address of the peer to send the ping
    """
    print("Pinging peer at {0}".format(peerAddress))
    toSend = json.dumps({ "command" : "PING" }).encode()
    ret = serversocket.sendto(toSend, peerAddress)
    if not ret == len(toSend): # Checking if the ping was sent successfully
        print("Failed to send ping to the peer {0}".format(peer))

def sendMessageToPeer(peerAddress, arg_message, arg_user):
    """method responsible to send a message to a peer

    Args:
        peerAddress (tuple): address of the peer to send the message
        arg_message (string): new message
        arg_user (string): user that sent this message 
    """
    print("Sending message to peer at {0}".format(peerAddress))
    toSend = json.dumps({ "command" : "MSG", "message" : arg_message, "user" : arg_user}).encode()
    print("To send is: {0}".format(toSend))
    ret = serversocket.sendto(toSend, peerAddress)
    if not ret == len(toSend): # Checking if the message was sent successfully
        print("Failed to send message to the peer {0}".format(peer))

def removeUnpingedPeers():
    """Method responsible for removing all the peers from known peer list who did not send a ping in the given time
    """
    for peer in list(peers_with_timestamps.keys()):
        # checking if the last ping of the peer is older than the given timeout
        if getMyCurrentTime() - peers_with_timestamps[peer][0] > PEER_PING_TIMEOUT_IN_SECONDS:
            print("No ping received from {0} in last {1} seconds. Removing it from known peers...".format(peer,PEER_PING_TIMEOUT_IN_SECONDS))
            del peers_with_timestamps[peer]
            print("\nKnown peers: {0}\n".format(list(peers_with_timestamps.keys())))

def getMyCurrentTime():
    """method to get the elapsed time in seconds from the beginning

    Returns:
        int: Time elapsed from the beginning in seconds
    """
    return int(time.time() - beginTime)


LOCAL_ADDR = '127.0.0.1' # address for the clients
LOCAL_PORT = 15020  # port for the clients

EXTERN_ADDR = socket.gethostname() # address for the peers
EXTERN_PORT = 16020 # port for the peers

SERVICE_TYPE = "_p2pchat._udp.local."
MY_SERVICE_NAME = "Arsh's p2p chatnode"

TIMEOUT_IN_SECONDS = 30 # timeout for the select. This ensures that my node sends ping to all the peers every 30 seconds

PEER_PING_TIMEOUT_IN_SECONDS = 120 # timeout to mark a peer as crashed and remove it from the known list

localsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
localsocket.setblocking(False)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serversocket.setblocking(False)

inputs = [localsocket, serversocket]
outputs = []
peers_with_timestamps = {} # dictionary of known peers
messages_queue = [] # queue of all the messages, both from peers and clients.

beginTime = time.time()

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
version_group = parser.add_mutually_exclusive_group()
version_group.add_argument('--v6', action='store_true')
version_group.add_argument('--v6-only', action='store_true')
args = parser.parse_args()

if args.debug:
    logging.getLogger('zeroconf').setLevel(logging.DEBUG)
if args.v6:
    ip_version = IPVersion.All
elif args.v6_only:
    ip_version = IPVersion.V6Only
else:
    ip_version = IPVersion.V4Only

desc = {}

info = ServiceInfo(
    SERVICE_TYPE,
    "{0} at {1}:{2}.{3}".format(MY_SERVICE_NAME, socket.gethostname(), EXTERN_PORT, SERVICE_TYPE),
    addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
    port=EXTERN_PORT,
    properties=desc,
    server= "{0}.{1}.local.".format(socket.gethostname(), EXTERN_PORT),
)

ip_version = IPVersion.V4Only

zeroconf = Zeroconf(ip_version=ip_version)
listener = MyListener()
browser = ServiceBrowser(zeroconf, SERVICE_TYPE, listener)

zeroconf.register_service(info)

try:
    serversocket.bind((EXTERN_ADDR, EXTERN_PORT))
    localsocket.bind((LOCAL_ADDR, LOCAL_PORT))
    localsocket.listen(5)
    print("Chatnode listening for clients at {0} on port {1}".format(LOCAL_ADDR, LOCAL_PORT))
    print("Chatnode accessible to peer chatnodes at {0} on port {1}\n".format(EXTERN_ADDR, EXTERN_PORT))
    lastPingTime = 0 #the last time I pinged my peers
    
    while inputs:
        sys.stdout.flush()
        try:
            readable, writeable, exceptional = select.select(inputs, outputs, inputs, TIMEOUT_IN_SECONDS)
            
            for s in readable:
                
                if s is localsocket:
                    conn, addr = s.accept()
                    print("New client joined at {0}".format(addr))
                    conn.setblocking(False)
                    inputs.append(conn)
                    outputs.append(conn)
                
                elif s is serversocket:
                    data, addr = s.recvfrom(1024)
                    try:
                        if not addr in peers_with_timestamps.keys():
                            print("Ignoring message from an unknown peer")

                        else:
                            # peer is known. proceed to process the received data
                            recvdJson = json.loads(data.decode().strip())

                            if "command" in recvdJson.keys():
                                
                                if recvdJson["command"].lower() == "ping":
                                    print("Ping received from the peer {0}".format(addr))

                                    # a valid ping received. Updating the peer's last timestamp
                                    peers_with_timestamps[addr][0] = getMyCurrentTime()
                                
                                elif recvdJson["command"].lower() == "msg" and "message" in recvdJson.keys() and "user" in recvdJson.keys():
                                    print("Message from peer {0}: {1}".format(addr, recvdJson))
                                    
                                    # a new valid message from the peer, appending at the end of the messages queue
                                    messages_queue.append("{0}> {1}".format(recvdJson["user"], recvdJson["message"]))    
                    
                    except Exception as e:
                        print("Bad message received from a peer. Ignoring...")
                        print(e)
                        pass
                else:
                    data = s.recv(1024)
                    if data:
                        try:
                            recvdJson = json.loads(data.decode().strip())
                            print("Client {0} sent: {1}".format(s.getpeername(), recvdJson))
                            
                            if "user" in recvdJson.keys() and "message" in recvdJson.keys():
                                
                                # A new valid message received from a client. appending it at the end of the messages queue
                                messages_queue.append("{0}> {1}".format(recvdJson["user"], recvdJson["message"]))
                                
                                # Sending the new message to all known peers as well
                                for peer in peers_with_timestamps.keys(): 
                                    sendMessageToPeer(peer, recvdJson["message"], recvdJson["user"])
                        except:
                            # ignoring any bad data from the client
                            pass
                    else:
                        print("Client {0} closed the connection".format(conn.getpeername()))
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        s.close()

            for s in writeable:
                # Need to send the new message to all the clients
                if len(messages_queue) > 0:
                    ret = s.sendall(messages_queue[0].encode())
                    if ret:
                        print("Failed to send a message to client {0}".format(s))
            
            if len(messages_queue) > 0:
                # first message in queue has been sent to all the clients. remove it from the queue
                messages_queue.remove(messages_queue[0])

            for s in exceptional:
                # problematic socket, removing from inputs and outputs
                if s in inputs:
                    inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                s.close()

            # sending a ping to all known peers
            currTime = getMyCurrentTime()
            if int(currTime - lastPingTime) >= TIMEOUT_IN_SECONDS: # if clause required because writable client sockets unblocks the select statement
                for peer in peers_with_timestamps.keys(): 
                    sendPingToPeer(peer)
                lastPingTime = currTime # ping sent. Updating my last ping time
            
            # removing peers who did not ping me within the given ping timeout (Assuming they are crashed)
            removeUnpingedPeers()

        except KeyboardInterrupt:

            print("\nI guess I have to die now...")
            
            # need to close all input and output sockets nicely so the clients would know that I am gone
            for s in inputs:
                print("closing input {0}".format(s))
                s.close()
            for s in outputs:
                print("closing output {0}".format(s))
                s.close()
            
            # need to close my sockets as well
            localsocket.close()
            serversocket.close()
            zeroconf.close()

            print("Sockets closed successfully")
            print("\nEverything worked out nicely. I can now rest in peace :D\n")
            sys.exit(0)

except Exception as e:
    print("Something bad happened. I am ded :|")
    print(e)
    print(traceback.print_exc(file=sys.stdout, chain=True))

finally:
    localsocket.close()
    serversocket.close()
    zeroconf.close()