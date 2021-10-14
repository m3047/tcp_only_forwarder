#!/usr/bin/python3
# Copyright (c) 2020 by Fred Morris Tacoma WA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TCP-only DNS Forwarder.

Please read the README. Usage:

    forwarder.py {--tls} <loopback-address> <dns-server-address> &
    
The above will run the script in the background. dns-server-address should be one of your
configured local caching resolvers (I don't recommend 8.8.8.8).

After running the script edit your network settings and change your resolver to loopback-address.

loopback-address will typically be 127.0.0.1 for IP4 or ::1 for IP6.

Specifying "--tls" establishes the connection with TLS, contacting the server on
port 853. (Also known as "DoT".)
"""

import sys
import asyncio
import ssl

class UDPListener(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        return
    
    async def handle_request(self, request, addr):
        reader, writer = await asyncio.open_connection(self.remote_address, self.ssl and 853 or 53, ssl=self.ssl)
        # NOTE: When using TCP the request and response are prepended with
        # the length of the request/response.
        writer.write(len(request).to_bytes(2, byteorder='big')+request)
        await writer.drain()
        response_length = int.from_bytes(await reader.read(2), byteorder='big')
        response = b''
        while response_length:
            resp = await reader.read(response_length)
            if not len(resp):
                break
            response += resp
            response_length -= len(resp)
        writer.close()
        self.transport.sendto(response, addr)
        return

    def datagram_received(self, request, addr):
        self.event_loop.create_task(self.handle_request(request,addr))
        return

def main():
    try:
        tls = sys.argv[1] == '--tls'
        if tls:
            listen_address, remote_address = sys.argv[2:4]
        else:
            listen_address, remote_address = sys.argv[1:3]
    except:
        print('Usage: forwarder.py {--tls} <udp-listen-address> <remote-server-address>', file=sys.stderr)
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
    if tls:
        service.ssl = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    else:
        service.ssl = None

    try:
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    event_loop.close()

if __name__ == "__main__":
    main()
