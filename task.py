import serialport
from tools import *
import runUI
import time
import gps

g_x1_d = 0
g_y1_d = 0
g_h1_d = 0
g_w1_s = 0
g_x2_d = 0
g_y2_d = 0
g_h2_d = 0
g_w2_s = 0

g_rec_task_flag = False
g_rec_heart_flag = False
g_send_task_flag = False
g_send_heart_flag = False

g_task_reced_flag = False

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
		for i in range(0, len(self.section), 54):
			no = self.section[(i + 0):(i + 2)]
			x1 = self.section[(i + 2):(i + 10)]
			y1 = self.section[(i + 10):(i + 18)]
			h1 = self.section[(i + 18):(i + 26)]
			w1 = self.section[(i + 26):(i + 28)]
			x2 = self.section[(i + 28):(i + 36)]
			y2 = self.section[(i + 36):(i + 44)]
			h2 = self.section[(i + 44):(i + 52)]
			w2 = self.section[(i + 52):(i + 54)]		# 0-53共54B

			return no, x1, y1, h1, w1, x2, y2, h2, w2  # return在循环里面,每一次返回一次


def task_rec_thread_func():
	# runUI.rectask_threadLock.acquire()  # 加锁
	global g_rec_task_flag, g_rec_heart_flag
	g_rec_task_flag = True  # 开始接收任务，停止接收心跳
	g_rec_heart_flag = False

	if g_rec_task_flag:
		g_rec_task_flag = False # 还需要声明吗？？？
		task = RecTask()
		x1_union = TypeSwitchUnion()
		y1_union = TypeSwitchUnion()
		h1_union = TypeSwitchUnion()
		w1_union = TypeSwitchUnion()
		x2_union = TypeSwitchUnion()
		y2_union = TypeSwitchUnion()
		h2_union = TypeSwitchUnion()
		w2_union = TypeSwitchUnion()
		com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0.5)  # read_line必须设置超时时间
		task_buffer = com_4g.read_line()  # type = bytes
		com_4g.close_com()

		task.task_msg_analysis(task_buffer)
		no, x1_union.char, y1_union.char, h1_union.char, w1_union.char, \
			x2_union.char, y2_union.char, h2_union.char, w2_union.char = task.section_analysis()  # 返回一个直线段
		# 联合体转换数据类型
		global g_x1_d, g_y1_d, g_h1_d, g_w1_s, g_x2_d, g_y2_d, g_h2_d, g_w2_s
		g_x1_d = x1_union.int
		g_y1_d = y1_union.int
		g_h1_d = h1_union.int
		g_w1_s = w1_union.short
		g_x2_d = x2_union.int
		g_y2_d = y2_union.int
		g_h2_d = h2_union.int
		g_w2_s = w2_union.short
		print(g_x1_d)
		print(g_y1_d)
		print(g_h1_d)
		print(g_w1_s)


	# runUI.rectask_threadLock.release()  # 解锁


def heart_rec_thead_func():
	global g_rec_task_flag

	if g_rec_task_flag:
		runUI.heart_rec_threadLock.acquire()
		com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0.5)
		heart_rec_buf = com_4g.read_line()
		print(heart_rec_buf)
		if heart_rec_buf[0] == 36:
			if heart_rec_buf[5] == 00:  # ack为0，表示有应答
				print("heart succ")
		runUI.heart_rec_threadLock.release()

def heart_send_thread_func():
	com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0)
	heart_send_buf = [0x36, 0x00, 0x01, 0x08, 0x01, 0x00, 0x00, 0x0a]
	while True:
		runUI.heart_send_threadLock.acquire()
		com_4g.send_data(heart_send_buf)
		time.sleep(5)
		heart_send_buf[4] = heart_send_buf[4] + 0x01  # seqnum
		runUI.heart_send_threadLock.release()

def task_send_thread_func():
	send_head_buf = [0] * 8
	send_body_buf = [0] * 40
	com_4g = serialport.SerialPortCommunication(runUI.g_4G_COM, 115200, 0.5)
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
			body.x[a] = int.from_bytes(gps.g_lat[a], byteorder='little', signed=False)
		for b in range(8):
			body.y[b] = int.from_bytes(gps.g_lon[b], byteorder='little', signed=False)
		for c in range(8):
			body.h[c] = int.from_bytes(gps.g_alt[c], byteorder='little', signed=False)

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
	# heart_rec__thead_func()
	# gps.gps_thread_fun()
	heart_send_thread_func()
	# if gps.g_worked_flag:
	# 	gps.g_worked_flag = False
	# 	task_send_thread_func()
