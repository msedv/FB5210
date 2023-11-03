#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
#             M S E D V   W I N D H A G E R   V I A   E S P
# ----------------------------------------------------------------------------
# (c) 2014-2023 msedv - DI Markus Schwaiger EDV-Dienstleistungen
#               Phone: +43-1-5449532-0; Fax: +43-1-5449532-14
#               Internet: http://www.msedv.at; Mail: office@msedv.at
#               SnailMail: Hauptstr. 110, A-1140 Wien/Vienna, Austria
# ----------------------------------------------------------------------------
#  History:
#  1.11.2023 MS	Beginn Implementierung
# ----------------------------------------------------------------------------
#  ToDo:
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

import signal, sys, socket

runLoop = True

def signal_handler (sig, frame):
	global runLoop

	print ("You pressed Ctrl+C!")
	runLoop = False
	# sys.exit (0)

def reflect_data(x, width):
    # See: https://stackoverflow.com/a/20918545
    if width == 8:
        x = ((x & 0x55) << 1) | ((x & 0xAA) >> 1)
        x = ((x & 0x33) << 2) | ((x & 0xCC) >> 2)
        x = ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)
    elif width == 16:
        x = ((x & 0x5555) << 1) | ((x & 0xAAAA) >> 1)
        x = ((x & 0x3333) << 2) | ((x & 0xCCCC) >> 2)
        x = ((x & 0x0F0F) << 4) | ((x & 0xF0F0) >> 4)
        x = ((x & 0x00FF) << 8) | ((x & 0xFF00) >> 8)
    elif width == 32:
        x = ((x & 0x55555555) << 1) | ((x & 0xAAAAAAAA) >> 1)
        x = ((x & 0x33333333) << 2) | ((x & 0xCCCCCCCC) >> 2)
        x = ((x & 0x0F0F0F0F) << 4) | ((x & 0xF0F0F0F0) >> 4)
        x = ((x & 0x00FF00FF) << 8) | ((x & 0xFF00FF00) >> 8)
        x = ((x & 0x0000FFFF) << 16) | ((x & 0xFFFF0000) >> 16)
    else:
        raise ValueError('Unsupported width')

    return x

def crc_poly(data, n, poly, crc=0, ref_in=False, ref_out=False, xor_out=0):
    g = 1 << n | poly  # Generator polynomial

    # Loop over the data
    for d in data:
        # Reverse the input byte if the flag is true
        if ref_in:
            d = reflect_data(d, 8)

        # XOR the top byte in the CRC with the input byte
        crc ^= d << (n - 8)

        # Loop over all the bits in the byte
        for _ in range(8):
            # Start by shifting the CRC, so we can check for the top bit
            crc <<= 1

            # XOR the CRC if the top bit is 1
            if crc & (1 << n):
                crc ^= g

    # Reverse the output if the flag is true
    if ref_out:
        crc = reflect_data(crc, n)

    # Return the CRC value
    return crc ^ xor_out

def checkPacketCRC (dataNetPacket, dataCRC):
	crc = crc_poly (dataNetPacket, 8, 0xD5, 0, True, True, 0)
	# print (crc, dataCRC)
	return crc == dataCRC

def dump (packet):
	return ''.join (format (x, '02x') for x in packet)

def parseOneTemp (byte1, byte2):
	res = None
	res = "-"

									# 0x7fff = kein Wert
	if byte1 != 0x7f and byte2 != 0xff:
		res = (255.0 * byte1 + byte2) / 100

	return res

def parsePacket (dataNetPacket):
	temp1Head = b'\x92\x05\x7f\x03\x02\x67\x08\x22\x0a' # 92057f03026708220a
	temp2Head = b'\x9b\x7f\x05\x02\x83\xf7\x00\x06\x21' # 0ac001091008fc157c

	if   dataNetPacket == b'\x9b\x7f\x00\x02\x83\xe7\x00':         # 9b7f000283e700
		print (dump (dataNetPacket), "ACK_BD_MD00")
	elif dataNetPacket == b'\x92\x05\x7f\x03\x02\x77\x07\x21\x00': # 92057f030277072100
		print (dump (dataNetPacket), "ASK_RAUM")
	elif dataNetPacket [:len (temp1Head)] == temp1Head:
		tempBin = dataNetPacket [len (temp1Head):]
		print ("Temp1:", dump (tempBin),
					 parseOneTemp (tempBin [0], tempBin [1]), parseOneTemp (tempBin [2], tempBin [3]), parseOneTemp (tempBin [4], tempBin [5]), parseOneTemp (tempBin [6], tempBin [7]), parseOneTemp (tempBin [8], tempBin [9]))
	elif dataNetPacket [:len (temp2Head)] == temp2Head:
		tempBin = dataNetPacket [len (temp2Head):]
		print ("Temp2:", dump (tempBin),
					 tempBin [0], parseOneTemp (tempBin [1], tempBin [2]), parseOneTemp (tempBin [3], tempBin [4]), parseOneTemp (tempBin [5], tempBin [6]), parseOneTemp (tempBin [7], tempBin [8]), tempBin [9])
	else:
		print (''.join (format (x, '02x') for x in dataNetPacket))

def readSocketFromESP (ip, port):
	global runLoop

	try:
		sock = socket.create_connection ((ip, port))

		timeout_seconds = 5
		sock.settimeout (timeout_seconds)

		while runLoop:
			dataStart = sock.recv (2)

			cnt = 0

			while runLoop and dataStart != b'\x10\x02':
				if cnt == 0:
					print ("*** ", end = "")

				dataStart = sock.recv (2)
				print (dataStart, end = "")
				cnt = cnt + 1

			if runLoop:
				if cnt > 0:
					print ()

				cnt = 0
				
				dataPacket = dataStart
				dataEnd1 = sock.recv (1)
				dataEnd2 = sock.recv (1)

										# Warten bis das erste Start-Tupel (x10x02) kommt
				while (cnt <= 100) and runLoop and not ((dataEnd1 == b'\x10') and (dataEnd2 == b'\x03')):
					dataPacket = dataPacket + dataEnd1
					# print (dataPacket, dataEnd1, dataEnd2)
					dataEnd1 = dataEnd2
					dataEnd2 = sock.recv (1)
					# print ("vor while:", dataEnd1, dataEnd2)
					cnt = cnt + 1

				if cnt >= 100:
					print ("keine Endemarkierung innerhalb von 100 Zeichen")
				else:
										# Bytes bis zum Ende-Tupel (x10x03) sammeln - max. 100 Bytes; wenn das überschritten wird dann ist was schief gegangen
					dataPacket = dataPacket + dataEnd1 + dataEnd2
										# Das CRC-Byte ist das letzte vor der Endekennung
					dataCRC = dataPacket [-3:]
					dataCRC = dataCRC [0]
										# Start (x10x02) und Ende (x10x03) weglassen
					dataNetPacket = dataPacket [2:]
					dataNetPacket = dataNetPacket [:-3]
										# x10 hat besondere Bedeutung als Frame-Anfang/Ende; falls es doch mal als Wert vorkommt wird es daher escapt, also doppelt gesendet
					dataNetPacket = dataNetPacket.replace (b'\x10\x10', b'\x10')
					# print (dataPacket, dataCRC, dataNetPacket)
					# print (''.join (format (x, '02x') for x in dataPacket), dataCRC, ''.join (format (x, '02x') for x in dataNetPacket))
					
					if checkPacketCRC (dataNetPacket, dataCRC):
						parsePacket (dataNetPacket)
					else:
						print ("Ungültiger CRC-Code:", ''.join (format (x, '02x') for x in dataPacket), dataCRC, ''.join (format (x, '02x') for x in dataNetPacket))
	except Exception as e:
		print (e)

if __name__ == "__main__":
	if len (sys.argv) < 2:
		print ("Aufruf mit " + sys.argv [0] + " 1.2.3.4")
	else:
		print ("Starte Scanner für " + sys.argv [1] + ":10000")
		signal.signal (signal.SIGINT, signal_handler)

		while runLoop:
			readSocketFromESP (sys.argv [1], 10000)
