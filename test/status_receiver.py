import socket
import threading

import google

from rally.common.status_information import StatusInformation
from rally.protocol import clientprotocol_pb2


class StatusReceiver(threading.Thread):
    def __init__(self, connection, positition_receiver):
        threading.Thread.__init__(self)
        self.terminate = False
        self.connection = connection
        self.positition_receiver = positition_receiver
        self.status_information = StatusInformation()

    def stop(self):
        self.terminate = True

    def run(self):
        while not self.terminate:
            success, size_bytes = self._receive_data(4)
            if not success:
                break
            size = int.from_bytes(size_bytes[0:4], "big")
            if size <= 0:
                print("Error in communications, size: {0}".format(size))
                break

            success, data = self._receive_data(size)
            if not success:
                print("Unknown communications error: {0}".format(data))
                break

            try:
                server_to_client = clientprotocol_pb2.ServerToClient()
                unpack_result = server_to_client.ParseFromString(data)
                if unpack_result > 0:
                    if server_to_client.HasField("status_update"):
                        su_message = server_to_client.status_update
                        self.status_information.update_status(su_message)
                        self.positition_receiver(self.status_information)
                else:
                    print("Unable to unpack message, quitting to be sure")
                    # Possibly loosing something now
                    break
            except google.protobuf.message.DecodeError as e:
                print("Incorrect message: {0}".format(e))
                break
            except Exception as e:
                print("Unknown error in communication {0}".format(e))
                break

    def _receive_data(self, size):
        while not self.terminate:
            try:
                data = bytearray()
                while len(data) < size:
                    tmp = self.connection.recv(size-len(data))
                    if not tmp:
                        print("No data received -> lost the connection")
                        # Lost the connection
                        return False, None
                    data.extend(tmp)
                return True, bytes(data)
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError):
                print("Lost the connection")
                return False, None
            except Exception as e:
                print("ERROR! Unknown exception when receiving data: {0}".format(e))
                return False, e
        return False, None
