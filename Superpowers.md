# Superpowers!

**STATUS: Very very alpha**

There are all kinds of systemly utilities which helpfully try reverse DNS lookup on addresses. It's useless;
I'm always using `-n`. `netstat -n`, `iptables -n`, you get the idea.

Let's try to fix PTR lookups!

How do we do that? BY RETURNING USEFUL INFORMATION! Seems kinda obvious to me...

_Superpowers_ refers to the ability to read minds and bend spoons (coming soon!).

But until then I have the basics. You can create defaults which will be returned if the normal PTR lookup
fails; I explain below.

`superpowers.py` runs just like `forwarder.py` except that it has a `superpowers.yaml` config file where
you can take control of PTR lookups.

### Configuring `superpowers.yaml`

The `params` section probably gives the plot away in terms of what superpowers are planned. ;-) Leave it alone
for now. What you can configure today is the `subnets` section. `pydoc3 superpowers` should give you the
complete documentation.

Leave the `powers:` empty (for now). Although an example is provided with the three keys, you can simple
specify nets as a subnet + mode + default string. Since there is no other reason to define things in here,
you don't need to worry about entries without an _fqdn_.

Furthermore, because there are no powers just leave the _mode_ as `last`. Just define some subnets and fqdn-like
strings.

Then run `superpowers.py` and configure it as your local resolver. If you want it test it without changing your
configuration, then use something like `dig @127.0.0.1 -x 10.0.0.22` to see what's happening.

### Security Issues / Side Effects

Some programs use or allow the use of DNS names for access control. (This is not really good security, especially without DNSSEC.)

If the program performs a forward lookup of the DNS name and uses the ip address for comparison, all is good.
If however the program performs a reverse lookup of the connecting address and compares the returned fqdn
against the configured value, _superpowers_ can most definitely interfere.
