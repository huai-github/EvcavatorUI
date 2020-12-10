# -*- coding: utf-8 -*-
from tools import *
from threading import Timer
from datetime import datetime
import serialport
import runUI
import gps

g_x1_d = 0
g_y1_d = 0
g_h1_d = 0
g_w1_s = 0
g_x2_d = 0
g_y2_d = 0
g_h2_d = 0
g_w2_s = 0
g_reced_heart = False	# 是否接收到心跳


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


class Reply(object):
	def __init__(self):
		self.start = 0x24
		self.type = 0x03
		self.id = 0x01
		self.len = 0x08
		self.seqnum = 0x00
		self.reply = 0xff		# 0x00接收任务成功，0x01接收任务失败
		self.sumcheck = 0x00
		self.end = 0x0a

	def reply_msg(self, reply):
		reply_buffer = [0x00] * 8
		reply_buffer[0] = self.start
		reply_buffer[1] = self.type
		reply_buffer[2] = self.id
		reply_buffer[3] = self.len
		self.seqnum = self.seqnum + 0x01
		if self.seqnum > 0xff:
			self.seqnum = 0x01
		reply_buffer[4] = self.seqnum
		reply_buffer[5] = reply
		self.sumcheck = sum(reply_buffer[0:6])
		reply_buffer[6] = self.sumcheck
		reply_buffer[7] = self.end
		return reply_buffer


class SendHeadStruct(object):
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
	def __init__(self):
		self.start = 0x24
		self.type = 0x01  	# 数据类型
		self.id = 0x00  	# 挖掘机编号
		self.len = 0x28  	# 数据包中长度
		self.seqnum = 0x00  # 包序列号
		self.x = [0] * 8  # 8B
		self.y = [0] * 8  # 8B
		self.h = [0] * 8  # 8B
		self.reserved = [0] * 9  # 9B
		self.sumcheck = 0x00
		self.end = 0x0a


def send_msg_func(com, headStruct, bodyStruct):
	head = headStruct
	body = bodyStruct

	send_head_buf = [0] * 8
	send_body_buf = [0] * 40

	send_head_buf[0] = head.start
	send_head_buf[1] = head.type
	send_head_buf[2] = head.id
	send_head_buf[3] = head.len
	head.seqnum = head.seqnum + 0x01
	if head.seqnum > 0xff:
		head.seqnum = 0x00
	send_head_buf[4] = head.seqnum
	send_head_buf[5] = head.reserved
	head.sumcheck = sum(send_head_buf[0:6]) & 0xff
	send_head_buf[6] = head.sumcheck
	send_head_buf[7] = head.end

	send_body_buf[0] = body.start
	send_body_buf[1] = body.type
	send_body_buf[2] = body.id
	send_body_buf[3] = body.len
	body.seqnum = body.seqnum + 0x01
	if body.seqnum > 0xff:
		body.seqnum = 0x00
	send_body_buf[4] = body.seqnum

	x_to_could_union = TypeSwitchUnion()
	y_to_could_union = TypeSwitchUnion()
	h_to_could_union = TypeSwitchUnion()

	x_to_could_union.double = gps.g_x
	# print("x_to_could_union.double: ", x_to_could_union.double)
	y_to_could_union.double = gps.g_y
	h_to_could_union.double = gps.g_h

	x_list = x_to_could_union.char_8		# x_list:  b'8\xb8\xf3cF\x19OA'
	y_list = y_to_could_union.char_8
	h_list = h_to_could_union.char_8

	send_body_buf[5:13] = x_list
	# 36, 1, 0, 40, 7, 255, 12, 89, 100, 70, 25, 79, 65, 113, 167, 129, 192, 226, 114, 31, 65, 233, 72, 46, 255, 33, 221, 61, 64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 241, 10
	send_body_buf[13:21] = y_list
	send_body_buf[21:29] = h_list
	send_body_buf[29:38] = body.reserved
	body.checksum = sum(send_body_buf[0:38]) & 0xff
	send_body_buf[38] = body.checksum
	send_body_buf[39] = body.end
	# print("send_body_buf: ", send_body_buf)
	com.send_data(send_head_buf)
	com.send_data(send_body_buf)


class RecTask(object):
	def __init__(self):
		self.start = 0x24  	# b‘\’ 的形式      ‘$’ = 36(十进制) = 24(16进制)
		self.type = 0  		# 数据类型
		self.id = 0  		# 挖掘机编号
		self.len = 0  		# 数据包中长度
		self.seqnum = 0  	# 包序列号
		self.baseHeight = []  # 2Bytes
		self.sectionNum = 0
		self.section = []  	# 不定长
		self.sumcheck = 0
		self.end = 0x0a

	def task_msg_analysis(self, recbuff):
		"""如果校验通过，拆包并保存数据"""
		self.sumcheck = sum(recbuff[0:-2]) 		# 计算校验位
		self.sumcheck = self.sumcheck & 0xff  	# 取sumcheck的最低字节
		if self.sumcheck != recbuff[-2]:  		# 计算出的校验位不等于接收到的校验位
			print("\r\n--check error!!!--\r\n")
			# 发送给上位机校验错误消息
		else:
			self.id = recbuff[2]
			self.len = recbuff[3]
			self.seqnum = recbuff[4]
			self.baseHeight = recbuff[5:7]		  	# baseHeight 2B
			self.sectionNum = recbuff[7]
			self.section = recbuff[8:-2]  			# section为索引: 8--倒数第2位（不包含倒数第二位）
			self.end = recbuff[-1]
			self.sumcheck = recbuff[-2]

	def base_height(self):
		"""得到基准高"""
		base_height_union = TypeSwitchUnion()
		base_height_union.char_2 = self.baseHeight
		return base_height_union.short

	def section_analysis(self, line_n):
		"""
		得到指定的直线段
		line_n: 哪一个直线段
		"""

		lines = [self.section[i:i+54] for i in range(self.sectionNum)]  # 一个直线段作为list的一个元素 [line1,line2,...]
		# lines: [
		# 	b'\x00\x01?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\x14\x14?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\xaa\xbb',
		# 	b'\x01?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\x14\x14?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\xaa\xbb\x00'
		# 	]
		if line_n > self.sectionNum:
			print()
		else:
			no = lines[line_n][0:2]
			x1 = lines[line_n][2:10]
			y1 = lines[line_n][10:18]
			h1 = lines[line_n][18:26]
			w1 = lines[line_n][26:28]
			x2 = lines[line_n][28:36]
			y2 = lines[line_n][36:44]
			h2 = lines[line_n][44:52]
			w2 = lines[line_n][52:54]  # 0-53共54Bytes
			print("no: ", no)
			return no, x1, y1, h1, w1, x2, y2, h2, w2


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
		self.__ack_flag = False

	def heart_msg_analysis(self, recbuff):
		"""保存心跳信息，如果上位机应答返回True"""
		self.id = recbuff[2]
		self.len = recbuff[3]
		self.seqnum = recbuff[4]
		self.ack = recbuff[5]
		self.reserved = recbuff[6]
		if self.ack == 0x00:  # ack信号为0，表示应答
			self.__ack_flag = True
			print("rec heart")

	def send_heart(self, com):
		send_heart_buff = [0] * 8
		send_heart_buff[0] = self.start
		send_heart_buff[1] = self.type
		send_heart_buff[2] = self.id
		send_heart_buff[3] = self.len
		Heart.s_seqnum = Heart.s_seqnum + 0x01
		if Heart.s_seqnum > 0xff:
			Heart.s_seqnum = 0x01
		send_heart_buff[4] = Heart.s_seqnum
		if self.__ack_flag:
			self.__ack_flag = False
			send_heart_buff[5] = 0x00
		send_heart_buff[6] = self.reserved
		send_heart_buff[7] = self.end
		com.send_data(send_heart_buff)


def _4g_thread_func():
	com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0.5)
	task = RecTask()
	heart = Heart()
	reply = Reply()
	x1_union = TypeSwitchUnion()
	y1_union = TypeSwitchUnion()
	h1_union = TypeSwitchUnion()
	w1_union = TypeSwitchUnion()
	x2_union = TypeSwitchUnion()
	y2_union = TypeSwitchUnion()
	h2_union = TypeSwitchUnion()
	w2_union = TypeSwitchUnion()
	head = SendHeadStruct()
	body = SendBodyStruct()
	# 间隔一分钟发送一次心跳
	start = datetime.now().replace(minute=0, second=0, microsecond=0)
	minute = TimeInterval(start, 2, heart.send_heart, [com_4g])
	minute.start()
	minute.cancel()

	while True:
		recbuff = com_4g.read_line()  # 读到回车停止
		# b'$\x02\x01\xff\x01\xa1\xa2\x01\x00\x01?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\x14\x14?kU\xb0\x86hB@\xe0R\xcc\x84\xf1J]@\xe9H.\xff!\xdd=@\xaa\xbb\x9d\n'
		if recbuff[0] == 0x24:  	# 判断数据包头是否正确
			if recbuff[1] == 0x00:  # 心跳包
				heart.heart_msg_analysis(recbuff)
				g_reced_heart = True

			if recbuff[1] == 0x02:  # 任务包
				line_num = 0x00		# 工作直线段

				runUI._4g_threadLock.acquire()		# 加锁
				task.task_msg_analysis(recbuff)		# 校验，保存数据
				task.base_height()

				# 获取一个直线段
				no, x1_union.char_8, y1_union.char_8, h1_union.char_8, w1_union.char_8, \
					x2_union.char_8, y2_union.char_8, h2_union.char_8, w2_union.char_8 = task.section_analysis(line_num)
				if gps.g_line_worked_flag:
					line_num += 0x01
					if line_num > task.sectionNum:
						line_num = 0x00
						# 说明本次接收的任务全部完成，请求上位机发送新任务
						pass

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

				# 回复上位机接收成功
				reply_buff = reply.reply_msg(0x00)
				com_4g.send_data(reply_buff)
		else:
			print("\r\n--head error!!!--\r\n")
			# 回复上位机接收失败
			reply_buff = reply.reply_msg(0x01)
			com_4g.send_data(reply_buff)

		send_msg_func(com_4g, head, body)			# 发送gps信息给上位机

