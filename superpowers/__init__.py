#!/usr/bin/python3
"""Superpowers Core

Configurations
--------------

The configuration is defined in a YAML file. There are two parts to the
configuration file:

* params -- parameters required to configure various superpowers
* subnets -- definitions of powers+subnets

Params in the configuration file is a dictionary of dictionaries, where
each enabled power has its own dictionary of parameters. See the documentation
for a specific superpower for information on the configuration parameters
it requires / accepts.

Parameters are represented in the Config object via the params(power) method
which returns the dictionary of parameters for the supplied power.

Subnets represents a list of mappings of powers to subnets. The list of
mappings is processed in order to provide a mapping from an IP address to
the rewriting methods (powers) which will be applied to it.

Anything declared later at the same address/scope supersedes what was
previously declared for that address/scope. It is possible to have multiple
(nested) scopes at the same address, for instance 10.0.0.0/8 and 10.0.0.0/24
or even 10.0.0.0/32. An address without a cidr is treated as a /32. The
processing rules for the innermost applicable scope are applied whenever
address/scopes overlap.

Nets are declared as lists. A given net has three components:

* net:  The network or address representing the subnetwork.
* mode: first / last / always / never. Explained below.
* fqdn: Fallback rewriting FQDN.

It can also be specified as a line (string) containing those three, untagged,
items in sequential order.

Powers provide special-purpose rewriting, but a subnet declaration lets you
hard code a value to be used if none of the powers applies as the third
(fqdn) component.

Powers can be applied in one of four modes:

* first:    The powers are applied before the normal PTR lookup is attempted.
* last:     The powers are applied after the normal PTR lookup is attempted.
* always:   The powers are always applied, normal PTR lookup does not occur.
* never:    The powers are never applied, only normal PTR lookup is attempted.

In all of the cases above, the first "hit" stops further processing.

It is possible to leave the powers of a mapping empty to obtain just the
default explicit rewritings specified with the subnets.
"""

import yaml
import ipaddress
import dns.message
import importlib

from .nets import Nets

# TODO: Need something in here to enumerate the superpowers within this directory.

CONFIG_FILE = 'superpowers.yaml'
RECOGNIZED_POWERS = { 'sqlite', 'shodohflo' }
REQUIRED_NET_SPEC_KEYS = { 'net', 'mode' }

PTR = 12

class Superpower(object):
    """Base class for superpowers."""
    def query(self, address):
        """Use the superpower to attempt to resolve address."""
        raise NotImplementedError()

class InvalidConfiguration(AttributeError):
    """Raised when the configuration is invalid for structural reasons."""
    pass

class Powers(object):
    """Encapsulates the notion that the DNS request is tractable to powers."""
    def __init__(self, config, request):
        self.query = dns.message.from_wire(request)
        # Request type has to be PTR.
        if self.query.question[0].rdtype != PTR:
            self.powers = None
            return
        address = ipaddress.ip_address(
            '.'.join(( x for x in reversed(self.query.question[0].name.to_text().replace('.in-addr.arpa.','').split('.')) ))
            )
        self.scope = config.nets.find(address)
        if self.scope is not None:
            self.powers = [config.powers[pwr] for pwr in self.scope.powers or []]
        else:
            self.powers = None
        return

    def __call__(self):
        """Returns true if the request potentially has an answer.
        
        Basically this means a PTR record, as it's possible for self.powers
        to be empty, in the case of subnets specified with no powers solely
        in order to use the fallback rewriting behavior.
        """
        return self.powers is not None
    
    @property
    def mode(self):
        return self.scope.mode
    
    @property
    def fqdn(self):
        return self.scope.fqdn.endswith('.') and self.scope.fqdn or self.scope.fqdn+'.'
    
    def exec(self):
        """Run the powers and see if they return something useful."""
        for power in self.powers:
            self.response = power.query(address)
            if self.response:
                return True
        return False

class Config(object):
    POSSIBLE_PARAMS = { 'sqlite', 'shodohflo' }

    def __init__(self, yaml_config):
        """Takes a (preprocessed) YAML config as the argument.
        
        The config is kept intact in its original format, and individual properties
        retrieve items of interest.
        """
        self.config = yaml_config
        self.nets_ = None
        self.powers = dict()
        return
    
    def params(self, power, default=None):
        """Return the configuration parameters for a power.
        
        If the power is not found in the list for which parameters are available,
        the value of default (by default None) is return.
        """
        if power not in self.POSSIBLE_PARAMS:
            raise KeyError("{} is not a recognized power.".format(power))
        params = self.config['params']
        return power in params and params[power] or default
    
    def load_powers(self):
        """Load any powers used by the compiled nets object."""
        for subnet in self.config['subnets']:
            if subnet['powers'] is None:
                continue
            modules = []
            for pwr in subnet['powers']:
                if pwr not in self.powers:
                    self.powers[pwr] = importlib.import_module(self.__module__ + '.' + pwr).Superpower()
                modules.append(self.powers[pwr])
            subnet['powers'] = modules
        return
        
    @property
    def nets(self):
        """Returns a compiled Nets object."""
        if self.nets_ is None:
            self.load_powers()
            self.nets_ = Nets(self.config['subnets'])
        return self.nets_
    
def load_config(config=CONFIG_FILE):
    with open(config) as cf:
        config = yaml.safe_load(cf)

    # Validate the specific parameters which have to occur.

    if not 'params' in config:
        raise InvalidConfiguration("No params section.")
    params = config['params']
    if type(params) is not dict:
        raise InvalidConfiguration("Params needs to be a dict.")
    if 'sqlite' in params and 'db' not in params['sqlite']:
        raise InvalidConfiguration("'sqlite' does not contain 'db'.")
    if 'shodohflo' in params and 'redis_server' not in params['shodohflo']:
        raise InvalidConfiguration("'shodohflo' does not contain 'redis_server'.")

    if not 'subnets' in config:
        raise InvalidConfiguration("No nets section.")
    subnets = config['subnets']
    if type(subnets) is not list:
        raise("Subnets needs to be a list of nets.")
    subnet = 0
    
    # Individual subnets...

    for net_spec in subnets:
        subnet += 1
        if 'powers' not in net_spec or (net_spec['powers'] is not None and type(net_spec['powers']) is not list):
            raise InvalidConfiguration('Subnet {}: missing "powers".'.format(subnet))
        if net_spec['powers'] is not None and not set(net_spec['powers']) <= RECOGNIZED_POWERS:
            raise InvalidConfiguration("Subnet {}: '{}' contains an unrecognized power.".format(subnet,net_spec['powers']))
        if 'nets' not in net_spec or type(net_spec['nets']) is not list:
            raise InvalidConfiguration('Subnet {}: missing "nets".'.format(subnet))

        specs = []
        for net in net_spec['nets']:
            # These can either be in a map format or a textual format which we will parse.
            if type(net) is str:
                fields = net.split()
                if len(fields) < 2 or len(fields) > 3:
                    raise InvalidConfiguration("Subnet {}: net spec is 'net mode [fqdn]': {}".format(subnet, net))
                net = { 'net':fields[0], 'mode':fields[1] }
                if len(fields) == 3:
                    net['fqdn'] = fields[2]
            if type(net) is dict:
                if not set(net.keys()) >= REQUIRED_NET_SPEC_KEYS:
                    raise InvalidConfiguration("Subnet {}: net spec doesn't contain 'net' and 'mode'".format(subnet))
                try:
                    net['net'] = ipaddress.ip_network(net['net'])
                except ValueError:
                    raise InvalidConfiguration("Subnet {}: net spec contains an invalid network '{}'".format(subnet, net['net']))
            else:
                raise InvalidConfiguration("Subnet {} contains an invalid net spec: '{}'".format(subnet, net))
            
            specs.append(net)
        net_spec['nets'] = specs
    
    return config
        

