import socket


def player(conn, addr):
    print('Connected ', addr)

    # ? Server Side Relay Protocol Description:
    # ? Max Buffer Size: 256
    # ? [1 Byte (Index of Client that sent message)] | [0 - 255 Bytes (Payload)]

    while True:  # ? This merely relays client messages to each other
        try:
            data = conn.recv(256)
        except:
            break
        if not data:
            break
        for client in clients.values():
            if client[0] != conn:
                try:
                    client[0].send(bytes([client[1]]) + data)
                except:
                    clients.pop(client[0].getsockname(), None)


# * Note to self:
# * In the multiplayer mode, player ids are associated with the order they joined in
# * Ex. Player 0, Player 1, Player 2...

print("Address to host on")
addr = input(" > ")

# ? Here, the person hosting should actually insert the address of the interface they're using or the one that's currently connected to the network (ie. Wifi address is usually 192.168.1.0/8 etc...)
# ? Likewise if you're hosting a LAN party and you have one ethernet interface connected to a switch you'd want to use that ethernet interface's address instead of wifi address
# ? On windows you can find the address by running "ipconfig" in command prompt and checking for ipv4 (avoid 127.0.0.1)/ipv6 (avoid ::1) addresses under the interface you wish to use (Be careful not use addresses under "subnet mask (this is not an address)" or "default gateway (this is usually your router's address)")

print("Specify port to host on")
port = int(input(" > "))

running = True
clients = {}
index = 0

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((addr, port))
print(f"Listening to connections on port {port}")
while running:
    try:
        b, addr = s.recvfrom(256)
    except:
        b = b''

    if clients.get(addr) == None:
        clients[addr] = index
        index += 1

    for client in clients.keys():
        if addr != client:
            s.sendto(bytes([index]) + b, client)
