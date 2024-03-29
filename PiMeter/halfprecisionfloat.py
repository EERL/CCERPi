# halfpercisionfloat.py
# Converts 32bit IEEE floating point number to 16bit floating point

import struct
import binascii

class Float16Compressor:
    def __init__(self):
        self.temp = 0
        
    def unpack(self,f32):
        """
        Takes f32 in type format and converts it to unpacked config
        """
        a = struct.pack('>f',f32)
        b = binascii.hexlify(a)
        return int(b)
    
    def compress(self,float32):
        """
        Take in 32 bit float and converts it to a 16 bit float
        Returns: 16 bit float as IEEE floating point configuration. Not in float type
        parameters: 
        
        float32: 32 bit float number to convert; must be a float type
        """

        F16_EXPONENT_BITS = 0x1F
        F16_EXPONENT_SHIFT = 10
        F16_EXPONENT_BIAS = 15
        F16_MANTISSA_BITS = 0x3ff
        F16_MANTISSA_SHIFT =  (23 - F16_EXPONENT_SHIFT)
        F16_MAX_EXPONENT =  (F16_EXPONENT_BITS << F16_EXPONENT_SHIFT)

        if type(float32) == float:
            f32 = self.unpack(float32)
        else:
            f32 = float32
        f16 = 0
        sign = (f32 >> 16) & 0x8000
        exponent = ((f32 >> 23) & 0xff) - 127
        mantissa = f32 & 0x007fffff
                
        if exponent == 128:
            f16 = sign | F16_MAX_EXPONENT
            if mantissa:
                f16 |= (mantissa & F16_MANTISSA_BITS)
        elif exponent > 15:
            f16 = sign | F16_MAX_EXPONENT
        elif exponent > -15:
            exponent += F16_EXPONENT_BIAS
            mantissa >>= F16_MANTISSA_SHIFT
            f16 = sign | exponent << F16_EXPONENT_SHIFT | mantissa
        else:
            f16 = sign
        return f16
        
        
    def decompress(self,float16):
        s = int((float16 >> 15) & 0x00000001)    # sign
        e = int((float16 >> 10) & 0x0000001f)    # exponent
        f = int(float16 & 0x000003ff)            # fraction

        if e == 0:
            if f == 0:
                return int(s << 31)
            else:
                while not (f & 0x00000400):
                    f = f << 1
                    e -= 1
                e += 1
                f &= ~0x00000400
                #print(s,e,f)
        elif e == 31:
            if f == 0:
                return int((s << 31) | 0x7f800000)
            else:
                return int((s << 31) | 0x7f800000 | (f << 13))

        e = e + (127 -15)
        f = f << 13
        return int((s << 31) | (e << 23) | f)
