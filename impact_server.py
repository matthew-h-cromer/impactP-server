from flask import Flask, request
from flask_ngrok import run_with_ngrok
import telnetlib
import time
import json
import sys

# Class containing all Telnet communications for Impact P part marking machine
class partMarkingMachine:
    host_ip = '192.168.0.124' #IP address assigned to machine by DHCP. A better option might be configuring static
    port = '55555'            #Port setting on machine
        
    def __init__(self):
        self.tn = telnetlib.Telnet(self.host_ip, self.port)
        self.tn.set_debuglevel(2)
        # Telnet login string
        self.tn.write(bytes.fromhex('fffb1ffffb20fffb18fffb27fffd01fffb03fffd03'))
        time.sleep(2)
        # Put the impact machine into "Human response" mode
        response = self.sendCommand('VM H')

    def sendCommand(self, command):
        self.tn.write(command.encode() + b'\r\n')
        return self.tn.read_until(bytes.fromhex('0d0a0d0a'), timeout = 0.25).decode('ascii')    

    # Returns the state of the machine
    def ST(self):
        print("Sending command: ST")
        response = self.sendCommand('ST')
        
        #state = self.stateCodes[response[2:5].strip()]
        return {"success": True,
                "state": response,
                "message": response}

    # Sets a system variable    
    def VS(self, varNumber, value):
        command = 'VS ' + str(varNumber) + ' "' + str(value) + '"'
        print("Sending command: " + command)
        response = self.sendCommand(command)

        if "Variable saved" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}

    # Loads a program
    def LD(self, filename):
        command = 'LD "' + filename + '" 1 N'
        print("Sending command: " + command)
        response = self.sendCommand(command)

        if "Ready to mark" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}

    # Triggers program to run
    def GO(self):
        print("Sending command: GO")
        response = self.sendCommand('GO')
        
        if "Marking in progress" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}

    # Stops marking
    def AM(self):
        print("Sending command: AM")
        response = self.sendCommand('AM')
        
        if "Marking stopped" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}
    # Acknowledges fault
    def AD(self):
        print("Sending command: AD")
        response = self.sendCommand('AD')
        
        if "Default acquitted" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}

    # Return to origin
    def OG(self):
        print("Sending command: OG")
        response = self.sendCommand('OG')
        
        if "At origin" in response:
            return {"success": True,
                    "message": response}
        else:
            return {"success": False,
                    "message": response}

    def waitMarking(self):
        response = self.tn.read_until(b'Marking finished\r\n', timeout = 30).decode('ascii')
        if "Marking finished" in response:
            return {"success": True,
                    "message": "Done marking"}
        else:
            return {"success": False,
                    "message": response}
        
impactP = partMarkingMachine()

#FLASK
app = Flask(__name__)
app.config["CACHE_TYPE"] = "null"
run_with_ngrok(app)

@app.route('/')
def home():
    return 'Author: mcromer <br/> This api allows communication with an impactP part marking system'

# Returns the state of the machine
@app.route('/state')
def state():
    return impactP.ST()

# Commands machine to write MRC part marking file with given variables and returns result
@app.route('/mrc-part-marking')
def mrcPartMarking():
    # 1. Get to good initial state
    stateResponse = impactP.ST()
    # if state is ready, unload program, check "alive"
    print("State before marking: " + json.dumps(stateResponse))
    # 2. Set all program variables
    print("Arguments: " + json.dumps(request.args))
    neededArguments = ['invPartNumber', 'workOrderNumber', 'serialNumber']
    if not all(arguments in request.args for arguments in neededArguments):
        return {"success": False,
                "message": "Missing arguments"}
    else:
        v0response = impactP.VS(0, request.args.get('invPartNumber'))
        print(json.dumps(v0response))
        if v0response["success"] == False:
            return v0response
        
        v1response = impactP.VS(1, request.args.get('workOrderNumber'))
        print(json.dumps(v1response))
        if v1response["success"] == False:
            return v1response
        
        v2response = impactP.VS(2, request.args.get('serialNumber'))
        print(json.dumps(v2response))
        if v2response["success"] == False:
            return v2response

    # 3. Load the marking file
    if "Alive" in stateResponse["state"]:
        loadResponse = impactP.LD('MRC_PART_MARKING_REMOTE.tml')
        if loadResponse["success"] == False:
            return loadResponse
        
    # 4. Run the program
    goResponse = impactP.GO()
    if goResponse["success"] == False:
            return goResponse
        
    # 5. Wait for result
    result = impactP.waitMarking()
    result['invPartNumber'] = request.args.get('invPartNumber')
    result['workOrderNumber'] = request.args.get('workOrderNumber')
    result['serialNumber'] = request.args.get('serialNumber')
    return result

# Stops marking
@app.route('/stop')
def stopMarking():
    stopResponse = impactP.AM()
    print(json.dumps(stopResponse))
    faultAcknowledgeResponse = impactP.AD()
    print(json.dumps(faultAcknowledgeResponse))
    originResponse = impactP.OG()
    print(json.dumps(originResponse))

    return originResponse
    

if __name__ == '__main__':
    app.run() #Local args: debug=True, host="localhost", port="9000"

    
