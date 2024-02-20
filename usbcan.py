from ctypes import *
import os
import threading
import time

DevType = c_uint

'''
    Device Type
'''
USBCAN1 = DevType(3)
USBCAN2 = DevType(4)
USBCANFD = DevType(6)
'''
    Device Index
'''
DevIndex = c_uint(0)  # 设备索引
'''
    Channel
'''
Channel1 = c_uint(0)  # CAN1
Channel2 = c_uint(1)  # CAN2
'''
    ECAN Status
'''
STATUS_ERR = 0
STATUS_OK = 1

'''
    Device Information
'''


class BoardInfo(Structure):
    _fields_ = [("hw_Version", c_ushort),  # 硬件版本号，用16进制表示
                ("fw_Version", c_ushort),  # 固件版本号，用16进制表示
                ("dr_Version", c_ushort),  # 驱动程序版本号，用16进制表示
                ("in_Version", c_ushort),  # 接口库版本号，用16进制表示
                ("irq_Num", c_ushort),  # 板卡所使用的中断号
                ("can_Num", c_byte),  # 表示有几路CAN通道
                ("str_Serial_Num", c_byte * 20),  # 此板卡的序列号，用ASC码表示
                ("str_hw_Type", c_byte * 40),  # 硬件类型，用ASC码表示
                ("Reserved", c_byte * 4)]  # 系统保留


class CAN_OBJ(Structure):
    _fields_ = [("ID", c_uint),  # 报文帧ID
                ("TimeStamp", c_uint),  # 接收到信息帧时的时间标识，从CAN控制器初始化开始计时，单位微秒
                ("TimeFlag", c_byte),  # 是否使用时间标识，为1时TimeStamp有效，TimeFlag和TimeStamp只在此帧为接收帧时有意义。
                ("SendType", c_byte),
                # 发送帧类型。=0时为正常发送，=1时为单次发送（不自动重发），=2时为自发自收（用于测试CAN卡是否损坏），=3时为单次自发自收（只发送一次，用于自测试），只在此帧为发送帧时有意义
                ("RemoteFlag", c_byte),  # 是否是远程帧。=0时为数据帧，=1时为远程帧
                ("ExternFlag", c_byte),  # 是否是扩展帧。=0时为标准帧（11位帧ID），=1时为扩展帧（29位帧ID）
                ("DataLen", c_byte),  # 数据长度DLC(<=8)，即Data的长度
                ("data", c_ubyte * 8),  # CAN报文的数据。空间受DataLen的约束
                ("Reserved", c_byte * 3)]  # 系统保留。


class INIT_CONFIG(Structure):
    _fields_ = [("acccode", c_uint32),  # 验收码。SJA1000的帧过滤验收码
                ("accmask", c_uint32),  # 屏蔽码。SJA1000的帧过滤屏蔽码。屏蔽码推荐设置为0xFFFF FFFF，即全部接收
                ("reserved", c_uint32),  # 保留
                ("filter", c_byte),  # 滤波使能。0=不使能，1=使能。使能时，请参照SJA1000验收滤波器设置验收码和屏蔽码
                ("timing0", c_byte),  # 波特率定时器0,详见动态库使用说明书7页
                ("timing1", c_byte),  # 波特率定时器1,详见动态库使用说明书7页
                ("mode", c_byte)]  # 模式。=0为正常模式，=1为只听模式，=2为自发自收模式。


class ECAN(object):
    def __init__(self):
        cwdx = os.getcwd()
        self.dll = cdll.LoadLibrary(cwdx + '/ECanVci64.dll')
        if self.dll == None:
            print("DLL Couldn't be loaded")

    def OpenDevice(self, DeviceType, DeviceIndex):
        try:
            return self.dll.OpenDevice(DeviceType, DeviceIndex, 0)
        except:
            print("Exception on OpenDevice!")
            raise

    def CloseDevice(self, DeviceType, DeviceIndex):
        try:
            return self.dll.CloseDevice(DeviceType, DeviceIndex, 0)
        except:
            print("Exception on CloseDevice!")
            raise

    def InitCan(self, DeviceType, DeviceIndex, CanInd, Initconfig):
        try:
            return self.dll.InitCAN(DeviceType, DeviceIndex, CanInd, byref(Initconfig))
        except:
            print("Exception on InitCan!")
            raise

    def StartCan(self, DeviceType, DeviceIndex, CanInd):
        try:
            return self.dll.StartCAN(DeviceType, DeviceIndex, CanInd)
        except:
            print("Exception on StartCan!")
            raise

    def ReadBoardInfo(self, DeviceType, DeviceIndex):
        try:
            mboardinfo = BoardInfo()
            ret = self.dll.ReadBoardInfo(DeviceType, DeviceIndex, byref(mboardinfo))
            return mboardinfo, ret
        except:
            print("Exception on ReadBoardInfo!")
            raise

    def Receivce(self, DeviceType, DeviceIndex, CanInd, length):
        try:
            recmess = (CAN_OBJ * length)()
            ret = self.dll.Receive(DeviceType, DeviceIndex, CanInd, byref(recmess), length, 0)
            return length, recmess, ret
        except:
            print("Exception on Receive!")
            raise

    def Tramsmit(self, DeviceType, DeviceIndex, CanInd, mcanobj):
        try:
            # mCAN_OBJ=CAN_OBJ*2
            # self.dll.Transmit.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, POINTER(CAN_OBJ),
            # ctypes.c_uint16]
            return self.dll.Transmit(DeviceType, DeviceIndex, CanInd, byref(mcanobj), c_uint16(1))
        except:
            print("Exception on Tramsmit!")
            raise

class USBCAN:
    def __init__(self) -> None:
        self.musbcanopen = False
        self.rec_CAN1 = 1
        self.rec_CAN2 = 1
        
        self.ecan = ECAN()
        self.init_can()
        
    def init_can(self, baudvaluecan1="1M",baudvaluecan2="1M"):
        if self.musbcanopen == False:
            initconfig = INIT_CONFIG()
            initconfig.acccode = 0  
            initconfig.accmask = 0xFFFFFFFF  
            initconfig.filter = 0  
            mbaudcan1 = baudvaluecan1
            mbaudcan2 = baudvaluecan2

            if self.ecan.OpenDevice(USBCAN2, DevIndex) != STATUS_OK:
                raise RuntimeError("OpenDevice Failed!")
            initconfig.timing0, initconfig.timing1 = getTiming(mbaudcan1)
            initconfig.mode = 0

            if self.ecan.InitCan(USBCAN2, DevIndex, Channel1, initconfig) != STATUS_OK:
                self.ecan.CloseDevice(USBCAN2, DevIndex)
                raise RuntimeError("InitCan CAN1 Failed!")

            initconfig.timing0, initconfig.timing1 = getTiming(mbaudcan2)
            if self.ecan.InitCan(USBCAN2, DevIndex, Channel2, initconfig) != STATUS_OK:
                self.ecan.CloseDevice(USBCAN2, DevIndex)
                raise RuntimeError("InitCan CAN2 Failed!")

            if self.ecan.StartCan(USBCAN2, DevIndex, Channel1) != STATUS_OK:
                self.ecan.CloseDevice(USBCAN2, DevIndex)
                raise RuntimeError("StartCan CAN1 Failed!")
            
            if self.ecan.StartCan(USBCAN2, DevIndex, Channel2) != STATUS_OK:
                self.ecan.CloseDevice(USBCAN2, DevIndex)
                raise RuntimeError("StartCan CAN2 Failed!")
            
            self.musbcanopen = True
            self.rec_CAN1 = 1
            self.rec_CAN2 = 1
            
            self.received_msg1 = {}
            self.received_msg2 = {}

            self.t = threading.Timer(0.03, self.read_can)
            self.t.start()
            time.sleep(0.01)
        else:
            self.musbcanopen = False
            self.ecan.CloseDevice(USBCAN2, DevIndex)
        
    def read_can(self):
        '''Read can data. Data is stored in self.received_msg. 
        '''
        if self.musbcanopen == True:
            scount = 0
            while scount < 50:
                scount = scount+1
                len, rec, ret = self.ecan.Receivce(USBCAN2, DevIndex, Channel1, 1)
                if len > 0 and ret == 1:
                    self.received_msg1['Rec'] = self.rec_CAN1
                    self.rec_CAN1 = self.rec_CAN1 + 1
                    
                    self.received_msg1['Time'] = rec[0].TimeStamp
                    
                    self.received_msg1['ID'] = rec[0].ID
                    if rec[0].RemoteFlag == 0:
                        self.received_msg1['data'] = rec[0].data
                    else:
                        self.received_msg1['data'] = ['Remote Request']

                len_, rec_, ret_ = self.ecan.Receivce(USBCAN2, DevIndex, Channel2, 1)
                if len_ > 0 and ret_ == 1:
                    self.received_msg2['Rec'] = self.rec_CAN2
                    self.rec_CAN2 = self.rec_CAN2 + 1
                    
                    self.received_msg2['Time'] = rec_[0].TimeStamp
                    
                    self.received_msg2['ID'] = rec_[0].ID
                    if rec_[0].RemoteFlag == 0:
                        self.received_msg2['data'] = rec_[0].data
                    else:
                        self.received_msg2['data'] = ['Remote Request']
        time.sleep(0.01)    # delay 0.01 for blocking
        return self.received_msg1

    def write_can(self, info: dict, channel=1):
        if self.musbcanopen == False:
            raise RuntimeError('Please open the device first !')
        can_obj = CAN_OBJ()
        can_obj.ID = int(info['ID'], 16)
        can_obj.DataLen = int(len(info['data']))
        can_obj.data[0] = int(info['data'][0], 16)
        can_obj.data[1] = int(info['data'][1], 16)
        can_obj.data[2] = int(info['data'][2], 16)
        can_obj.data[3] = int(info['data'][3], 16)
        can_obj.data[4] = int(info['data'][4], 16)
        can_obj.data[5] = int(info['data'][5], 16)
        can_obj.data[6] = int(info['data'][6], 16)
        can_obj.data[7] = int(info['data'][7], 16)
        can_obj.RemoteFlag = 0
        can_obj.ExternFlag = 0
        
        if channel == 1:
            self.ecan.Tramsmit(USBCAN2, DevIndex, Channel1, can_obj)
        else:
            self.ecan.Tramsmit(USBCAN2, DevIndex, Channel2, can_obj)
        
        time.sleep(0.01)
    
    def shutdown_can(self):
        self.ecan.CloseDevice(USBCAN2, DevIndex)

def getTiming(mbaud):
    if mbaud == "1M":
        return 0, 0x14
    if mbaud == "800k":
        return 0, 0x16
    if mbaud == "666k":
        return 0x80, 0xb6
    if mbaud == "500k":
        return 0, 0x1c
    if mbaud == "400k":
        return 0x80, 0xfa
    if mbaud == "250k":
        return 0x01, 0x1c
    if mbaud == "200k":
        return 0x81, 0xfa
    if mbaud == "125k":
        return 0x03, 0x1c
    if mbaud == "100k":
        return 0x04, 0x1c
    if mbaud == "80k":
        return 0x83, 0xff
    if mbaud == "50k":
        return 0x09, 0x1c

if __name__ == "__main__":
    usbcan = USBCAN()
    
    # write 
    info = {
        'ID': str(101),
        'data': [str(1), str(3), str(0), str(0), str(4), str(0), str(7), str(0)]
    }
    usbcan.write_can(info)
    usbcan.shutdown_can()
    
    # # read
    # info = {
    #     'ID': str(101),
    #     'data': [str(2), str(3), str(1), str(0), str(0), str(0), str(0), str(0)]
    # }
    # usbcan.write_can(info)
    # print(hex(usbcan.received_msg1['data'][3]))
    # usbcan.shutdown_can()