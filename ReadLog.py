from datetime import datetime
import os

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
