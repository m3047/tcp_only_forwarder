#!/usr/bin/python3
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
    

