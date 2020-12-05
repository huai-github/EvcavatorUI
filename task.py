import serialport
from tools import *
import runUI
import time
import gps


class SendHeadStruct:
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


class SendBodyStruct:
	"""上传数据,每帧40B"""

	def __init__(self):
		self.start = 0x24
		self.type = 0x01  # 数据类型
		self.id = 0x00  # 挖掘机编号
		self.len = 0x28  # 数据包中长度
		self.seqnum = 0x00  # 包序列号
		self.x = [0]*8  # 8B
		self.y = [0]*8   # 8B
		self.h = [0]*8  # 8B
		self.reserved = [0] * 9  # 9B
		self.sumcheck = 0x00
		self.end = 0x0a


class RecTask:
	"""接收任务消息"""

	def __init__(self):
		self.start = 36  # ‘$’ = 36(十进制) = 24(16进制)
		self.type = 0  # 数据类型
		self.id = 0  # 挖掘机编号
		self.len = 0  # 数据包中长度
		self.seqnum = 0  # 包序列号
		self.baseHeight = []  # 2B
		self.sectionNum = 0
		self.section = []  # 不定长
		self.sumcheck = 0
		self.end = '0a'

	def task_msg_analysis(self, recbuff):
		if self.start == recbuff[0]:  # 判断头是否正确
			self.type = recbuff[1]
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
		else:
			print("\r\nhead error!!!\r\n")

	def section_analysis(self):
		for i in range(len(self.section)):
			no = self.section[(i + 0):(i + 2)]
			x1 = self.section[(i + 2):(i + 10)]
			y1 = self.section[(i + 10):(i + 18)]
			h1 = self.section[(i + 18):(i + 26)]
			w1 = self.section[(i + 26):(i + 28)]
			x2 = self.section[(i + 28):(i + 36)]
			y2 = self.section[(i + 36):(i + 44)]
			h2 = self.section[(i + 44):(i + 52)]
			w2 = self.section[(i + 52):(i + 54)]

			return no, x1, y1, h1, w1, x2, y2, h2, w2  # return在循环里面,第一次返回一次


x1_d = 0
y1_d = 0
h1_d = 0
w1_s = 0
x2_d = 0
y2_d = 0
h2_d = 0
w2_s = 0


def task_rec_thread_func():
	_4G_COM = "com21"
	task = RecTask()
	com_4g = serialport.SerialPortCommunication(_4G_COM, 115200, 0.5)
	task_buffer = com_4g.read_line()  # type = bytes
	# print(task_buffer)
	task.task_msg_analysis(task_buffer)
	section_one = task.section_analysis()  # 返回一个直线段
	# print(section_one)  # tuple
	runUI.rectask_threadLock.acquire()  # 加锁
	# 联合体转换数据类型
	global x1_d, y1_d, h1_d, w1_s, x2_d, y2_d, h2_d, w2_s
	x1_union = TypeSwitchUnion()
	x1_union.char = section_one[1]
	x1_d = x1_union.int

	y1_union = TypeSwitchUnion()
	y1_union.char = section_one[2]
	y1_d = y1_union.int

	h1_union = TypeSwitchUnion()
	h1_union.char = section_one[3]
	h1_d = h1_union.int

	w1_union = TypeSwitchUnion()
	w1_union.char = section_one[4]
	w1_s = w1_union.short

	x2_union = TypeSwitchUnion()
	x2_union.char = section_one[5]
	x2_d = x2_union.int

	y2_union = TypeSwitchUnion()
	y2_union.char = section_one[6]
	y2_d = y2_union.int

	h2_union = TypeSwitchUnion()
	h2_union.char = section_one[7]
	h2_d = h2_union.int

	w2_union = TypeSwitchUnion()
	w2_union.char = section_one[8]
	w2_s = w2_union.short
	runUI.rectask_threadLock.release()  # 解锁

	return x1_d, y1_d, h1_d, w1_s, x2_d, y2_d, h2_d, w2_s


def heart_rec__thead_func():
	_4G_COM = "com21"
	com_4g = serialport.SerialPortCommunication(_4G_COM, 115200, 0.5)
	heart_rec_buf = com_4g.read_line()
	print(heart_rec_buf)
	if heart_rec_buf[0] == 36:
		if heart_rec_buf[5] == 00:  # ack为0，表示有应答
			print("heart succ")


def heart_send_thread_func():
	_4G_COM = "com21"
	com_4g = serialport.SerialPortCommunication(_4G_COM, 115200, 0.5)
	heart_send_buf = [0x36, 0x00, 0x01, 0x08, 0x01, 0x00, 0x00, 0x0a]
	while True:
		com_4g.send_data(heart_send_buf, len(heart_send_buf))
		time.sleep(60)
		heart_send_buf[4] = heart_send_buf[4] + 0x01  # seqnum


def task_send_thread_func():
	_4G_COM = "com21"
	send_head_buf = [0] * 8
	send_body_buf = [0] * 40
	com_4g = serialport.SerialPortCommunication(_4G_COM, 115200, 0)
	head = SendHeadStruct()
	body = SendBodyStruct()

	for i in range(100):  # 条件？？？
		send_head_buf[0] = head.start
		send_head_buf[1] = head.type
		send_head_buf[2] = head.id
		send_head_buf[3] = head.len
		head.seqnum = head.seqnum + 0x01
		send_head_buf[4] = head.seqnum
		send_head_buf[5] = head.reserved
		head.sumcheck = sum(send_head_buf[0:6])
		send_head_buf[6] = head.sumcheck
		send_head_buf[7] = head.end

		send_body_buf[0] = body.start
		send_body_buf[1] = body.type
		send_body_buf[2] = body.id
		send_body_buf[3] = body.len
		body.seqnum = body.seqnum + 0x01
		send_body_buf[4] = body.seqnum
		# gps接收的是bytes类型，这里要转换成int类型
		for a in range(8):
			body.x[a] = int.from_bytes(gps.lat[a], byteorder='little', signed=False)
		for b in range(8):
			body.y[b] = int.from_bytes(gps.lon[b], byteorder='little', signed=False)
		for c in range(8):
			body.h[c] = int.from_bytes(gps.alt[c], byteorder='little', signed=False)

		send_body_buf[5:13] = body.x
		send_body_buf[13:21] = body.y
		send_body_buf[21:29] = body.h
		send_body_buf[29:38] = body.reserved
		body.checksum = sum(send_body_buf[0:38]) & 0xff
		send_body_buf[38] = body.checksum

		send_body_buf[39] = body.end

		com_4g.send_data(send_head_buf)
		com_4g.send_data(send_body_buf)



##############################################################################################################

if __name__ == "__main__":
	gps.gps_thread_fun()
	task_send_thread_func()
