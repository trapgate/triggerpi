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

There are more details about the hardware to use and how to wire things up in
the comments at the top of triggerpi.py. There's no wiring diagram at the
moment.

## Installation
These instructions are a little sparse, and assume a fair amount of Linux
knowledge. They could be improved. The installation process is a matter of
putting two python files into the pi user's home directory, then setting up
systemd to start them at boot time. (If you're using a version of raspbian
that doesn't have systemd, you'll need to use other methods to start the
daemon automatically).

First install a recent build of raspbian on the RaspberryPi, then install the
AutomationHat python module by following the instructions in
https://github.com/pimoroni/automation-hat/README.md. Copy triggerpi.py and
daemon.py to /home/pi on the RaspberryPi, and copy triggerpi.service to
/etc/systemd/system. Finally, run this command to enable the new service:

$ sudo systemctl enable triggerpi.service
