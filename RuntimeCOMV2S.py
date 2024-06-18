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
#Loading in Csv Files
df = pd.read_csv(r"SerComCmds.csv")
dfSSH = pd.read_csv(r"SSHCmds.csv")
#Logging time
startTime = time.time()
#Loading in values from Csv files
commands = list(df["Commands"].values)
noC = len(commands)
succ = list(df["Success"].fillna("root@mylinkit").values.astype(str))
waits= list(df["Waits"].fillna(20).values.astype(int))
lfr = list(df["lfr"].fillna(True).values.astype(bool))
FailMsg = list(df["FailMsg"].fillna("Failed").values.astype(str))



commands_ssh = list(dfSSH["Commands"].values.astype(str))
noC_ssh = len(commands_ssh)
succ_ssh = list(dfSSH["SuccessCheck"].fillna("root@mylinkit").values.astype(str))
FailMsg_ssh = list(dfSSH["FailMsg"].fillna("Failed").values.astype(str))


#Function to be run on threads


def Runner(ins: SerComMin.SerCom):
    ins.start()
    print("Started")
    file = open("LogsNew.txt", "a")
    time.sleep(5)
    ins.runCmd("cd /tmp/run/mountd/sda1")
    ins.Ready()
    ins.runCmd("cd")
    ins.Ready()
    for i in range(2, noC):
        ins.runCmd(commands[i])
        file.write("Attempted "+commands[i]+"\t")
        print("Attempted "+commands[i]+"\n")
        time.sleep(0.5)
        repo = ins.Ready(test_str=succ[i], waits=waits[i], lfr=lfr[i])
        if repo < 2:
            file.write(FailMsg[i]+"\n")
        else:
            file.write("Successfully executed \n")
    ins.getIMEI()
    ins.logFiler()
    ins.pChange()
    print("Switching to ssh")
    sshConn = fabric.Connection(ins.ipGet(), user="root",connect_kwargs={"password":"root"})
    file.write("SSH connected")
    for i in range(noC_ssh):
        file.write("Attempting "+commands[i]+"\t")
        resp = sshConn.run(commands_ssh[i]).stdout
        ins.logs.write(resp)
        if resp.find(succ_ssh[i]) == -1:
            file.write(FailMsg_ssh[i]+"\n")
        else:
            file.write("Successfully executed \n")
        
    sshConn.close()    
    file.close()
    print(ins.imei+" done "+str(time.time()-startTime))
    


#Threadmaker
threads = []
instances = []
i = 0
while True:
    ins = SerComMin.SerCom(f"TesterFile{i}.txt")
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

    





