# meter_setting.py
# 5/29/19
# Xiaoyu Yan (xy97)
# This is setting for the Pi to poll the meter
# Change values to match meter settings

MAX_MSG_SIZE   = 100  #in bytes
READS_PER_PHASE = 2  #Need to read real and reactive power : 2 regs
BYTE_SIZE_PER_READ = 2  #We reduce the size of each reading from 4 to 2 bytes
BAUD_RATE = 19200  #Baud rate of the Meter 
REGS_PER_READING = 2 #4 byte float or ints stored in two 16 bit registers in meter

# SHOULD BE CHANGED BASED ON NEEDS
PHASE     = 2   #Number of phases used usually 2 or 3
REG_ADDRS = [[1010,1],[1148,1]] # Address and their corresponding meter
CT_SIZE_A = 400 #Max current of CT_A. CT's used 100A, 200A, 400A
CT_SIZE_B = 400
CT_SIZE_C = 400
