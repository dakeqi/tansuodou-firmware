"""
ESP32 蓝牙BLE支持库
支持 ESP32/ESP32-S3/ESP32-C3
搭豆智联 2.0 - MicroPython固件
"""

import bluetooth
from micropython import const
import struct
import time

# BLE事件常量
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)


class BLE:
    """蓝牙BLE管理类"""
    
    def __init__(self, name="ESP32_BLE"):
        """
        初始化BLE
        
        Args:
            name: 蓝牙设备名称
        """
        self._ble = bluetooth.BLE()
        self._name = name
        self._connections = set()
        self._write_callback = None
        self._read_callback = None
        self._rx_buffer = bytearray()
        
        # UART服务和特征值
        self._uart_service = None
        self._rx_handle = None
        self._tx_handle = None
        
        print(f"🔵 BLE初始化: {name}")
    
    def active(self, state=True):
        """
        激活或停用BLE
        
        Args:
            state: True激活，False停用
        """
        self._ble.active(state)
        if state:
            self._ble.irq(self._irq_handler)
            print("✅ BLE已激活")
        else:
            print("⏹️  BLE已停用")
    
    def _irq_handler(self, event, data):
        """BLE事件处理器"""
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print(f"📱 客户端已连接: {conn_handle}")
        
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print(f"📱 客户端已断开: {conn_handle}")
            # 重新开始广播
            self.advertise()
        
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            
            if value_handle == self._rx_handle:
                # 接收到数据
                self._rx_buffer.extend(value)
                if self._write_callback:
                    self._write_callback(value)
        
        elif event == _IRQ_GATTS_READ_REQUEST:
            conn_handle, value_handle = data
            if self._read_callback:
                value = self._read_callback()
                if value:
                    self._ble.gatts_write(value_handle, value)
    
    def config(self, **kwargs):
        """
        配置BLE参数
        
        Args:
            gap_name: 设备名称
            mtu: 最大传输单元
        """
        if 'gap_name' in kwargs:
            self._name = kwargs['gap_name']
            self._ble.config(gap_name=self._name)
            print(f"📝 设备名称: {self._name}")
        
        if 'mtu' in kwargs:
            self._ble.config(mtu=kwargs['mtu'])
            print(f"📝 MTU: {kwargs['mtu']}")
    
    def setup_uart_service(self):
        """
        设置UART服务（Nordic UART Service）
        用于简单的数据收发
        """
        # Nordic UART Service UUID
        UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
        UART_TX_UUID = bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
        UART_RX_UUID = bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
        
        # 注册UART服务
        UART_SERVICE = (
            UART_UUID,
            (
                (UART_TX_UUID, bluetooth.FLAG_NOTIFY),
                (UART_RX_UUID, bluetooth.FLAG_WRITE),
            ),
        )
        
        ((self._tx_handle, self._rx_handle,),) = self._ble.gatts_register_services((UART_SERVICE,))
        print("✅ UART服务已注册")
    
    def advertise(self, interval_us=100000, connectable=True):
        """
        开始广播
        
        Args:
            interval_us: 广播间隔（微秒），默认100ms
            connectable: 是否可连接
        """
        # 广播数据
        name_bytes = self._name.encode()
        adv_data = bytearray(b'\x02\x01\x06') + bytearray([len(name_bytes) + 1, 0x09]) + name_bytes
        
        self._ble.gap_advertise(interval_us, adv_data=adv_data, connectable=connectable)
        print(f"📡 开始广播: {self._name}")
    
    def stop_advertise(self):
        """停止广播"""
        self._ble.gap_advertise(None)
        print("📡 停止广播")
    
    def send(self, data):
        """
        发送数据到所有已连接的客户端
        
        Args:
            data: 要发送的数据（bytes或str）
        """
        if isinstance(data, str):
            data = data.encode()
        
        if not self._tx_handle:
            raise RuntimeError("UART service not setup. Call setup_uart_service() first")
        
        for conn_handle in self._connections:
            try:
                self._ble.gatts_notify(conn_handle, self._tx_handle, data)
            except Exception as e:
                print(f"❌ 发送失败 {conn_handle}: {e}")
    
    def receive(self):
        """
        接收数据
        
        Returns:
            bytes: 接收到的数据
        """
        if self._rx_buffer:
            data = bytes(self._rx_buffer)
            self._rx_buffer.clear()
            return data
        return b''
    
    def on_write(self, callback):
        """
        设置接收数据回调
        
        Args:
            callback: 回调函数，参数为接收到的数据
        """
        self._write_callback = callback
    
    def on_read(self, callback):
        """
        设置读取数据回调
        
        Args:
            callback: 回调函数，应返回要发送的数据
        """
        self._read_callback = callback
    
    def is_connected(self):
        """
        检查是否有客户端连接
        
        Returns:
            bool: True表示有连接
        """
        return len(self._connections) > 0
    
    def disconnect_all(self):
        """断开所有连接"""
        for conn_handle in list(self._connections):
            try:
                self._ble.gap_disconnect(conn_handle)
            except Exception as e:
                print(f"❌ 断开失败 {conn_handle}: {e}")


# 全局BLE实例
_ble_instance = None

def init(name="ESP32_BLE"):
    """
    初始化BLE
    
    Args:
        name: 蓝牙设备名称
    
    Returns:
        BLE: BLE实例
    """
    global _ble_instance
    if _ble_instance is None:
        _ble_instance = BLE(name)
        _ble_instance.active(True)
        _ble_instance.setup_uart_service()
    return _ble_instance

def get():
    """获取BLE实例"""
    global _ble_instance
    if _ble_instance is None:
        raise RuntimeError("BLE not initialized. Call init() first")
    return _ble_instance


if __name__ == '__main__':
    # 测试代码
    print("BLE测试")
    print("-" * 40)
    
    # 初始化BLE
    ble = init("TestDevice")
    
    # 设置接收回调
    def on_receive(data):
        print(f"收到数据: {data}")
        # 回显
        ble.send(b"Echo: " + data)
    
    ble.on_write(on_receive)
    
    # 开始广播
    ble.advertise()
    
    print("BLE已就绪，等待连接...")
    
    # 主循环
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止BLE")
        ble.disconnect_all()
        ble.stop_advertise()
        ble.active(False)
