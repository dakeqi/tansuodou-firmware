"""
ESP32-S2/S3 USB HID支持库
支持键盘、鼠标模拟
搭豆智联 2.0 - MicroPython固件
"""

import time

try:
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    from adafruit_hid.mouse import Mouse
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False
    print("⚠️  USB HID库不可用（仅ESP32-S2/S3支持）")


class USBKeyboard:
    """USB键盘模拟类"""
    
    def __init__(self):
        """初始化USB键盘"""
        if not USB_AVAILABLE:
            raise RuntimeError("USB HID not available on this device")
        
        self._keyboard = Keyboard(usb_hid.devices)
        print("⌨️  USB键盘已初始化")
    
    def press(self, key):
        """
        按下按键
        
        Args:
            key: 按键码或字符
        """
        if isinstance(key, str):
            # 字符串转按键码
            if len(key) == 1:
                self._keyboard.press(ord(key.upper()))
            else:
                # 特殊键
                keycode = getattr(Keycode, key.upper(), None)
                if keycode:
                    self._keyboard.press(keycode)
        else:
            self._keyboard.press(key)
    
    def release(self, key):
        """
        释放按键
        
        Args:
            key: 按键码或字符
        """
        if isinstance(key, str):
            if len(key) == 1:
                self._keyboard.release(ord(key.upper()))
            else:
                keycode = getattr(Keycode, key.upper(), None)
                if keycode:
                    self._keyboard.release(keycode)
        else:
            self._keyboard.release(key)
    
    def write(self, text):
        """
        输入文本
        
        Args:
            text: 要输入的文本
        """
        self._keyboard.write(text)
    
    def send(self, *keys):
        """
        发送组合键
        
        Args:
            *keys: 按键列表，例如 send('CTRL', 'C')
        """
        keycodes = []
        for key in keys:
            if isinstance(key, str):
                keycode = getattr(Keycode, key.upper(), None)
                if keycode:
                    keycodes.append(keycode)
            else:
                keycodes.append(key)
        
        if keycodes:
            self._keyboard.send(*keycodes)
    
    def release_all(self):
        """释放所有按键"""
        self._keyboard.release_all()


class USBMouse:
    """USB鼠标模拟类"""
    
    # 鼠标按钮常量
    LEFT_BUTTON = 1
    RIGHT_BUTTON = 2
    MIDDLE_BUTTON = 4
    
    def __init__(self):
        """初始化USB鼠标"""
        if not USB_AVAILABLE:
            raise RuntimeError("USB HID not available on this device")
        
        self._mouse = Mouse(usb_hid.devices)
        print("🖱️  USB鼠标已初始化")
    
    def move(self, x=0, y=0, wheel=0):
        """
        移动鼠标
        
        Args:
            x: X轴移动量（-127到127）
            y: Y轴移动量（-127到127）
            wheel: 滚轮移动量（-127到127）
        """
        self._mouse.move(x, y, wheel)
    
    def click(self, button=LEFT_BUTTON):
        """
        点击鼠标按钮
        
        Args:
            button: 按钮码（LEFT_BUTTON/RIGHT_BUTTON/MIDDLE_BUTTON）
        """
        self._mouse.click(button)
    
    def press(self, button=LEFT_BUTTON):
        """
        按下鼠标按钮
        
        Args:
            button: 按钮码
        """
        self._mouse.press(button)
    
    def release(self, button=LEFT_BUTTON):
        """
        释放鼠标按钮
        
        Args:
            button: 按钮码
        """
        self._mouse.release(button)
    
    def release_all(self):
        """释放所有按钮"""
        self._mouse.release_all()


class USBSerial:
    """USB串口通信类（USB CDC）"""
    
    def __init__(self):
        """初始化USB串口"""
        import sys
        self._serial = sys.stdout
        print("📟 USB串口已初始化")
    
    def write(self, data):
        """
        写入数据
        
        Args:
            data: 要写入的数据（bytes或str）
        """
        if isinstance(data, str):
            data = data.encode()
        self._serial.buffer.write(data)
    
    def read(self, size=-1):
        """
        读取数据
        
        Args:
            size: 读取字节数，-1表示读取所有
        
        Returns:
            bytes: 读取到的数据
        """
        import sys
        return sys.stdin.buffer.read(size)
    
    def readline(self):
        """读取一行"""
        import sys
        return sys.stdin.buffer.readline()


# 全局实例
_keyboard = None
_mouse = None
_serial = None

def keyboard():
    """获取USB键盘实例"""
    global _keyboard
    if _keyboard is None:
        _keyboard = USBKeyboard()
    return _keyboard

def mouse():
    """获取USB鼠标实例"""
    global _mouse
    if _mouse is None:
        _mouse = USBMouse()
    return _mouse

def serial():
    """获取USB串口实例"""
    global _serial
    if _serial is None:
        _serial = USBSerial()
    return _serial


if __name__ == '__main__':
    # 测试代码
    print("USB HID测试")
    print("-" * 40)
    
    if not USB_AVAILABLE:
        print("❌ 此设备不支持USB HID")
        print("   仅ESP32-S2和ESP32-S3支持")
    else:
        # 测试键盘
        try:
            kb = keyboard()
            print("✅ 键盘初始化成功")
            
            # 等待2秒
            print("2秒后将输入 'Hello World'...")
            time.sleep(2)
            kb.write("Hello World\n")
            print("✅ 键盘测试完成")
        except Exception as e:
            print(f"❌ 键盘错误: {e}")
        
        # 测试鼠标
        try:
            m = mouse()
            print("✅ 鼠标初始化成功")
            
            print("2秒后将移动鼠标...")
            time.sleep(2)
            m.move(10, 10)
            print("✅ 鼠标测试完成")
        except Exception as e:
            print(f"❌ 鼠标错误: {e}")
