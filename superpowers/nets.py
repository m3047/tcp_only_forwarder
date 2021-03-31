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

"""A database which will allow us to efficiently search by address."""

import ipaddress

class Scope(object):
    def __init__(self, powers, scope, mode, fqdn=""):
        self.scope = scope
        self.mode = mode
        self.fqdn = fqdn
        self.powers = powers
        return
    
    def __str__(self):
        return '{} / {} / {}'.format(self.scope, self.mode, self.fqdn or '--')

class Node(object):
    """Encapsulates a single address at all scopes."""
    LT = 0
    GT = 1
    
    def __init__(self, address, *scopes):
        """Each node is comprised of an address at one or more scopes."""
        self.address = address
        self.scopes = sorted(scopes, key=lambda x:x.scope, reverse = True)
        return
    
    def __str__(self):
        result = [ str(scope) for scope in self.scopes ]
        return '\n'.join(result)
    
    @classmethod
    def new(cls, powers, subnet):
        address = int(subnet['net'].network_address)
        mask = subnet['net'].prefixlen
        return Node(address, Scope(powers, mask, subnet['mode'], 'fqdn' in subnet and subnet['fqdn'] or ''))
    
    def add_scope(self, scope):
        """Something with the same address and scope replaces the previous value."""
        for i in range(len(self.scopes)):
            if self.scopes[i].scope == scope.scope:
                self.scopes[i] = scope
                return
        self.scopes.append(scope)
        self.scopes = sorted(self.scopes, key=lambda x:x.scope, reverse=True)
        return
        
    def get_scope(self, bits):
        for scope in self.scopes:
            if scope.scope <= bits:
                return scope
        return None
        
class Nets(object):
    """Encapsulates an entire address space with rewriting rules.
    
    Allows both subnets, and individual addresses or /32.
    """
    def __init__(self, subnets):
        nets = self.nets = dict()
        for net_spec in subnets:
            powers = net_spec['powers']
            for subnet in net_spec['nets']:
                node = Node.new(powers, subnet)
                if node.address in nets:
                    nets[node.address].add_scope(node.scopes[0])
                else:
                    nets[node.address] = node
        return
    
    def __str__(self):
        result = []
        for k in self.nets.keys():
            result.append('Subnet {}:\n{}'.format(ipaddress.ip_address(k), self.nets[k]))        
        return '\n'.join(result)
        
    def find(self, address):
        """Return the effective scope."""
        all_bits = 2**32 - 1
        address = int(address)
        for i in range(32):
            effective_address = address & (all_bits ^ (2**i - 1))
            if effective_address not in self.nets:
                continue
            node = self.nets[effective_address]
            scope = node.get_scope(32-i)
            if scope:
                return scope
        return None

