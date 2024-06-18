# -*- coding: utf-8 -*-
"""
Created on Mon Jun  6 11:11:03 2024

@author: Rayan
"""

import serial
import serial.tools.list_ports
import time
import os
import fabric

class SerCom:
    def __init__(self, tempfilename="dumplogs.txt"):
        self.ports_List = []
        #List of USB serial ports found at last scan
        self.connection = None
        #USB serial ports successfully connected to
        self.logs = open(tempfilename,"a")
        #Log dump for all devices
        self.readyCheck = "root@mylinkit"
        #check string for end of command execution
        self.NoC = 0
        #Number of connected devices
        self.filename = tempfilename
        self.imei = ""
        self.ip = ""
        self.readPorts()
        self.connectPorts()
        self.ssh = None
        self.com = "Default"

    def __del__(self):
        if self.connection:
            self.connection.close()
        self.logs.close()
        print("Object deleted")
    def readPorts(self):#Scans for usb serial devices
        ports = []
        avails = list(serial.tools.list_ports.comports())
    
        for p in avails:
            if "USB Serial Port" in p.description:
                ports.append(str(p)[:6].rstrip())
        self.ports_List = ports
    def connectPorts(self):#Connects to first unopened port, Should only be called once
        for com in self.ports_List:
            try:
                conn1 = serial.Serial(com, baudrate=57600)
                self.connection = conn1
                print(f"Connected to {com}")
                self.com = str(com[-2:])
                self.ip = "192.168.100."+ self.com
                self.NoC += 1
                break
            except serial.SerialException:
                pass
    def logFiler(self):#Renames default logfile to __IMEI__.txt
        self.logs.close()
        fname = ""
        if self.imei == "":
            fname = "COM"+self.com+".txt"
        else:
            fname = self.imei+".txt"
        try:
            os.rename(self.filename, fname)
        except:
            raise Exception("Device already flashed")
        print("Output File Name: "+fname)
        self.logs = open(fname, "a")
    def runCmd(self, cmdL, waits=10):#Runs the command with enter padding, waits is the maximum number of lines it waits for confirmation of command execution
        cmde = cmdL + "\r\n"
        con = self.connection
        con.write(cmde.encode('utf-8'))
        resp = con.readline().decode('utf-8')
        self.logs.write(resp+"\n")
        print(resp+"\n")
        timeout = waits
        while resp.find(cmdL) == -1 and timeout > 0:
            resp = con.readline().decode('utf-8')
            self.logs.write(resp)
            print(resp+"\n")
            timeout -= 1
        
    
    def Ready(self, test_str='root@mylinkit', waits=20, lfr=True):#Checks if test_str or readyCheck (only if lfr=True) is in output to signify end of output
        con = self.connection
        resp = con.readline().decode('utf-8')
        self.logs.write(resp+"\n")
        print(resp+"\n")
        timeout = waits
        while resp.find(test_str) + resp.find(self.readyCheck) == -2 and timeout > 0:
            resp = con.readline().decode('utf-8')
            self.logs.write(resp+"\n")
            print(resp+"\n")
            timeout -= 1
            
        if timeout == 0:
            print("Timed out")
            return 0
        if resp.find(test_str) == -1:
            return 1#denotes fail
        if lfr:
            while resp.find(self.readyCheck) == -1:
                resp = con.readline().decode('utf-8')
                self.logs.write(resp+"\n")
                print(resp+"\n")
        return 2#denotes success
    def pChange(self):#Changes passwd to root
        self.runCmd("passwd root", waits=1)
        time.sleep(1)
        self.runCmd("root", waits=0)
        time.sleep(1)
        self.runCmd("root", waits=0)
        suc = self.Ready()
        print("Passwd changed to root" if suc == 2 else "password error")
    def start(self):#Reads and connects to all available ports
        self.Ready("nonblocking pool", lfr=False, waits=350)
        print("Attempting newline")
        self.runCmd("#")
        self.Ready(waits=150)
        print("ready")
        time.sleep(2)
        self.logFiler()
        return self
    def getIMEI(self):
        con = self.connection
        self.runCmd("echo 3 > /proc/sys/kernel/printk")
        self.Ready()
        self.runCmd("cp /tmp/run/mountd/sda1/RayanScripts/ImeiRayan.py /tmp")
        self.Ready()
        # self.runCmd("ls /tmp/run/mountd | grep sda1")
        # if self.Ready("sda")  < 2:
        #     raise Exception("PenDrive Not Found")
        self.runCmd("python /tmp/ImeiRayan.py")
        while True:
            resp = con.readline().decode('utf-8')
            self.logs.write(resp+"\n")
            print(resp+"\n")
            x = resp.find("IMEI:")
            if x >= 0:
                imei =  resp[x+6:x+21]
                if imei.isdecimal():
                    self.runCmd("#")
                    self.imei = imei
                    return 0
                else:
                    self.runCmd("#")
                    return 1
            elif resp.find(self.readyCheck) >= 0:
                self.runCmd("#")
                return 2
    def ipGet(self):
        self.runCmd("ifconfig br-lan "+self.ip)
        self.Ready()
        return self.ip
    def ipSet(self): #deprecated
        self.runCmd("ifconfig br-lan "+self.ip)
        self.Ready()
        time.sleep(1)
        self.ssh = fabric.Connection(self.ip, user="root",connect_kwargs={"password":"root"})

        resp = self.ssh.run("python /tmp/run/mountd/sda1/DIO_Test.py").stdout
        self.logs.write(resp)
        flags = []
        flags.append(resp.find("DIO Success"))
        resp = self.ssh.run("python /tmp/run/mountd/sda1/adc_c.py").stdout
        self.logs.write(resp)
        flags.append(resp.find("ADC Current HIGH test PASS"))
        resp = self.ssh.run("python /tmp/run/mountd/sda1/adc_t.py").stdout
        self.logs.write(resp)
        flags.append(resp.find("ADC Temperature test PASS"))
        resp = self.ssh.run("python /tmp/run/mountd/sda1/adc_v.py").stdout
        self.logs.write(resp)
        flags.append(resp.find("ADC Voltage HIGH test PASS"))
        resp = self.ssh.run("python /tmp/run/mountd/sda1/2Way485.py").stdout
        self.logs.write(resp)
        flags.append(resp.find("485 pass"))
        flags = list(map(lambda x: 1 if x >= 0 else False, flags))
        if sum(flags) == 5:
            print("Passed Secondary Testing")
        else:
            print("Failed Secondary")
        print(flags)
    
        
    def rLines(self): #deprecated, do not use
        resp = []
        for i, con in enumerate(self.connections):
            resp.append(con.readline().decode('utf-8'))
            print(resp[-1])
            self.logs[i] += resp[-1]
        