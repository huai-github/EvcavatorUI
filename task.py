# -*- coding: utf-8 -*-
from tools import *
from threading import Timer
from datetime import datetime
import serialport
import runUI

g_x1_d = 0
g_y1_d = 0
g_h1_d = 0
g_w1_s = 0
g_x2_d = 0
g_y2_d = 0
g_h2_d = 0
g_w2_s = 0


class TimeInterval(object):
	def __init__(self, start_time, interval, callback_proc, args=None, kwargs=None):
		self.__timer = None
		self.__start_time = start_time
		self.__interval = interval
		self.__callback_pro = callback_proc
		self.__args = args if args is not None else []
		self.__kwargs = kwargs if kwargs is not None else {}

	def exec_callback(self, args=None, kwargs=None):
		self.__callback_pro(*self.__args, **self.__kwargs)
		self.__timer = Timer(self.__interval, self.exec_callback)
		self.__timer.start()

	def start(self):
		interval = self.__interval - (datetime.now().timestamp() - self.__start_time.timestamp())
		# print( interval )
		self.__timer = Timer(interval, self.exec_callback)
		self.__timer.start()

	def cancel(self):
		self.__timer.cancel()
		self.__timer = None


class SendHeadStruct(object):
	"""上传头部"""

	def __init__(self):
		self.start = 0x24
		self.type = 0x01
		self.id = 0x01
		self.len = 0x08
		self.seqnum = 0x00
		self.reserved = 0x00
		self.sumcheck = 0x00
		self.end = 0x0a


class SendBodyStruct(object):
	"""上传数据,每帧40B"""

	def __init__(self):
		self.start = 0x24
		self.type = 0x01  # 数据类型
		self.id = 0x00  # 挖掘机编号
		self.len = 0x28  # 数据包中长度
		self.seqnum = 0x00  # 包序列号
		self.x = [0] * 8  # 8B
		self.y = [0] * 8  # 8B
		self.h = [0] * 8  # 8B
		self.reserved = [0] * 9  # 9B
		self.sumcheck = 0x00
		self.end = 0x0a


class RecTask(object):
	def __init__(self):
		self.start = 36  # b‘\’ 的形式      ‘$’ = 36(十进制) = 24(16进制)
		self.type = 0  # 数据类型
		self.id = 0  # 挖掘机编号
		self.len = 0  # 数据包中长度
		self.seqnum = 0  # 包序列号
		self.baseHeight = []  # 2B
		self.sectionNum = 0
		self.section = []  # 不定长
		self.sumcheck = 0
		self.end = 0x0a

	def task_msg_analysis(self, recbuff):
		self.id = recbuff[2]
		self.len = recbuff[3]
		self.seqnum = recbuff[4]
		self.baseHeight = recbuff[5:7]  # baseHeight 2B
		self.sectionNum = recbuff[7]
		self.section = recbuff[8:-2]  # section为索引: 8--倒数第2位（不包含倒数第二位）
		self.sumcheck = sum(recbuff[0:-2])  # 计算校验位
		self.sumcheck = self.sumcheck & 0xff  # 取sumcheck的最低字节
		if self.sumcheck != recbuff[-2]:  # 计算出的校验位不等于接受到的校验位
			print("\r\ncheck error!!!\r\n")
		else:
			self.sumcheck = recbuff[-2]
		self.end = recbuff[-1]

	def section_analysis(self):
		for i in range(0, len(self.section), 54):
			no = self.section[(i + 0):(i + 2)]
			x1 = self.section[(i + 2):(i + 10)]
			y1 = self.section[(i + 10):(i + 18)]
			h1 = self.section[(i + 18):(i + 26)]
			w1 = self.section[(i + 26):(i + 28)]
			x2 = self.section[(i + 28):(i + 36)]
			y2 = self.section[(i + 36):(i + 44)]
			h2 = self.section[(i + 44):(i + 52)]
			w2 = self.section[(i + 52):(i + 54)]  # 0-53共54B

			return no, x1, y1, h1, w1, x2, y2, h2, w2  # return在循环里面,每一次返回一次


class Heart(object):
	s_seqnum = 0x00  # 静态变量

	def __init__(self):
		self.start = 0x24
		self.type = 0x00
		self.id = 0x01  # 设备号，待定
		self.len = 0x08
		self.seqnum = 0x00
		self.ack = 0xff
		self.reserved = 0x00
		self.end = 0x0a
		self.__ack_flags = False

	def heart_msg_analysis(self, recbuff):
		self.id = recbuff[2]
		self.len = recbuff[3]
		self.seqnum = recbuff[4]
		self.ack = recbuff[5]
		self.reserved = recbuff[6]
		if self.ack == 0x00:  # ack信号为0，表示应答
			self.__ack_flags = True
			print("rec heart")

	def send_heart(self, com):
		send_heart_buff = [0] * 8
		send_heart_buff[0] = self.start
		send_heart_buff[1] = self.type
		send_heart_buff[2] = self.id
		send_heart_buff[3] = self.len
		Heart.s_seqnum = Heart.s_seqnum + 0x01
		if Heart.s_seqnum > 0xff:
			Heart.s_seqnum = 0x00
		send_heart_buff[4] = Heart.s_seqnum
		if self.__ack_flags:
			self.__ack_flags = False
			send_heart_buff[5] = 0x00
		send_heart_buff[6] = self.reserved
		send_heart_buff[7] = self.end
		com.send_data(send_heart_buff)


def _4g_thread_func():
	com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0.5)
	task = RecTask()
	heart = Heart()
	x1_union = TypeSwitchUnion()
	y1_union = TypeSwitchUnion()
	h1_union = TypeSwitchUnion()
	w1_union = TypeSwitchUnion()
	x2_union = TypeSwitchUnion()
	y2_union = TypeSwitchUnion()
	h2_union = TypeSwitchUnion()
	w2_union = TypeSwitchUnion()

	start = datetime.now().replace(minute=0, second=0, microsecond=0)
	minute = TimeInterval(start, 10, heart.send_heart, [com_4g])  # 间隔10秒发送一次心跳
	minute.start()
	minute.cancel()

	while True:
		recbuff = com_4g.read_line()  # 读到回车停止
		# b'$\x02\x01\xff\x01\xa1\xa2\x01\x00\x01?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\x14\x14?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\xaa\xbb\x9d\n'
		if recbuff[0] == 0x24:  # 判断数据包头是否正确
			if recbuff[1] == 0x00:  # 心跳包
				# 解析心跳包
				heart.heart_msg_analysis(recbuff)

			if recbuff[1] == 0x02:  # 任务包
				runUI._4g_threadLock.acquire()		# 加锁
				task.task_msg_analysis(recbuff)
				no, x1_union.char, y1_union.char, h1_union.char, w1_union.char, \
				x2_union.char, y2_union.char, h2_union.char, w2_union.char = task.section_analysis()  # 返回一个直线段
				global g_x1_d, g_y1_d, g_h1_d, g_w1_s, g_x2_d, g_y2_d, g_h2_d, g_w2_s
				g_x1_d = x1_union.int
				g_y1_d = y1_union.int
				g_h1_d = h1_union.int
				g_w1_s = w1_union.short
				g_x2_d = x2_union.int
				g_y2_d = y2_union.int
				g_h2_d = h2_union.int
				g_w2_s = w2_union.short
				runUI._4g_threadLock.release()		# 解锁
				print(g_x1_d)

		else:
			print("\r\nhead error!!!\r\n")


##############################################################################################################
# if __name__ == "__main__":
# 	gps.gps_thread_fun()
# 	if gps.g_worked_flag:
# 		gps.g_worked_flag = False
# 	msg_send_thread_func()
