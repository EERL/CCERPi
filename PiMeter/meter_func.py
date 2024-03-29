# meter_func.py
# 5/29/19
# Xiaoyu Yan (xy97)
# functions{
#   meter_init:     Writes to Wattnode meter with the CT amperage ratings and CT directions
#   run_meter:      Reads from the meter. We read registers:
#                   1010 - 1016 : real power
#                   1148 - 1153 : reactive power
#                   Each meter can have three phases' each phase can have one real and one
#                   reactive power reading. The readings are 4 bytes stored in two 2 byte 
#                   registers. To read from the values, we must poll two registers and then
#                   combined the two values from the two registers in little endian format
#                   LSB in lower addr, MSB in high addr.
#                   Readings are in IEEE floating point format.
#                   We compress the readings from 4 bytes to 2 bytes for smaller payload to
#                   send over radio.
#                   Polls the Wattnode every second
#   serial_monitor: Handles communication with Feather MCU. 
#                   Custom communication protocol: 
#                   if recv msg
#                   '<': sends '>' so that MCU knows beginning of msg and then send msg
#                   otherwise, wait but don't stall meter polling.
#                   This module busy waits so it is important to set some sleep time so 
#                   we are not polling every cycle.
# }

import serial
import time
import pymodbus.client 
from pymodbus.client import sync as modbus
import pymodbus.register_read_message
import logging
import sys
import halfprecisionfloat
import struct
from collections import deque
import subprocess
from meter_settings import *


fcomp = halfprecisionfloat.Float16Compressor()
lst = []
Queue = deque(lst,3)
connection = 0

def meter_init(PORT,BAUD=19200, A=100,B=100,C=100,a=0,b=0,c=0):
    """
    Initializes the meter settings
    A,B,C: CT ratings for phase A,B,C respectively
    a,b,c: CT directions. 0 or 1
    """  
    #SERIAL = '/dev/ttyUSB0'
    #BAUD = 19200

    client =  modbus.ModbusSerialClient(method='rtu', port=PORT,\
        stopbits=1, bytesize=8, timeout=3, baudrate=BAUD, parity='N')

    connection = client.connect()
    print ("initializing meter, connection = " +str(connection) )
    time.sleep(0.5)
    
    print ("Reading CT settings")
    response = client.read_holding_registers(1602,count=4,unit=1)
    print ("%d, %d, %d, %d" %(response.registers[0], response.registers[1],\
            response.registers[2], response.registers[3]))
    
    print ("Writing to CT registers")
    client.write_registers(1603, [A,B,C])
    print ("Reading CT directions")
    response = client.read_holding_registers(1606,count=1,unit=1)
    print ("%d" %(response.registers[0]))

    print ("setting CT's directions")
    value = (a&0x1)|((b&0x1)<<1)|((c&0x1)<<2)
    client.write_registers(1606,value)


    client.close()


def run_meter(PORT, INTERVAL, PHASE, ADDRS, BAUD=19200, debug=True):
    """
    packs seconds of data 
    """
    
    try:
        print "starting"

        #SERIAL = '/dev/ttyUSB0'
        #BAUD = 19200

        client =  modbus.ModbusSerialClient(method='rtu', port=PORT,\
        stopbits=1, bytesize=8, timeout=3, baudrate=BAUD, parity='N')
        global connection
        connection = client.connect()
        print "connection is "+ str(connection)
        time.sleep(0.5)
        package_length = INTERVAL*PHASE*BYTE_SIZE_PER_READ*READS_PER_PHASE
         #PHASE*bytes/phase ; we are polling real and reactive
        header_length  = 4   #header msgs such as time and phase
        msg_length     = package_length + header_length
        while(connection):
            packed  = []
            message = []
            message.append(msg_length&0xFF)          #Doesn't count since it gets read
            message.append(0xF1)                     #Meter function
            message.append(PHASE &0xFF)
            message.append(time.localtime()[4]&0xFF) #local relative minutes
            message.append(time.localtime()[5]&0xFF) #local relative seconds
            for i in range(INTERVAL):
                start_time = time.time()
                #print "Polling Response"
                #Read registers 1010 - 1016 real power
                #1148  - 1153 reactive power
                for j in range(len(ADDRS)):
                    response = client.read_holding_registers(ADDRS[j][0],\
                    count = ADDRS[j][1],unit = ADDRS[j][2])
                    for k in range(0,len(response.registers),2):
                        val = (response.registers[k])|(response.registers[k+1]<<16) 
                        if debug:
                            print ADDRS[j]
                            print((struct.unpack('f',struct.pack('I',val))))
                        valComp = fcomp.compress(val)
                        message.append(valComp & 0xff)
                        message.append((valComp & 0xff00)>>8)
                
                end_time = time.time()
                delay  = max(0, 1 - (end_time-start_time)) # how long needed to 
                # wait for next polling
                #if debug:
                #   print "time diff: " + repr(end_time-start_time)
                time.sleep(delay) #delay to account for computation time
            for mes in message:
                packed.append(struct.pack('>B',mes).encode('hex'))
                
            Queue.append(packed)
            if debug:
                print "len = " +str(len(message))+  " message = " + repr(message) 
            
            
    except Exception as e:
        print (e)
        print (str(e.message))
        print "meter disconnected"   
        logging.error(str(time.localtime()) + "RUN_METER() "+str(e.message))
    client.close()


def serial_monitor(debug=True):
    try:
        with serial.Serial(
            port='/dev/serial0',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        ) as ser:
            while True:
                if len(Queue)>0 and debug:
                    print "Queue: " + repr(Queue)
                if len(Queue) != 0 and ser.read() == '<':
                    ser.write('>')

                    msg = Queue.popleft()
                    if debug:
                        print "got ready signal!"
                    for p in msg:
                        ser.write(p)
                        time.sleep(0.01)
                        
                    ser.reset_input_buffer()
                
                time.sleep(0.5) #SUPPER IMPORTANT AS TO NOT OVERLOAD CPU
                    
    except Exception as e:
        print "serial error"
        logging.error(str(time.localtime()) + " SERIAL_MONITOR "+ str(e.message))
        
      



if __name__=="__main__":
    while True:
        try:    
            port = subprocess.check_output("ls /dev/ttyUSB*", shell=True) 
            port = port[:(len(port)-1)]
            #meter_init(port,19200,100,100,200,0,1,0)
            run_meter(port,12,2,[[1010,4,1]])
        except:
            print("exit")
    
    print ("DONE")
