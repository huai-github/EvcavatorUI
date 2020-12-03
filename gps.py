from serialport import SerialPortCommunication
from tools import *


class LatLonAlt:
	def __init__(self):
		self.latitude = 0
		self.longitude = 0
		self.altitude = 0


class GPSINSData:
	def __init__(self):
		self.head = [b'\xaa', b'\x33'] 		# 2B deviation 0-2
		self.length = [0x00]*2			# 2B deviation 4-6
		self.latitude =[0x00]*8  		# 8B deviation 24
		self.longitude = [0x00]*8  		# 8B deviation 32
		self.altitude = [0x00]*8  		# 8B deviation 40
		self.checksum = 0x00	 		# 2B deviation 136
		self.xor_check = 0x00         	# 定义异或校验返回值

	def gps_msg_analysis(self, recbuff):
		if (recbuff[0] == self.head[0]) and (recbuff[1] == self.head[1]):
			self.length = recbuff[4:6]
			self.latitude = recbuff[24:32]
			self.longitude = recbuff[32:40]
			self.altitude = recbuff[40:48]
			self.checksum = recbuff[136:138]
			self.checksum = self.checksum[0] + self.checksum[1]
			# print(self.checksum)

			for i in range(len(recbuff) -2):
				recbuff[i] = int.from_bytes(recbuff[i], byteorder='big', signed=False)  # bytes转int
				self.xor_check = self.xor_check ^ recbuff[i]

			self.xor_check = self.xor_check.to_bytes(length=2, byteorder='little', signed=False)
			print((self.xor_check))

			if self.xor_check == self.checksum:  # 数据包异或校验通过
				if recbuff[104] == b'\x04':  # gps信号稳定
					print("The signal of gps is stable！\r\n")
				else:
					print("The signal of gps is unstable！\r\n")
			else:
				print("checksum error!!!\r\n")
				return

		else:
			print("data head error!!!\r\n")
			return

	def gps_typeswitch(self):
		gps_switch_lat = TypeSwitchUnion()
		gps_switch_lat.char = self.latitude

		gps_switch_lon = TypeSwitchUnion()
		gps_switch_lon.char = self.longitude

		gps_switch_alt = TypeSwitchUnion()
		gps_switch_alt.char = self.altitude
		print("%s\t%s\t%s\t" %gps_switch_lat.double,  gps_switch_lon.double,  gps_switch_alt.double)
		return gps_switch_lat.double,  gps_switch_lon.double,  gps_switch_alt.double  # 用的时候加*

##############################################################################################################
GPS_COM = "com21"

if __name__ == "__main__":
	gps_rec_buffer = []
	gps_data = GPSINSData()
	gps_com = SerialPortCommunication(GPS_COM, 115200, 0.5)
	gps_com.rec_data(gps_rec_buffer, 138) # int
	print(gps_rec_buffer)
	gps_data.gps_msg_analysis(gps_rec_buffer)
	# gps_data.gps_typeswitch()

