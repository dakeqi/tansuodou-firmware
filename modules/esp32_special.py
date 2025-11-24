"""
ESP32 特殊功能支持库
支持触摸引脚、霍尔传感器、DAC输出
搭豆智联 2.0 - MicroPython固件
"""

from machine import Pin, TouchPad, DAC
import esp32

class Touch:
    """触摸引脚管理类"""
    
    # 触摸引脚映射表 (ESP32/S2/S3)
    TOUCH_PINS = {
        0: 4,   # Touch0 -> GPIO4
        1: 0,   # Touch1 -> GPIO0
        2: 2,   # Touch2 -> GPIO2
        3: 15,  # Touch3 -> GPIO15
        4: 13,  # Touch4 -> GPIO13
        5: 12,  # Touch5 -> GPIO12
        6: 14,  # Touch6 -> GPIO14
        7: 27,  # Touch7 -> GPIO27
        8: 33,  # Touch8 -> GPIO33
        9: 32   # Touch9 -> GPIO32
    }
    
    def __init__(self):
        """初始化触摸引脚字典"""
        self._touchpads = {}
    
    def read(self, touch_num):
        """
        读取触摸引脚的电容值
        
        Args:
            touch_num: 触摸引脚编号 (0-9)
        
        Returns:
            int: 电容值，数值越小表示触摸越强
        """
        if touch_num not in self.TOUCH_PINS:
            raise ValueError(f"Invalid touch pin: {touch_num}. Must be 0-9")
        
        # 懒加载：首次使用时才创建 TouchPad 对象
        if touch_num not in self._touchpads:
            gpio_num = self.TOUCH_PINS[touch_num]
            pin = Pin(gpio_num)
            self._touchpads[touch_num] = TouchPad(pin)
        
        return self._touchpads[touch_num].read()
    
    def is_touched(self, touch_num, threshold=300):
        """
        检测触摸引脚是否被触摸
        
        Args:
            touch_num: 触摸引脚编号 (0-9)
            threshold: 触摸阈值，默认300（需根据实际环境调整）
        
        Returns:
            bool: True表示被触摸
        """
        return self.read(touch_num) < threshold


class HallSensor:
    """霍尔传感器类（仅ESP32经典版支持）"""
    
    @staticmethod
    def read():
        """
        读取内置霍尔传感器的值
        
        Returns:
            int: 霍尔传感器读数，正负值表示磁场方向
        
        Note:
            霍尔传感器使用GPIO36和GPIO39，使用时这两个引脚不能用于其他功能
        """
        try:
            return esp32.hall_sensor()
        except AttributeError:
            raise RuntimeError("Hall sensor is only available on ESP32 (classic)")


class DACOutput:
    """DAC模拟输出类（ESP32/S2支持）"""
    
    # DAC引脚映射
    DAC_PINS = {
        1: 25,  # DAC1 -> GPIO25
        2: 26   # DAC2 -> GPIO26
    }
    
    def __init__(self):
        """初始化DAC字典"""
        self._dacs = {}
    
    def write(self, dac_num, value):
        """
        输出模拟电压
        
        Args:
            dac_num: DAC通道编号 (1或2)
            value: 输出值 (0-255)，对应 0-3.3V
        
        Note:
            ESP32和ESP32-S2有2路8位DAC
            ESP32-S3不支持DAC
        """
        if dac_num not in self.DAC_PINS:
            raise ValueError(f"Invalid DAC channel: {dac_num}. Must be 1 or 2")
        
        if not 0 <= value <= 255:
            raise ValueError(f"Invalid DAC value: {value}. Must be 0-255")
        
        # 懒加载：首次使用时才创建 DAC 对象
        if dac_num not in self._dacs:
            gpio_num = self.DAC_PINS[dac_num]
            pin = Pin(gpio_num)
            self._dacs[dac_num] = DAC(pin)
        
        self._dacs[dac_num].write(value)
    
    def voltage(self, dac_num, voltage):
        """
        输出指定电压
        
        Args:
            dac_num: DAC通道编号 (1或2)
            voltage: 电压值 (0.0-3.3V)
        """
        if not 0.0 <= voltage <= 3.3:
            raise ValueError(f"Invalid voltage: {voltage}. Must be 0.0-3.3V")
        
        # 电压转换为0-255的值
        value = int((voltage / 3.3) * 255)
        self.write(dac_num, value)


# 全局实例
touch = Touch()
hall = HallSensor()
dac = DACOutput()

# 便捷访问
def dac1():
    """返回DAC1实例"""
    return _DAC1Instance()

def dac2():
    """返回DAC2实例"""
    return _DAC2Instance()

class _DAC1Instance:
    """DAC1实例包装"""
    def write(self, value):
        dac.write(1, value)
    
    def voltage(self, v):
        dac.voltage(1, v)

class _DAC2Instance:
    """DAC2实例包装"""
    def write(self, value):
        dac.write(2, value)
    
    def voltage(self, v):
        dac.voltage(2, v)


if __name__ == '__main__':
    # 测试代码
    print("ESP32 特殊功能测试")
    print("-" * 40)
    
    # 测试触摸
    print("触摸引脚0值:", touch.read(0))
    
    # 测试霍尔传感器（仅ESP32）
    try:
        print("霍尔传感器值:", hall.read())
    except RuntimeError as e:
        print("霍尔传感器:", e)
    
    # 测试DAC
    try:
        print("DAC1输出1.65V...")
        dac.voltage(1, 1.65)
        print("完成")
    except Exception as e:
        print("DAC错误:", e)
