# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 12:55:58 2024

@author: Rayan
"""
#Importing Libraries
import SerComMin
import time
import pandas as pd
import threading
import fabric
import serial.tools.list_ports
from datetime import datetime
from pandasgui import show
import numpy as np
#Loading in Csv Files



df = pd.read_csv(r"FinalCmds.csv")
dfSSH = pd.read_csv(r"SSHCmd.csv")
outputs = {}
#Logging time
startTime = time.time()
#Loading in values from Csv files
__NEWLINE__ = "root@mylinkit"
commands = list(df["Commands"].values)
noC = len(commands)
succ = list(df["Success"].fillna(__NEWLINE__).values.astype(str))
waits= list(df["Waits"].fillna(20).values.astype(int))
lfr = list(df["lfr"].values.astype(bool))
FailMsg = list(df["FailMsg"].fillna("Failed").values.astype(str))
reportF = list(np.invert(df["Report"].values.astype(bool)))



commands_ssh = list(dfSSH["Commands"].values.astype(str))
noC_ssh = len(commands_ssh)
succ_ssh = list(dfSSH["SuccessCheck"].fillna(__NEWLINE__).values.astype(str))
FailMsg_ssh = list(dfSSH["FailMsg"].fillna("Failed").values.astype(str))
reportFSSH = list(np.invert(dfSSH["Report"].values.astype(bool)))


#Function to be run on threads


def Runner(ins: SerComMin.SerCom):
    ins.start()
    polling = []
    print("Started")
    time.sleep(5)
    ins.runCmd("cd /tmp/run/mountd/sda1")
    ins.Ready()
    ins.runCmd("cd")
    ins.Ready()
    flag = False
    for i in range(noC):
        ins.runCmd(commands[i])
        print("Attempted "+commands[i]+"\n")
        time.sleep(0.5)
        repo = ins.Ready(test_str=succ[i], waits=waits[i], lfr=lfr[i])
        if reportF[i]:
            if repo < 2:
                polling.append("Fail")
                flag = True
            else:
                polling.append("Success")
    ins.pChange()
    
    print("Switching to ssh")
    time.sleep(1)
    try:
        sshConn = fabric.Connection(ins.ipGet(), user="root",connect_kwargs={"password":"root"}, hide=True)
        sshConn.run("cd")
    except TimeoutError:
        ins.runCmd("python /tmp/run/mountd/sda1/RayanScripts/flashp3.py")
        ins.logs.write("SSH FAILURE\n")
        return None
    cmd = "python /tmp/run/mountd/sda1/RayanScripts/ImeiRayan.py"
    resp = sshConn.run(cmd).stdout
    ins.logs.write(resp)
    ins.imei = ins.pullInfo("IMEI:", "endl", resp)
    if ins.imei == "DNF":
        polling.append("IMEI Fail")
    else:
        ins.logFiler()
        polling.append("Success")
    iccid_1 = ins.pullInfo("ICCID1:", "endl1", resp)
    if iccid_1 == "DNF":
        polling.append("Fail")
    else:
        polling.append(iccid_1)
    iccid_2 = ins.pullInfo("ICCID2:", "endl2", resp)
    if iccid_2 == "DNF":
        polling.append("Fail")
    else:
        polling.append(iccid_2)
    for i in range(noC_ssh):
        resp = sshConn.run(commands_ssh[i]).stdout
        ins.logs.write(resp)
        if reportFSSH[i]:
            if resp.find(succ_ssh[i]) == -1:
                polling.append("Fail")
            else:
                polling.append("Success")
            
    cmd = "python /tmp/run/mountd/sda1/RayanScripts/RTCR.py " + datetime.today().strftime('%d-%m-%Y-%H-%M-%S-%w')
    resp = sshConn.run(cmd).stdout
    if resp.find("SUCCESS") > -1:
        polling.append("Success")
    else:
        polling.append("Fail")
        flag = True
    ins.logs.write(resp)
    sshConn.run("kill $(ps | grep [f]lash | awk '{print $1}')")
    if flag:
        sshConn.run("python /tmp/run/mountd/sda1/RayanScripts/flashp4.py &")
    else:
        sshConn.run("python /tmp/run/mountd/sda1/RayanScripts/flasher.py 15-0-15-0 &")
    sshConn.close()    
    ins.logs.close()
    finishTime = str(time.time()-startTime)
    polling.append(finishTime)
    outputs[ins.imei] = polling
    print(ins.imei+" done "+finishTime)
    


#Threadmaker
threads = []
instances = []
i = 0
while True:
    ins = SerComMin.SerCom(verbose=False)
    if ins.connection is None:
        del ins
        break
    i += 1
    instances.append(ins)
    thread = threading.Thread(target=Runner, args=(ins,))
    thread.start()
    threads.append(thread)
    
ports = set(instances[-1].ports_List)



print(f"Connected to and executing on {i} devices")
def watchdog():
    while True:
        avails = list(serial.tools.list_ports.comports())
        for p in avails:
            if "USB Serial Port" in p.description:
                port = str(p)[:6].rstrip()
                if not(port in ports):
                    ports.add(port)
                    instances.append(ins)
                    thread = threading.Thread(target=Runner, args=(ins,))
                    thread.start()
                    threads.append(thread)
        time.sleep(5)
                    
watcher = threading.Thread(target=watchdog, daemon=True)

def Results():
    outputs["Commands"] = [commands[i] for i in range(noC) if reportF[i]] + ["Imei", "ICCID1", "ICCID2"] + [commands_ssh[i] for i in range(noC_ssh) if reportFSSH[i]] + ["RTC Check", "Finish Time"]
    res = pd.DataFrame.from_dict(outputs, orient='index')
    res.to_csv(r"Results.csv")
    show(res)
    print("Saved")
    #Insert Reset Code
    
    
