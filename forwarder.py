#!/usr/bin/python3

import sys
import asyncio

class UDPListener(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        return
    
    async def handle_request(self, request, addr):
        reader, writer = await asyncio.open_connection(self.remote_address, 53)
        # NOTE: When using TCP the request and response are prepended with
        # the length of the request/response.
        writer.write(len(request).to_bytes(2, byteorder='big')+request)
        await writer.drain()
        response_length = await reader.read(2)
        response = await reader.read(int.from_bytes(response_length, byteorder='big'))
        writer.close()
        self.transport.sendto(response, addr)
        return

    def datagram_received(self, request, addr):
        self.event_loop.create_task(self.handle_request(request,addr))
        return

def main():
    try:
        listen_address, remote_address = sys.argv[1:3]
    except:
        print('Usage: forwarder.py <udp-listen-address> <remote-server-address>', file=sys.stderr)
        sys.exit(1)
    event_loop = asyncio.get_event_loop()
    listener = event_loop.create_datagram_endpoint(UDPListener, local_addr=(listen_address, 53))
    try:
        transport, service = event_loop.run_until_complete(listener)
    except PermissionError:
        print('Permission Denied! (are you root?)', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print('{} (did you supply a loopback address?)'.format(e), file=sys.stderr)
        sys.exit(1)
        
    service.remote_address = remote_address
    service.event_loop = event_loop

    try:
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    event_loop.close()

if __name__ == "__main__":
    main()
