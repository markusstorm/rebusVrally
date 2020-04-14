
# def int_to_bytes(x: int) -> bytes:
#     return x.to_bytes((x.bit_length() + 7) // 8, 'big')
#
# def int_from_bytes(xbytes: bytes) -> int:
#     return int.from_bytes(xbytes, 'big')

def protobuf_send(connection, message):
    try:
        data = message.SerializeToString()
        size = len(data)
        connection.sendall(size.to_bytes(4, "big") + data)
        #connection.sendall(data)
        return True
    except:
        return False

def protobuf_sendto(socket, dest_port, message):
    # try:
    data = message.SerializeToString()
    size = len(data)
    socket.sendto(size.to_bytes(4, "big") + data, ("127.0.0.1", dest_port))
    return True
    # except:
    #     return False


# def protobuf_unpack(buffer, target_proto):
#     if len(buffer) < 4:
#         return len(buffer) - 4, buffer
#
#     size = int.from_bytes(buffer[0:4], "big")
#     print("Received message of {0} bytes".format(size))
#     if len(buffer) < 4 + size:
#         return len(buffer) - 4 - size, buffer
#     data = buffer[4:4+size]
#     buffer = buffer[4+size:]
#     try:
#         unpack_result = target_proto.ParseFromString(data)
#         return unpack_result, buffer
#     except:
#         return 0, buffer
