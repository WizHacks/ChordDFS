from datetime import datetime
import os
import sys
import re

class MyLogger():
    def __init__(self, ip, chord_id, log_file_path, client=False):     
        self.ip = ip   
        self.chord_id = chord_id
        self.log_file_path = log_file_path
        self.client = client

    # Print that will show up in mininet output and get added to log file
    def mnPrint(self, msg):
        if self.client:
            # Format msg
            msg = "<{0}_c>: {1}".format(self.ip, msg)
        else:
            # Format msg
            msg = "<{0}, {1}>: {2}".format(self.ip, self.chord_id, msg)

        # Print msg to stdout
        print(msg)
        sys.stdout.flush() # need to flush output, else never show up

        # Write msg to log file        
        with open(self.log_file_path, "a") as logFile:
            logFile.write("{0} {1}\n".format(str(datetime.now()).replace(" ", "_"), msg))

    def pretty_msg(self, msg):
        '''Only print key,value pairs where value is not None'''
        pretty = "{"
        for key, value in msg.items():
            if value is not None:
                pretty += "{0}:{1},".format(key,value)
        pretty = pretty[:-1] + "}"
        return pretty

# functions for main application
def help():
    help_str = '''Chord Log Application v1.0 
    ring           print chord ring    
    stabilize      get stabilization time
    start          application start time
    end            application end time
    servers        number of server nodes
    clients        number of client nodes
    exit           exit application
    help           print help screen
    '''

def ring():
    global log_str
    chord_ring = ""
    # find chord ids
    ring_re = re.compile(r"chord_id is [0-9]+")
    # get chord ids
    num_re = re.compile(r'[0-9]+')
    # sort ids
    nodes = sorted(list(map(int,num_re.findall("".join(ring_re.findall(log_str))))))
    for node in nodes:
        chord_ring += "{0}->".format(node)
    chord_ring += str(nodes[0])
    return chord_ring

def start():
    global sorted_entries
    return sorted_entries[0]["time"]

def end():
    global sorted_entries
    return sorted_entries[-1]["time"]
    
def report():
    global log_str
    # report of log summaries etc
    report_str = \
    '''
    Start: {0}\n\
    End: {1}\n\
    # Servers: {2}\n\
    # Clients: {3}\n\
    Ring: {4}\n\
    Stabilization Time: {5}\n\
    '''.format(start(),end(),servers(),clients(),ring(),stabilize())
    return report_str

def stabilize():
    global log_str
    # example 2018-05-06_19:17:52.324541 <172.1.1.1>: Successor updated by stabilize
    stabilize_re = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{6} <[0-9]+.[0-9]+.[0-9]+.[0-9]>: Successor updated by stabilize")    
    times_stab = stabilize_re.findall(log_str)
    time_re = re.compile(r"[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{6}")
    times = time_re.findall("".join(times_stab))
    start = datetime.strptime(times[0],"%H:%M:%S.%f")
    end = datetime.strptime(times[-1],"%H:%M:%S.%f")
    total = end - start
    final = "{0} sec".format(total.total_seconds())
    return final

def servers():
    global log_str    
    # find chord ids
    ring_re = re.compile(r"chord_id is [0-9]+")
    nodes = ring_re.findall(log_str)
    return len(nodes)

def clients():
    global log_str    
    # find clients    
    # ex: I'm a chord client, my IP is 172.1.1.2
    ring_re = re.compile(r"chord client, my IP is [0-9]+.[0-9]+.[0-9]+.[0-9]+")
    ip_re = re.compile(r"[0-9]+.[0-9]+.[0-9]+.[0-9]")    
    nodes = ip_re.findall("".join(ring_re.findall(log_str)))
    return len(nodes)

if __name__ == "__main__":
    # Get every file in logs folder
    logFileNames = []
    for root, dirs, files in os.walk("nodes", topdown=False):
        for f in files:
            if f.endswith(".log"):
                logFileNames.append(os.path.join(root, f))

    # Get all entries from log files
    entries = []
    for logFileName in logFileNames:
        logFile = open(logFileName)
        for line in logFile:
            timestamp = line.strip().split(" ", 1)[0]
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d_%H:%M:%S.%f")
            entry = dict()
            entry['time'] = timestamp
            entry['log'] = line
            entries.append(entry)
        logFile.close()
    
    log_str = ""
    sorted_entries = sorted(entries, key=lambda e: e['time'])
    # Print all entries in order
    for entry in sorted_entries:
        log_str += entry['log'] + "\n"        

    # same compiled logs into 1    
    with open("master.log", "w") as f_out:
        f_out.write(log_str)

    input_str = ""    

    while True:
        input_str = input("Enter a command: ")
        if input_str == "help":
            help()
        if input_str == "exit":
            break
        if input_str == "ring":
            print(ring())
        if input_str == "start":
            print(start())
        if input_str == "end":
            print(end())
        if input_str == "stabilize":
            print(stabilize())
        if input_str == "servers":
            print(servers())
        if input_str == "clients":
            print(clients())
        if input_str == "report":
            print(report())
        sys.stdout.flush()
