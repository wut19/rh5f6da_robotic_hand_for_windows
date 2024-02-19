from usbcan import USBCAN
import math
import time

class RoboticHand:
    def __init__(self, is_right=True) -> None:
        self.usbcan = USBCAN()
        self.id = '101' if is_right else '102'
        self.joint_map = {
            'thumb_1': '0x01',
            'thumb_0': '0x02',
            'index_finger': '0x03',
            'middle_finger': '0x04',
            'ring_finger': '0x05',
            'little_finger': '0x06'
        }
        self.joints = list(self.joint_map.keys())
        self.info_type_map = {
            'joint_pos': '0x01',
            'joint_target_pos': '0x05',
            'torque': '0x0B'
        }
        self.readable_info_types = list(self.info_type_map.keys())
        
        print('-----------------------------------------------------')
        print(f'Available joints: {self.joints}')
        print(f'Readable info types: {self.readable_info_types}')
        print('-----------------------------------------------------')
        
    def shutdown(self):
        self.usbcan.shutdown_can()
        
    def write_joint_pos(self, joint: str, pos: float, velocity:float=1., torque: float=0.5):
        '''control joints of hands
            joint: joint name, available names are in self.joints (note that thumb_0 refers to the joint close to palm)
            pos: target control position. Normalized to [0, 1]
            velocity: target control velocity. Normalized to [0, 1]
            torque: torque when control, actually is the maxinum voltage. Normalized to [0, 1]
        '''
        data = []
        data.append('1') # control command, data[0]
        
        if not joint in self.joints:
            raise RuntimeError(f'No joint named {joint}!!!')
        joint_index = self.joint_map.get(joint)
        data.append(joint_index)    # joint index, data[1]
        
        # unnormalize position
        pos_degree = math.floor(pos * 90)
        if pos_degree == 90:
            pos_degree = 89
            pos_minute = 60
        else:
            pos_minute = math.floor((pos * 90 - pos_degree) * 60)
        data.append(str(hex(pos_degree)))   # position in degree, data[2]
        data.append(str(hex(pos_minute)))   # position in minute, data[3]
        
        # unnormalize velocity
        time = int(1 / (velocity + 0.2) * 4)
        data.append(str(hex(time))) # time to reach target position, data[4]
        data.append(str('0'))       # don't use here, data[5]
        
        # unnormalize torque
        torque = int(torque * 205) + 50
        data.append(str(hex(torque))) # torque, data[6]
        
        data.append('0')    # not used, data[7]
        
        info = {
            'ID': self.id,
            'data': data
        }
        
        self.usbcan.write_can(info=info)
        
    def read_joint_info(self, joint:str, info_type:str):
        assert joint in self.joints and info_type in self.readable_info_types, "Make sure the joint name and info type are available !!!"
        
        joint_index = self.joint_map.get(joint)
        info_type_index = self.info_type_map.get(info_type)
        data = ['0x02', joint_index, info_type_index, '0x00', '0x00', '0x00', '0x00', '0x00']
        
        info = {
            'ID': self.id,
            'data': data
        }
        self.usbcan.write_can(info)
        print(self.usbcan.received_msg1['data'][0], self.usbcan.received_msg1['data'][1])
        assert self.usbcan.received_msg1['data'][0] == 0 and self.usbcan.received_msg1['data'][1] == joint_index, 'RECEIVE ERROR !!!'
        
        rec_data1 = self.usbcan.received_msg1['data'][2]
        rec_data2 = self.usbcan.received_msg1['data'][3]
        
        if info_type == 'joint_pos' or info_type == 'joint_target_pos':
            pos = float(rec_data1) + float(rec_data2) / 60.
            normalized_pos = pos / 90
            return info_type, pos, normalized_pos
        elif info_type == 'torque':
            voltage = float(rec_data2) / 255. * 12.
            voltage = voltage if rec_data1 == 0x01 else -voltage
            normalized_torque = voltage / 12.
            return info_type, voltage, normalized_torque
        else:
            KeyError('No this info type !!!')
            
    def reset(self):
        for joint in self.joints:
            self.write_joint_pos(joint,0)
    
    def grasp(self):
        for joint in self.joints:
            self.write_joint_pos(joint, 0.5)
            
if __name__ == '__main__':
    hand = RoboticHand()
    hand.reset()
    print(hand.read_joint_info(joint='index_finger', info_type='joint_pos'))
    time.sleep(1)
    hand.grasp()
    print(hand.read_joint_info(joint='index_finger', info_type='joint_pos'))
    time.sleep(1)
    hand.reset()
    print(hand.read_joint_info(joint='index_finger', info_type='joint_pos'))
    time.sleep(1)
    hand.shutdown()