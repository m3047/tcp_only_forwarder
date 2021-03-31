#!/usr/bin/python3
# Copyright (c) 2021 by Fred Morris Tacoma WA
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

"""TCP Only DNS Forwarder with Superpowers

"Superpowers" refers to the ability to intercept and rewrite PTR queries as are
typically performed by default by the many tools I use which I commonly postscript
with "-n": arp, route, netstat, iptables....

Configuration is loaded from configuration.yaml. See "pydoc3 superpowers" for further
information on configuration file format.
"""

import asyncio

import dns.message
import dns.rrset
import dns.rcode

import forwarder
from forwarder import UDPListener
from superpowers import *

TTL = 60

class SuperUDPListener(UDPListener):
    """Here's where we get our superpowers by intermediating PTR requests."""
    
    def connection_made(self, transport):
        self.config = Config(load_config())
        UDPListener.connection_made(self, transport)
        return

    async def handle_request(self, request, addr):
        powers = Powers(self.config, request)

        # first / last / always / never is sorted out here.
        if powers() and powers.mode in ('first', 'always'):
            if powers.exec():
                self.transport.sendto(powers.response, addr)
                return
        if not powers() or powers.mode != 'always':
            reader, writer = await asyncio.open_connection(self.remote_address, self.ssl and 853 or 53, ssl=self.ssl)
            # NOTE: When using TCP the request and response are prepended with
            # the length of the request/response.
            writer.write(len(request).to_bytes(2, byteorder='big')+request)
            await writer.drain()
            response_length = await reader.read(2)
            response = await reader.read(int.from_bytes(response_length, byteorder='big'))
            writer.close()
            dns_response = dns.message.from_wire(response)
            if dns_response.rcode() == 0 or powers.mode == 'never':
                self.transport.sendto(response, addr)
                return
        if powers() and powers.mode == 'last':
            if powers.exec():
                self.transport.sendto(powers.response, addr)
                return
        
        # If we're still hanging around then use the fallback value.
        if powers() and powers.fqdn:
            dns_response = dns.message.make_response(powers.query, recursion_available=True)
            dns_response.answer.append( dns.rrset.from_text_list( dns_response.question[0].name, TTL, 'IN', 'PTR', [ powers.fqdn ] ))
            self.transport.sendto(dns_response.to_wire(), addr)
            return
        
        # If we're still here, return NXDOMAIN.
        dns_response = dns.message.make_response(powers.query, recursion_available=True)
        dns_response.set_rcode(dns.rcode.NXDOMAIN)
        self.transport.sendto(dns_response.to_wire(), addr)

        return
    
if __name__ == '__main__':
    forwarder.UDPListener = SuperUDPListener
    forwarder.main()
    

