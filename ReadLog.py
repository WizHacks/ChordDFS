from datetime import datetime
import os
import sys

class MyLogger():
    def __init__(self, ip, log_file_path, client=False):     
        self.ip = ip   
        self.log_file_path = log_file_path        
        self.client = client


    # Print that will show up in mininet output and get added to log file
    def mnPrint(self, msg):
        if self.client:
            # Format msg
            msg = "<{0}_c>: {1}".format(self.ip, msg)
        else:
            # Format msg
            msg = "<{0}>: {1}".format(self.ip, msg)

        # Print msg to stdout
        # TODO: figure out what to do with IOERROR
        print(msg)
        sys.stdout.flush() # need to flush output, else never show up

        # Write msg to log file        
        with open(self.log_file_path, "a") as logFile:
            logFile.write("{0} {1}\n".format(str(datetime.now()).replace(" ", "_"), msg))

if __name__ == "__main__":
    # Get every file in logs folder
    logFileNames = os.listdir("logs")

    # Get all entries from log files
    entries = []
    for logFileName in logFileNames:
        logFile = open("logs/" + logFileName)
        for line in logFile:
            timestamp = line.strip().split(" ", 1)[0]
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d_%H:%M:%S.%f")
            entry = dict()
            entry['time'] = timestamp
            entry['log'] = line
            entries.append(entry)
        logFile.close()
    
    # Print all entries in order
    for entry in sorted(entries, key=lambda e: e['time']):
        print(entry['log'])
