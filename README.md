# TCP-Only Forwarder

I posted an _Ask HN_ about this and it dropped like a lead zeppelin. So this is actual working code to prove the point.

### Are DNS over HTTP(s) (DoH) and DNS over TLS (DoT) faster because they use TCP?

DNS experts, including yours truly, generally believe that DNS over TCP will not perform as well as DNS over UDP.
But some people assert that DoH/DoT perform better for them.

In these COVID times I've had ample opportunity to study DNS performance in my SOHO network(s). This includes some
crappy WiFi APs and several media devices (Rokus, Kindles). I've also been playing with 802.11. TLDR: media devices cheat.
Ha ha ha. Bet you're really surprised!

What I've discovered is that my wirelessly connected OSX laptop suffers from DNS resolution problems when the media devices
are running. I don't think it's entirely the media devices' fault, but yeah they cheat.

But here's the thing about DNS: although DNS servers _MUST_ support TCP, the stub resolvers on your typical well-behaved
device (laptop) will not try TCP opportunistically. In other words they don't try TCP unless they receive a UDP response
to a query with `TC=1`. So if they never receive a response to a UDP query, they never try it!

What I discovered was that when DNS was failing

    dig foo.bar

would also fail, but

    dig foo.bar +tcp

would succeed. Usually startlingly fast!

##### my question

So my question to you is this: is it about time that _Apple_ and _Microsoft_ considered making DNS with TCP opportunistic, or
in other words if UDP fails their stub resolvers try TCP?

Please leave your experiences and thoughts in the feedback issue.

### Usage

I assume that you're running a local caching resolver, and not using `8.8.8.8`. I don't know how that will work, I haven't
tried it and I'm not likely to. If you're worried about _privacy_ then DoT/H should be your go-to (I recommend DoT).

This requires `python3`. If `python3` lives in `/usr/bin/` then yay! Otherwise:

    python3 ./forwarder.py 127.0.0.1 <one-of-your-actual-resolvers> &

Once you've done that, edit your network settings to refer to `127.0.0.1`. It should work with IP6 too, although I haven't
tried it.
