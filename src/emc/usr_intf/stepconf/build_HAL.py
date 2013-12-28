#!/usr/bin/env python
#
#    This is stepconf, a graphical configuration editor for LinuxCNC
#    Copyright 2007 Jeff Epler <jepler@unpythonic.net>
#    stepconf 1.1 revamped by Chris Morley 2014
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#    This builds the HAL files from the collected data.
#
import os
import time
import shutil

class HAL:
    def __init__(self,app):
        # access to:
        self.d = app.d  # collected data
        global SIG
        SIG = app._p    # private data (signal names)
        self.a = app    # The parent, stepconf

    def write_halfile(self, base):
        inputs = set((self.d.pin10,self.d.pin11,self.d.pin12,self.d.pin13,self.d.pin15))
        outputs = set((self.d.pin1, self.d.pin2, self.d.pin3, self.d.pin4, self.d.pin5,
            self.d.pin6, self.d.pin7, self.d.pin8, self.d.pin9, self.d.pin14, self.d.pin16,
            self.d.pin17))

        filename = os.path.join(base, self.d.machinename + ".hal")
        file = open(filename, "w")
        print >>file, _("# Generated by stepconf 1.1 at %s") % time.asctime()
        print >>file, _("# If you make changes to this file, they will be")
        print >>file, _("# overwritten when you run stepconf again")

        print >>file, "loadrt trivkins"
        print >>file, "loadrt [EMCMOT]EMCMOT base_period_nsec=[EMCMOT]BASE_PERIOD servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[TRAJ]AXES"
        print >>file, "loadrt probe_parport"
        port3name=port2name=port2dir=port3dir=""
        if self.d.number_pports>2:
             port3name = self.d.ioaddr3
             if self.d.pp3_direction:
                port3dir =" in"
             else: 
                port3dir =" out"
        if self.d.number_pports>1:
             port2name = self.d.ioaddr2
             if self.d.pp2_direction:
                port2dir =" in"
             else: 
                port2dir =" out"
        print >>file, "loadrt hal_parport cfg=\"%s out %s%s %s%s\"" % (self.d.ioaddr, port2name, port2dir, port3name, port3dir)
        if self.a.doublestep():
            print >>file, "setp parport.0.reset-time %d" % self.d.steptime
        encoder = SIG.PHA in inputs
        counter = SIG.PHB not in inputs
        probe = SIG.PROBE in inputs
        limits_homes = SIG.ALL_LIMIT_HOME in inputs
        pwm = SIG.PWM in outputs
        pump = SIG.PUMP in outputs
        if self.d.axes == 2:
            print >>file, "loadrt stepgen step_type=0,0"
        elif self.d.axes == 1:
            print >>file, "loadrt stepgen step_type=0,0,0,0"
        else:
            print >>file, "loadrt stepgen step_type=0,0,0"

        if encoder:
            print >>file, "loadrt encoder num_chan=1"
        if self.d.pyvcphaltype == 1 and self.d.pyvcpconnect == 1:
            print >>file, "loadrt abs count=1"
            if encoder:
               print >>file, "loadrt scale count=1"
               print >>file, "loadrt lowpass count=1"
               if self.d.usespindleatspeed:
                   print >>file, "loadrt near"
        if pump:
            print >>file, "loadrt charge_pump"
            print >>file, "net estop-out charge-pump.enable iocontrol.0.user-enable-out"
            print >>file, "net charge-pump <= charge-pump.out"

        if limits_homes:
            print >>file, "loadrt lut5"

        if pwm:
            print >>file, "loadrt pwmgen output_type=1"


        if self.d.classicladder:
            print >>file, "loadrt classicladder_rt numPhysInputs=%d numPhysOutputs=%d numS32in=%d numS32out=%d numFloatIn=%d numFloatOut=%d" % (self.d.digitsin , self.d.digitsout , self.d.s32in, self.d.s32out, self.d.floatsin, self.d.floatsout)

        print >>file
        print >>file, "addf parport.0.read base-thread"
        if self.d.number_pports > 1:
            print >>file, "addf parport.1.read base-thread"
        if self.d.number_pports > 2:
            print >>file, "addf parport.2.read base-thread"

        print >>file, "addf stepgen.make-pulses base-thread"
        if encoder: print >>file, "addf encoder.update-counters base-thread"
        if pump: print >>file, "addf charge-pump base-thread"
        if pwm: print >>file, "addf pwmgen.make-pulses base-thread"
        print >>file, "addf parport.0.write base-thread"
        if self.a.doublestep():
            print >>file, "addf parport.0.reset base-thread"
        if self.d.number_pports > 1:
            print >>file, "addf parport.1.write base-thread"
        if self.d.number_pports > 2:
            print >>file, "addf parport.2.write base-thread"
        print >>file
        print >>file, "addf stepgen.capture-position servo-thread"
        if encoder: print >>file, "addf encoder.capture-position servo-thread"
        print >>file, "addf motion-command-handler servo-thread"
        print >>file, "addf motion-controller servo-thread"
        if self.d.classicladder:
            print >>file,"addf classicladder.0.refresh servo-thread"
        print >>file, "addf stepgen.update-freq servo-thread"

        if limits_homes:
            print >>file, "addf lut5.0 servo-thread"

        if pwm: print >>file, "addf pwmgen.update servo-thread"
        if self.d.pyvcphaltype == 1 and self.d.pyvcpconnect == 1:
            print >>file, "addf abs.0 servo-thread"
            if encoder:
               print >>file, "addf scale.0 servo-thread"
               print >>file, "addf lowpass.0 servo-thread"
               if self.d.usespindleatspeed:
                   print >>file, "addf near.0 servo-thread"
        if pwm:
            x1 = self.d.spindlepwm1
            x2 = self.d.spindlepwm2
            y1 = self.d.spindlespeed1
            y2 = self.d.spindlespeed2
            scale = (y2-y1) / (x2-x1)
            offset = x1 - y1 / scale
            print >>file
            print >>file, "net spindle-cmd <= motion.spindle-speed-out => pwmgen.0.value"
            print >>file, "net spindle-on <= motion.spindle-on => pwmgen.0.enable"
            print >>file, "net spindle-pwm <= pwmgen.0.pwm"
            print >>file, "setp pwmgen.0.pwm-freq %s" % self.d.spindlecarrier        
            print >>file, "setp pwmgen.0.scale %s" % scale
            print >>file, "setp pwmgen.0.offset %s" % offset
            print >>file, "setp pwmgen.0.dither-pwm true"
        else: 
            print >>file, "net spindle-cmd <= motion.spindle-speed-out"

        if SIG.ON in outputs and not pwm:
            print >>file, "net spindle-on <= motion.spindle-on"
        if SIG.CW in outputs:
            print >>file, "net spindle-cw <= motion.spindle-forward"
        if SIG.CCW in outputs:
            print >>file, "net spindle-ccw <= motion.spindle-reverse"
        if SIG.BRAKE in outputs:
            print >>file, "net spindle-brake <= motion.spindle-brake"

        if SIG.MIST in outputs:
            print >>file, "net coolant-mist <= iocontrol.0.coolant-mist"

        if SIG.FLOOD in outputs:
            print >>file, "net coolant-flood <= iocontrol.0.coolant-flood"

        if encoder:
            print >>file
            if SIG.PHB not in inputs:
                print >>file, "setp encoder.0.position-scale %f"\
                     % self.d.spindlecpr
                print >>file, "setp encoder.0.counter-mode 1"
            else:
                print >>file, "setp encoder.0.position-scale %f" \
                    % ( 4.0 * int(self.d.spindlecpr))
            print >>file, "net spindle-position encoder.0.position => motion.spindle-revs"
            print >>file, "net spindle-velocity encoder.0.velocity => motion.spindle-speed-in"
            print >>file, "net spindle-index-enable encoder.0.index-enable <=> motion.spindle-index-enable"
            print >>file, "net spindle-phase-a encoder.0.phase-A"
            print >>file, "net spindle-phase-b encoder.0.phase-B"
            print >>file, "net spindle-index encoder.0.phase-Z"


        if probe:
            print >>file
            print >>file, "net probe-in => motion.probe-input"

        for i in range(4):
            dout = "dout-%02d" % i
            if dout in outputs:
                print >>file, "net %s <= motion.digital-out-%02d" % (dout, i)

        for i in range(4):
            din = "din-%02d" % i
            if din in inputs:
                print >>file, "net %s => motion.digital-in-%02d" % (din, i)

        print >>file
        for o in (1,2,3,4,5,6,7,8,9,14,16,17): self.connect_output(file, o)      
        print >>file
            
        print >>file
        for i in (10,11,12,13,15): self.connect_input(file, i)
        print >>file

        if limits_homes:
            print >>file, "setp lut5.0.function 0x10000"
            print >>file, "net all-limit-home => lut5.0.in-4"
            print >>file, "net all-limit <= lut5.0.out"
            if self.d.axes == 2:
                print >>file, "net homing-x <= axis.0.homing => lut5.0.in-0"
                print >>file, "net homing-z <= axis.1.homing => lut5.0.in-1"
            elif self.d.axes == 0:
                print >>file, "net homing-x <= axis.0.homing => lut5.0.in-0"
                print >>file, "net homing-y <= axis.1.homing => lut5.0.in-1"
                print >>file, "net homing-z <= axis.2.homing => lut5.0.in-2"
            elif self.d.axes == 1:
                print >>file, "net homing-x <= axis.0.homing => lut5.0.in-0"
                print >>file, "net homing-y <= axis.1.homing => lut5.0.in-1"
                print >>file, "net homing-z <= axis.2.homing => lut5.0.in-2"
                print >>file, "net homing-a <= axis.3.homing => lut5.0.in-3"


        if self.d.axes == 2:
            self.connect_axis(file, 0, 'x')
            self.connect_axis(file, 1, 'z')
        elif self.d.axes == 0:
            self.connect_axis(file, 0, 'x')
            self.connect_axis(file, 1, 'y')
            self.connect_axis(file, 2, 'z')
        elif self.d.axes == 1:
            self.connect_axis(file, 0, 'x')
            self.connect_axis(file, 1, 'y')
            self.connect_axis(file, 2, 'z')
            self.connect_axis(file, 3, 'a')

        print >>file
        print >>file, "net estop-out <= iocontrol.0.user-enable-out"
        if  self.d.classicladder and self.d.ladderhaltype == 1 and self.d.ladderconnect: # external estop program
            print >>file 
            print >>file, _("# **** Setup for external estop ladder program -START ****")
            print >>file
            print >>file, "net estop-out => classicladder.0.in-00"
            print >>file, "net estop-ext => classicladder.0.in-01"
            print >>file, "net estop-strobe classicladder.0.in-02 <= iocontrol.0.user-request-enable"
            print >>file, "net estop-outcl classicladder.0.out-00 => iocontrol.0.emc-enable-in"
            print >>file
            print >>file, _("# **** Setup for external estop ladder program -END ****")
        elif SIG.ESTOP_IN in inputs:
            print >>file, "net estop-ext => iocontrol.0.emc-enable-in"
        else:
            print >>file, "net estop-out => iocontrol.0.emc-enable-in"

        print >>file
        if self.d.manualtoolchange:
            print >>file, "loadusr -W hal_manualtoolchange"
            print >>file, "net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change"
            print >>file, "net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed"
            print >>file, "net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number"

        else:
            print >>file, "net tool-number <= iocontrol.0.tool-prep-number"
            print >>file, "net tool-change-loopback iocontrol.0.tool-change => iocontrol.0.tool-changed"
        print >>file, "net tool-prepare-loopback iocontrol.0.tool-prepare => iocontrol.0.tool-prepared"
        if self.d.classicladder:
            print >>file
            if self.d.modbus:
                print >>file, _("# Load Classicladder with modbus master included (GUI must run for Modbus)")
                print >>file, "loadusr classicladder --modmaster custom.clp"
            else:
                print >>file, _("# Load Classicladder without GUI (can reload LADDER GUI in AXIS GUI")
                print >>file, "loadusr classicladder --nogui custom.clp"
        if self.d.pyvcp:
            vcp = os.path.join(base, "custompanel.xml")
            if not os.path.exists(vcp):
                f1 = open(vcp, "w")

                print >>f1, "<?xml version='1.0' encoding='UTF-8'?>"

                print >>f1, "<!-- "
                print >>f1, _("Include your PyVCP panel here.\n")
                print >>f1, "-->"
                print >>f1, "<pyvcp>"
                print >>f1, "</pyvcp>"
        if self.d.pyvcp or self.d.customhal:
            custom = os.path.join(base, "custom_postgui.hal")
            if os.path.exists(custom): 
                shutil.copy( custom,os.path.join(base,"postgui_backup.hal") ) 
            f1 = open(custom, "w")
            print >>f1, _("# Include your customized HAL commands here")
            print >>f1, _("# The commands in this file are run after the AXIS GUI (including PyVCP panel) starts") 
            print >>f1
            if self.d.pyvcphaltype == 1 and self.d.pyvcpconnect: # spindle speed/tool # display
                  print >>f1, _("# **** Setup of spindle speed display using pyvcp -START ****")
                  if encoder:
                      print >>f1, _("# **** Use ACTUAL spindle velocity from spindle encoder")
                      print >>f1, _("# **** spindle-velocity bounces around so we filter it with lowpass")
                      print >>f1, _("# **** spindle-velocity is signed so we use absolute component to remove sign") 
                      print >>f1, _("# **** ACTUAL velocity is in RPS not RPM so we scale it.")
                      print >>f1
                      print >>f1, ("setp scale.0.gain 60")
                      print >>f1, ("setp lowpass.0.gain %f")% self.d.spindlefiltergain
                      print >>f1, ("net spindle-velocity => lowpass.0.in")
                      print >>f1, ("net spindle-fb-filtered-rps      lowpass.0.out  => abs.0.in")
                      print >>f1, ("net spindle-fb-filtered-abs-rps  abs.0.out      => scale.0.in")
                      print >>f1, ("net spindle-fb-filtered-abs-rpm  scale.0.out    => pyvcp.spindle-speed")
                      print >>f1
                      print >>f1, _("# **** set up spindle at speed indicator ****")
                      if self.d.usespindleatspeed:
                          print >>f1
                          print >>f1, ("net spindle-cmd            =>  near.0.in1")
                          print >>f1, ("net spindle-velocity       =>  near.0.in2")
                          print >>f1, ("net spindle-at-speed       <=  near.0.out")
                          print >>f1, ("setp near.0.scale %f")% self.d.spindlenearscale
                      else:
                          print >>f1, ("# **** force spindle at speed indicator true because we chose no feedback ****")
                          print >>f1
                          print >>f1, ("sets spindle-at-speed true")
                      print >>f1, ("net spindle-at-speed       => pyvcp.spindle-at-speed-led")
                  else:
                      print >>f1, _("# **** Use COMMANDED spindle velocity from LinuxCNC because no spindle encoder was specified")
                      print >>f1, _("# **** COMANDED velocity is signed so we use absolute component (abs.0) to remove sign")
                      print >>f1
                      print >>f1, ("net spindle-cmd => abs.0.in")
                      print >>f1, ("net absolute-spindle-vel <= abs.0.out => pyvcp.spindle-speed")
                      print >>f1
                      print >>f1, ("# **** force spindle at speed indicator true because we have no feedback ****")
                      print >>f1
                      print >>f1, ("net spindle-at-speed => pyvcp.spindle-at-speed-led")
                      print >>f1, ("sets spindle-at-speed true")

        if self.d.customhal or self.d.classicladder or self.d.halui:
            custom = os.path.join(base, "custom.hal")
            if not os.path.exists(custom):
                f1 = open(custom, "w")
                print >>f1, _("# Include your customized HAL commands here")
                print >>f1, _("# This file will not be overwritten when you run stepconf again") 
        file.close()
        self.d.add_md5sum(filename)

#******************
# HELPER FUNCTIONS
#******************

    def connect_axis(self, file, num, let):
        axnum = "xyza".index(let)
        lat = self.d.latency
        print >>file
        print >>file, "setp stepgen.%d.position-scale [AXIS_%d]SCALE" % (num, axnum)
        print >>file, "setp stepgen.%d.steplen 1" % num
        if self.a.doublestep():
            print >>file, "setp stepgen.%d.stepspace 0" % num
        else:
            print >>file, "setp stepgen.%d.stepspace 1" % num
        print >>file, "setp stepgen.%d.dirhold %d" % (num, self.d.dirhold + lat)
        print >>file, "setp stepgen.%d.dirsetup %d" % (num, self.d.dirsetup + lat)
        print >>file, "setp stepgen.%d.maxaccel [AXIS_%d]STEPGEN_MAXACCEL" % (num, axnum)
        print >>file, "net %spos-cmd axis.%d.motor-pos-cmd => stepgen.%d.position-cmd" % (let, axnum, num)
        print >>file, "net %spos-fb stepgen.%d.position-fb => axis.%d.motor-pos-fb" % (let, num, axnum)
        print >>file, "net %sstep <= stepgen.%d.step" % (let, num)
        print >>file, "net %sdir <= stepgen.%d.dir" % (let, num)
        print >>file, "net %senable axis.%d.amp-enable-out => stepgen.%d.enable" % (let, axnum, num)
        homesig = self.a.home_sig(let)
        if homesig:
            print >>file, "net %s => axis.%d.home-sw-in" % (homesig, axnum)
        min_limsig = self.min_lim_sig(let)
        if min_limsig:
            print >>file, "net %s => axis.%d.neg-lim-sw-in" % (min_limsig, axnum)
        max_limsig = self.max_lim_sig(let)
        if max_limsig:
            print >>file, "net %s => axis.%d.pos-lim-sw-in" % (max_limsig, axnum)

    def connect_input(self, file, num):
        p = self.d['pin%d' % num]
        i = self.d['pin%dinv' % num]
        if p == SIG.UNUSED_INPUT: return

        if i:
            print >>file, "net %s <= parport.0.pin-%02d-in-not" \
                % (p, num)
        else:
            print >>file, "net %s <= parport.0.pin-%02d-in" \
                % (p, num)

    def find_input(self, input):
        inputs = set((10, 11, 12, 13, 15))
        for i in inputs:
            pin = getattr(self.d, "pin%d" % i)
            inv = getattr(self.d, "pin%dinv" % i)
            if pin == input: return i
        return None

    def find_output(self, output):
        outputs = set((1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 16, 17))
        for i in outputs:
            pin = self.d["pin%d" % i]
            inv = self.d["pin%dinv" % i]
            if pin == output: return i
        return None

    def connect_output(self, file, num):
        p = self.d['pin%d' % num]
        i = self.d['pin%dinv' % num]
        if p == SIG.UNUSED_OUTPUT: return
        if i: print >>file, "setp parport.0.pin-%02d-out-invert 1" % num
        print >>file, "net %s => parport.0.pin-%02d-out" % (p, num)
        if self.a.doublestep():
            if p in (SIG.XSTEP, SIG.YSTEP, SIG.ZSTEP, SIG.ASTEP):
                print >>file, "setp parport.0.pin-%02d-out-reset 1" % num

    def min_lim_sig(self, axis):
        inputs = set((self.d.pin10,self.d.pin11,self.d.pin12,self.d.pin13,self.d.pin15))
        thisaxisminlimits = set((SIG.ALL_LIMIT, SIG.ALL_LIMIT_HOME, "min-" + axis, "min-home-" + axis,
                               "both-" + axis, "both-home-" + axis))
        for i in inputs:
            if i in thisaxisminlimits:
                if i==SIG.ALL_LIMIT_HOME:
                    # ALL_LIMIT is reused here as filtered signal
                    return SIG.ALL_LIMIT
                else:
                    return i

    def max_lim_sig(self, axis):
        inputs = set((self.d.pin10,self.d.pin11,self.d.pin12,self.d.pin13,self.d.pin15))
        thisaxismaxlimits = set((SIG.ALL_LIMIT, SIG.ALL_LIMIT_HOME, "max-" + axis, "max-home-" + axis,
                               "both-" + axis, "both-home-" + axis))
        for i in inputs:
            if i in thisaxismaxlimits:
                if i==SIG.ALL_LIMIT_HOME:
                    # ALL_LIMIT is reused here as filtered signal
                    return SIG.ALL_LIMIT
                else:
                    return i
    # Boiler code
    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)
