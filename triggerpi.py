#!/usr/bin/env python3
#
# Copyright (c) 2017 Geoff Hickey
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Audio trigger fix for Emotiva XMC-1.
#
# This program is written to run on a RaspberryPi 3 with a Pimoroni
# AutomationHat. The AutomationHat has 3 24V-tolerant inputs and three relays.
# We'll use the relays to control the trigger outputs. Input one will control
# relay 1, input 2 relay 2, etc.
#
# The Emotiva XMC-1) has two different standby modes. When configured to use the
# low-power standby mode, the 12V trigger module doesn't function correctly: it
# powers on with all triggers on, then turns them all off after 20s or so while
# it's booting up, then turns the correct ones on again. So anything connected
# to the triggers turns on, then off, then on again. That's inelegant.
#
# To fix this behavior, this module watches the trigger inputs, and handles the
# input values using a state machine. The state machine expects any trigger to
# go high for a certain amount of time, then low again, then high again. The
# trigger outputs will be turned on the second time an input goes high. When all
# 3 of the trigger inputs turn off, the state machine will assume that the XMC-1
# has been turned off, and it'll go through the powering-on states next time a
# trigger turns on.
#
# This will work as long as at least one of the trigger inputs is turned on once
# the XMC-1 finishes booting. If that's not how you have your triggers set up
# then this won't work as-is.
#
# The wiring I used is pretty simple. For each of the three inputs you'll need
# two 3.5mm mono headphone jacks. I used these:
# https://www.digikey.com/product-detail/en/switchcraft-inc/35PM1/SC1455-ND/1288859
# The pi doesn't have a 12V power supply, so I used voltage from the trigger
# inputs. That does mean that there's no way to keep powering a trigger if the
# XMC-1 has turned off the trigger line, since even if the relay is switched
# there won't be any voltage present. If you wanted to keep the triggers turned
# on after the XMC-1 turned them off, you'd need to use an external voltage
# source.
#
# For each trigger input there are a pair of 3.5mm jacks, one for input and the
# other for output to the connected device. To wire the input jack, connect two
# wires to the tip, which will be 12V when the trigger is on, and two to the
# ring, which is the ground. Run one of the tip wires to an AutomationHat input,
# and the other to one of the relay commons. Then run one of the ground wires to
# one of the AutomationHat ground connections, and the other to the ring
# connection on the other jack. Finally connect the normally open (NO) terminal
# on the relay to the tip connection on the output jack.

# The automationhat python module is provided by pimoroni, and will need to be
# installed before this program will run; instructions are in the project
# README.md file at https://github.com/pimoroni/automation-hat/README.md.
import automationhat
import datetime
from time import sleep

# The time (in seconds) to keep the outputs off while the input is on.
POWERON_HOLD_TIME = 60
# The time between reading the input, in seconds
READ_INTERVAL = 0.2
# The time to wait for the second raising of the input before giving up and
# going back to off.
ARMED_HOLD_TIME = 30


def getInput():
    """
    Read the input signal and return it.

    This reads inputs 1 2 and 3 and returns a tuple of 0 or 1 values, depending
    on the voltage.
    """
    return (automationhat.input.one.read(),
            automationhat.input.two.read(),
            automationhat.input.three.read())


class State:
    def __init__(self):
        # Remember when we got into this state
        self.started = datetime.datetime.now()

    def input(self, input):
        pass


class StateOff(State):
    def __init__(self):
        State.__init__(self)
        # Turn the power LED off
        automationhat.light.power.off()
        automationhat.light.comms.off()
        automationhat.light.warn.off()
        # Turn off all three relays
        automationhat.relay.one.off()
        automationhat.relay.two.off()
        automationhat.relay.three.off()

    def input(self, input):
        # If the input is currently 0 we'll stay off
        if 1 in input:
            # Any input is high. Move to the 'turning_on' state.
            return 'turning_on'
        return ''


class StateTurningOn(State):
    def __init__(self):
        State.__init__(self)
        # Turn the power light on.
        automationhat.light.power.on()
        automationhat.light.comms.on()
        automationhat.light.warn.off()

    def input(self, input):
        # If all inputs are 0 again, the amp is mostly started and has gotten
        # around to initializing the triggers. Go to the armed state.
        if 1 not in input:
            return 'armed'
        # Otherwise, see how long since the input went high, and dim the comms
        # LED as more time elapses.
        elapsed = (datetime.datetime.now() - self.started).total_seconds()
        if elapsed >= POWERON_HOLD_TIME:
            return 'armed'
        pct_elapsed = elapsed / POWERON_HOLD_TIME
        # Don't let the brightness of the comms led go below .01, or it will
        # turn off.
        brightness = max(.01, 1 - pct_elapsed)
        automationhat.light.comms.write(brightness)
        return ''


class StateArmed(State):
    def __init__(self):
        State.__init__(self)
        automationhat.light.power.on()
        automationhat.light.comms.off()
        automationhat.light.warn.on()

    def input(self, input):
        # We stay in this state as long as any input is 1.
        if 1 in input:
            return 'on'
        elapsed = (datetime.datetime.now() - self.started).total_seconds()
        if elapsed >= ARMED_HOLD_TIME:
            return 'off'
        return ''


class StateOn(State):
    def __init__(self):
        State.__init__(self)
        automationhat.light.power.on()
        automationhat.light.comms.off()
        automationhat.light.warn.off()

    def input(self, input):
        if 1 not in input:
            return 'off'
        # Set all three relays to match their inputs.
        if input[0] == 1:
            automationhat.relay.one.on()
        else:
            automationhat.relay.one.off()
        if input[1] == 1:
            automationhat.relay.two.on()
        else:
            automationhat.relay.two.off()
        if input[2] == 1:
            automationhat.relay.three.on()
        else:
            automationhat.relay.three.off()
        return ''


states = {'off': StateOff,
          'turning_on': StateTurningOn,
          'armed': StateArmed,
          'on': StateOn}
current_state = None


def set_state(state):
    """
    Set the current state of the state machine.

    Args:
      state (string): The state to change to. If this is empty or None, then the
                      current state is unchanged.
    """
    global current_state
    if not state:
        return
    current_state = states[state]()


def trigger():
    # Our initial state depends on whether the input is currently low or high.
    # If it's low we'll start in the outputOff state; if it's high jump right to
    # the outputOn state.
    if 1 in getInput():
        set_state('on')
    else:
        set_state('off')

    # Main loop: sleep until it's time to read the input, then pass the input
    # to the current state.
    while(True):
        sleep(READ_INTERVAL)
        i = getInput()
        newstate = current_state.input(i)
        set_state(newstate)


if __name__ == '__main__':
    print('Starting trigger monitor')
    trigger()
