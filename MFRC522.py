##!/usr/bin/env python3
# -*- coding: utf8 -*-
#
#    Copyright 2025 Mohammad Reza Mohammadi
#
#    Base on Mario Gomez <mario.gomez@teubi.co>   MFRC522-Python



import spidev 
import signal
import time

DEBUG = False


class MFRC522:
  MAX_LEN = 16

  PCD_IDLE       = 0x00
  PCD_AUTHENT    = 0x0E
  PCD_RECEIVE    = 0x08
  PCD_TRANSMIT   = 0x04
  PCD_TRANSCEIVE = 0x0C
  PCD_RESETPHASE = 0x0F
  PCD_CALCCRC    = 0x03

  PICC_REQIDL    = 0x26
  PICC_REQALL    = 0x52
  PICC_ANTICOLL1  = 0x93
  PICC_ANTICOLL2  = 0x95
  PICC_ANTICOLL3  = 0x97
  PICC_AUTHENT1A = 0x60
  PICC_AUTHENT1B = 0x61
  PICC_READ      = 0x30
  PICC_WRITE     = 0xA0
  PICC_DECREMENT = 0xC0
  PICC_INCREMENT = 0xC1
  PICC_RESTORE   = 0xC2
  PICC_TRANSFER  = 0xB0
  PICC_HALT      = 0x50

  MI_OK       = 0
  MI_NOTAGERR = 1
  MI_ERR      = 2

  Reserved00     = 0x00
  CommandReg     = 0x01
  CommIEnReg     = 0x02
  DivlEnReg      = 0x03
  CommIrqReg     = 0x04
  DivIrqReg      = 0x05
  ErrorReg       = 0x06
  Status1Reg     = 0x07
  Status2Reg     = 0x08
  FIFODataReg    = 0x09
  FIFOLevelReg   = 0x0A
  WaterLevelReg  = 0x0B
  ControlReg     = 0x0C
  BitFramingReg  = 0x0D
  CollReg        = 0x0E
  Reserved01     = 0x0F

  Reserved10     = 0x10
  ModeReg        = 0x11
  TxModeReg      = 0x12
  RxModeReg      = 0x13
  TxControlReg   = 0x14
  TxAutoReg      = 0x15
  TxSelReg       = 0x16
  RxSelReg       = 0x17
  RxThresholdReg = 0x18
  DemodReg       = 0x19
  Reserved11     = 0x1A
  Reserved12     = 0x1B
  MifareReg      = 0x1C
  Reserved13     = 0x1D
  Reserved14     = 0x1E
  SerialSpeedReg = 0x1F

  Reserved20        = 0x20
  CRCResultRegM     = 0x21
  CRCResultRegL     = 0x22
  Reserved21        = 0x23
  ModWidthReg       = 0x24
  Reserved22        = 0x25
  RFCfgReg          = 0x26
  GsNReg            = 0x27
  CWGsPReg          = 0x28
  ModGsPReg         = 0x29
  TModeReg          = 0x2A
  TPrescalerReg     = 0x2B
  TReloadRegH       = 0x2C
  TReloadRegL       = 0x2D
  TCounterValueRegH = 0x2E
  TCounterValueRegL = 0x2F

  Reserved30      = 0x30
  TestSel1Reg     = 0x31
  TestSel2Reg     = 0x32
  TestPinEnReg    = 0x33
  TestPinValueReg = 0x34
  TestBusReg      = 0x35
  AutoTestReg     = 0x36
  VersionReg      = 0x37
  AnalogTestReg   = 0x38
  TestDAC1Reg     = 0x39
  TestDAC2Reg     = 0x3A
  TestADCReg      = 0x3B
  Reserved31      = 0x3C
  Reserved32      = 0x3D
  Reserved33      = 0x3E
  Reserved34      = 0x3F

  serNum = []

  def __init__(self, bus=0,dev=0, spd=1000000):
    self.spi=spidev.SpiDev()
    self.spi.open(bus=bus,device=dev)
    self.spi.max_speed_hz=spd
    self.MFRC522_Init()

  def MFRC522_Reset(self):
    self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

  def Write_MFRC522(self, addr, val):
    self.spi.writebytes(((addr<<1)&0x7E,val))

  def Read_MFRC522(self, addr):
    val = self.spi.xfer2((((addr<<1)&0x7E) | 0x80,0))
    return val[1]

  def SetBitMask(self, reg, mask):
    tmp = self.Read_MFRC522(reg)
    self.Write_MFRC522(reg, tmp | mask)

  def ClearBitMask(self, reg, mask):
    tmp = self.Read_MFRC522(reg);
    self.Write_MFRC522(reg, tmp & (~mask))

  def AntennaOn(self):
    temp = self.Read_MFRC522(self.TxControlReg)
    if(~(temp & 0x03)):
      self.SetBitMask(self.TxControlReg, 0x03)

  def AntennaOff(self):
    self.ClearBitMask(self.TxControlReg, 0x03)

  def MFRC522_ToCard(self,command,sendData):
    backData = []
    backLen = 0
    status = self.MI_ERR
    irqEn = 0x00
    waitIRq = 0x00
    lastBits = None
    n = 0
    i = 0

    if command == self.PCD_AUTHENT:
      irqEn = 0x12
      waitIRq = 0x10
    if command == self.PCD_TRANSCEIVE:
      irqEn = 0x77
      waitIRq = 0x30

    self.Write_MFRC522(self.CommIEnReg, irqEn|0x80)
    self.ClearBitMask(self.CommIrqReg, 0x80)
    self.SetBitMask(self.FIFOLevelReg, 0x80)

    self.Write_MFRC522(self.CommandReg, self.PCD_IDLE);  

    while(i<len(sendData)):
      self.Write_MFRC522(self.FIFODataReg, sendData[i])
      i = i+1

    self.Write_MFRC522(self.CommandReg, command)

    if command == self.PCD_TRANSCEIVE:
      self.SetBitMask(self.BitFramingReg, 0x80)

    i = 2000
    while True:
      n = self.Read_MFRC522(self.CommIrqReg)
      i = i - 1
      if ~((i!=0) and ~(n&0x01) and ~(n&waitIRq)):
        break

    self.ClearBitMask(self.BitFramingReg, 0x80)

    if i != 0:
      if (self.Read_MFRC522(self.ErrorReg) & 0x1B)==0x00:
        status = self.MI_OK

        if n & irqEn & 0x01:
          status = self.MI_NOTAGERR

        if command == self.PCD_TRANSCEIVE:
          n = self.Read_MFRC522(self.FIFOLevelReg)
          lastBits = self.Read_MFRC522(self.ControlReg) & 0x07
          if lastBits != 0:
            backLen = (n-1)*8 + lastBits
          else:
            backLen = n*8

          if n == 0:
            n = 1
          if n > self.MAX_LEN:
            n = self.MAX_LEN

          i = 0
          while i<n:
            backData.append(self.Read_MFRC522(self.FIFODataReg))
            i = i + 1;
      else:
        status = self.MI_ERR

    return (status,backData,backLen)


  def MFRC522_Request(self, reqMode):
    status = None
    backBits = None
    TagType = []

    self.Write_MFRC522(self.BitFramingReg, 0x07)

    TagType.append(reqMode);
    (status,backData,backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, TagType)

    if ((status != self.MI_OK) | (backBits != 0x10)):
      status = self.MI_ERR

    return (status,backBits)


  def MFRC522_Anticoll(self,anticolN):
    backData = []
    serNumCheck = 0

    serNum = []

    self.Write_MFRC522(self.BitFramingReg, 0x00)

    serNum.append(anticolN)
    serNum.append(0x20)

    (status,backData,backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE,serNum)

    if(status == self.MI_OK):
      i = 0
      if len(backData)==5:
        while i<4:
          serNumCheck = serNumCheck ^ backData[i]
          i = i + 1
        if serNumCheck != backData[i]:
          status = self.MI_ERR
      else:
        status = self.MI_ERR

    return (status,backData)

  def MFRC522_Anticoll1(self):
    return  self.MFRC522_Anticoll(self.PICC_ANTICOLL1)

  def MFRC522_Anticoll2(self):
    return  self.MFRC522_Anticoll(self.PICC_ANTICOLL2)

  def MFRC522_Anticoll3(self):
    return  self.MFRC522_Anticoll(self.PICC_ANTICOLL3)


  def CalulateCRC(self, pIndata):
    self.ClearBitMask(self.DivIrqReg, 0x04)
    self.SetBitMask(self.FIFOLevelReg, 0x80);
    i = 0
    while i<len(pIndata):
      self.Write_MFRC522(self.FIFODataReg, pIndata[i])
      i = i + 1
    self.Write_MFRC522(self.CommandReg, self.PCD_CALCCRC)
    i = 0xFF
    while True:
      n = self.Read_MFRC522(self.DivIrqReg)
      i = i - 1
      if not ((i != 0) and not (n&0x04)):
        break
    pOutData = []
    pOutData.append(self.Read_MFRC522(self.CRCResultRegL))
    pOutData.append(self.Read_MFRC522(self.CRCResultRegM))
    return pOutData

  def MFRC522_PcdSelect(self, serNum,anticolN):
    backData = []
    buf = []
    buf.append(anticolN)
    buf.append(0x70)
    i = 0
    while i<5:
      buf.append(serNum[i])
      i = i + 1
    pOut = self.CalulateCRC(buf)
    buf.append(pOut[0])
    buf.append(pOut[1])
    (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buf)
    if (status == self.MI_OK) and (backLen == 0x18):
      if DEBUG:
        print("Size: " + str(backData[0]))
        print("PcdSelect {} {}".format(anticolN,backData))
      return  1
    else:
      return 0

  def MFRC522_PcdSelect1(self, serNum):
    return  self.MFRC522_PcdSelect(serNum,self.PICC_ANTICOLL1)

  def MFRC522_PcdSelect2(self, serNum):
    return  self.MFRC522_PcdSelect(serNum,self.PICC_ANTICOLL2)

  def MFRC522_PcdSelect3(self, serNum):
    return  self.MFRC522_PcdSelect(serNum,self.PICC_ANTICOLL3)




  def MFRC522_Auth(self, authMode, BlockAddr, Sectorkey, serNum):
    buff = []

    # First byte should be the authMode (A or B)
    buff.append(authMode)

    # Second byte is the trailerBlock (usually 7)
    buff.append(BlockAddr)

    # Now we need to append the authKey which usually is 6 bytes of 0xFF
    i = 0
    while(i < len(Sectorkey)):
      buff.append(Sectorkey[i])
      i = i + 1
    i = 0

    # Next we append the first 4 bytes of the UID
    while(i < 4):
      buff.append(serNum[i])
      i = i +1

    # Now we start the authentication itself
    (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_AUTHENT,buff)

    # Check if an error occurred


    if DEBUG:
      if not(status == self.MI_OK):
        print("AUTH ERROR!!")
      if not (self.Read_MFRC522(self.Status2Reg) & 0x08) != 0:
        print("AUTH ERROR(status2reg & 0x08) != 0")

    # Return the status
    return status

  def MFRC522_StopCrypto1(self):
    self.ClearBitMask(self.Status2Reg, 0x08)

  def MFRC522_Read(self, blockAddr):
    recvData = []
    recvData.append(self.PICC_READ)
    recvData.append(blockAddr)
    pOut = self.CalulateCRC(recvData)
    recvData.append(pOut[0])
    recvData.append(pOut[1])
    (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, recvData)
    if not(status == self.MI_OK):
      print("Error while reading!")
    i = 0
    if len(backData) == 16:
      print("Sector "+str(blockAddr)+" "+str(backData))

  def MFRC522_Write(self, blockAddr, writeData):
    buff = []
    buff.append(self.PICC_WRITE)
    buff.append(blockAddr)
    crc = self.CalulateCRC(buff)
    buff.append(crc[0])
    buff.append(crc[1])
    (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buff)
    if not(status == self.MI_OK) or not(backLen == 4) or not((backData[0] & 0x0F) == 0x0A):
        status = self.MI_ERR
    
    print("%s backdata &0x0F == 0x0A %s" % (backLen, backData[0]&0x0F))
    if status == self.MI_OK:
        i = 0
        buf = []
        while i < 16:
            buf.append(writeData[i])
            i = i + 1
        crc = self.CalulateCRC(buf)
        buf.append(crc[0])
        buf.append(crc[1])
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE,buf)
        if not(status == self.MI_OK) or not(backLen == 4) or not((backData[0] & 0x0F) == 0x0A):
            print("Error while writing")
        if status == self.MI_OK:
            print("Data written")

  def MFRC522_DumpClassic1K(self, key, uid):
    i = 0
    while i < 64:
        status = self.MFRC522_Auth(self.PICC_AUTHENT1A, i, key, uid)
        # Check if authenticated
        if status == self.MI_OK:
            self.MFRC522_Read(i)
        else:
            print("Authentication error")
        i = i+1

  def MFRC522_Init(self):

    self.MFRC522_Reset();


    self.Write_MFRC522(self.TModeReg, 0x8D)
    self.Write_MFRC522(self.TPrescalerReg, 0x3E)
    self.Write_MFRC522(self.TReloadRegL, 30)
    self.Write_MFRC522(self.TReloadRegH, 0)

    self.Write_MFRC522(self.TxAutoReg, 0x40)
    self.Write_MFRC522(self.ModeReg, 0x3D)
    self.AntennaOn()


  def MFRC522_SelectTagSN(self):
      valid_uid=[]
      (status,uid)= self.MFRC522_Anticoll1()
      if status != self.MI_OK:
           return  (self.MI_ERR,[])

      if DEBUG:   print("anticol1() {}".format(uid))
      if self.MFRC522_PcdSelect1(uid) == 0:
          return (self.MI_ERR,[])
      if DEBUG:   print("pcdSelect1() {}".format(uid))

      #check if first byte is 0x88
      if uid[0] == 0x88 :
        #ok we have another type of card
         valid_uid.extend(uid[1:4])
         (status,uid)=self.MFRC522_Anticoll2()
         if status != self.MI_OK:
           return (self.MI_ERR,[])
         if DEBUG: print("Anticol2() {}".format(uid))
         rtn =  self.MFRC522_PcdSelect2(uid)
         if DEBUG: print("pcdSelect2 return={} uid={}".format(rtn,uid))
         if rtn == 0:
           return (self.MI_ERR,[])
         if DEBUG: print("PcdSelect2() {}".format(uid))
         #now check again if uid[0] is 0x88
         if uid[0] == 0x88 :
           valid_uid.extend(uid[1:4])
           (status , uid) = self.MFRC522_Anticoll3()
           if status != self.MI_OK:
             return (self.MI_ERR,[])
           if DEBUG: print("Anticol3() {}".format(uid))
           if self.MFRC522_PcdSelect3(uid) == 0:
             return (self.MI_ERR,[])
           if DEBUG: print("PcdSelect3() {}".format(uid))
      valid_uid.extend(uid[0:4])

      return (self.MI_OK,valid_uid)


