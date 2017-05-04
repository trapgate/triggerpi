# triggerpi
Fix the behavior of the Emotiva XMC-1's 12V triggers using a RaspberryPi and a
Pimoroni AutomationHat.

## Details
The Emotiva XMC-1 (an AV pre-amp/signal processor) powers on from low-power
standby with all its 12V triggers turned on. After 20s or so, it gets around to
initializing the trigger board, at which point it turns them all off again.
Several seconds later it turns the right triggers on.

This means that anything connected to those triggers turns on, then off, then on
again, which is a little annoying. Triggers should behave better than this.

This program fixes the problem with a small state machine that delays turning on
the outputs until the second rising of the trigger signal. There are also
timeouts built in so that if a trigger goes high and stays that way the outputs
will still eventually turn on.

There are only three relays on the AutomationHat, so this only works for 3 of
the 4 12V triggers on the XMC-1.
