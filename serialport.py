import binascii

import serial
import serial.tools.list_ports


class SerialPortCommunication():
	def __init__(self, com, bps, timeout):
		self.port = com
		self.bps = bps
		self.timeout = timeout
		global ret
		try:
			# 打开串口，并得到串口对象
			self.com = serial.Serial(self.port, self.bps, timeout=self.timeout)
			# 判断是否打开成功
			if (self.com.is_open):
				ret = True
		except Exception as e:
			print("---open error---：", e)

	# 打印设备基本信息
	def port_msg(self):
		print(self.com.name)  # 设备名字
		print(self.com.port)  # 读或者写端口
		print(self.com.baudrate)  # 波特率
		print(self.com.bytesize)  # 字节大小
		print(self.com.parity)  # 校验位
		print(self.com.stopbits)  # 停止位
		print(self.com.timeout)  # 读超时设置
		print(self.com.writeTimeout)  # 写超时
		print(self.com.xonxoff)  # 软件流控
		print(self.com.rtscts)  # 软件流控
		print(self.com.dsrdtr)  # 硬件流控
		print(self.com.interCharTimeout)  # 字符间隔超时

	# 打开串口
	def open_com(self):
		self.com.open()

	# 关闭串口
	def close_com(self):
		self.com.close()

	# 打印可用串口列表
	@staticmethod
	def print_used_com():
		port_list = list(serial.tools.list_ports.comports())
		print(port_list)

	# 接收指定大小的数据
	# 从串口读size个字节。如果指定超时，则可能在超时后返回较少的字节；如果没有指定超时，则会一直等到收完指定的字节数。
	def read_size(self, size):
		return self.com.read(size=size)

	# 接收一行数据
	# 使用readline()时应该注意：打开串口时应该指定超时，否则如果串口没有收到新行，则会一直等待。
	# 如果没有超时，readline会报异常。
	def read_line(self):
		return self.com.readline()

	def send_data(self, send_buffer, send_len):
		for i in range(send_len):
			data_byte = int(send_buffer[i]).to_bytes(length=1, byteorder='big', signed=True)
			self.com.write(data_byte)

	def rec_data(self, rec_buff, rec_len, way=0):
		while True:
			try:
				if self.com.in_waiting:  # in_waiting返回接收缓冲区的字节数
					if way == 0:
						# for i in range(self.com.in_waiting):
						for i in range(rec_len):
							data = self.read_size(1).hex()
							if data != "0a":
								rec_buff.append(data)
							else:
								return
					# if way == 1:  # 整体接收
					# 	# data = self.com.read(self.com.in_waiting).decode("utf-8")#方式一
					# 	rec_buff = self.com.read_all()
					return rec_buff

			except Exception as e:
				print("rec error：", e)

#####################################################################################
# 宏定义
_4G_COM = "com21"

if __name__ == '__main__':
	com_rec_buf = []
	com_send_buf = [12, 22, 33, 44, 55, 66, 77, 88] # test

	test_port = SerialPortCommunication(_4G_COM, 115200, 0)
	if ret:
		test_port.rec_data(com_rec_buf, 1024, 0)
		print(com_rec_buf)

		# test_port.send_data(com_send_buf, len(com_send_buf))
	test_port.close_com()
