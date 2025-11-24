"""
ESP32-S3 摄像头支持库
支持 OV2640/OV5640 等摄像头模块
搭豆智联 2.0 - MicroPython固件
"""

import time

try:
    import camera
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    print("⚠️  摄像头库不可用（仅ESP32-S3支持）")


class Camera:
    """摄像头管理类"""
    
    # 图像格式
    JPEG = 0
    RGB565 = 1
    YUV422 = 2
    GRAYSCALE = 3
    
    # 分辨率
    QVGA = 0    # 320x240
    VGA = 1     # 640x480
    SVGA = 2    # 800x600
    XGA = 3     # 1024x768
    HD = 4      # 1280x720
    SXGA = 5    # 1280x1024
    UXGA = 6    # 1600x1200
    
    # 特效
    EFFECT_NONE = 0
    EFFECT_NEGATIVE = 1
    EFFECT_GRAYSCALE = 2
    EFFECT_RED_TINT = 3
    EFFECT_GREEN_TINT = 4
    EFFECT_BLUE_TINT = 5
    EFFECT_SEPIA = 6
    
    def __init__(self):
        """初始化摄像头"""
        if not CAMERA_AVAILABLE:
            raise RuntimeError("Camera not available on this device")
        
        self._initialized = False
        self._streaming = False
        print("📷 摄像头模块已加载")
    
    def init(self, format=JPEG, framesize=VGA, quality=10):
        """
        初始化摄像头
        
        Args:
            format: 图像格式（JPEG/RGB565/YUV422/GRAYSCALE）
            framesize: 分辨率（QVGA/VGA/SVGA/XGA/HD/SXGA/UXGA）
            quality: JPEG质量（0-63，数值越小质量越高）
        
        Returns:
            bool: True表示初始化成功
        """
        try:
            # ESP32-S3典型引脚配置（根据具体模块调整）
            camera.init(
                0,  # 摄像头ID
                format=format,
                framesize=framesize,
                quality=quality,
                # 以下是常见的引脚配置（AI-Thinker模块）
                d0=4, d1=5, d2=18, d3=19, d4=36, d5=39, d6=34, d7=35,
                xclk=0, pclk=22, vsync=25, href=23,
                sda=26, scl=27,
                pwdn=-1, reset=15,
                xclk_freq=20000000
            )
            
            self._initialized = True
            print(f"✅ 摄像头初始化成功")
            print(f"   格式: {self._format_name(format)}")
            print(f"   分辨率: {self._framesize_name(framesize)}")
            print(f"   质量: {quality}")
            return True
        
        except Exception as e:
            print(f"❌ 摄像头初始化失败: {e}")
            return False
    
    def capture(self):
        """
        拍摄一张照片
        
        Returns:
            bytes: 图像数据
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized. Call init() first")
        
        try:
            img = camera.capture()
            print(f"📸 已拍摄照片 ({len(img)} 字节)")
            return img
        except Exception as e:
            print(f"❌ 拍照失败: {e}")
            return None
    
    def stream_start(self):
        """开始视频流"""
        if not self._initialized:
            raise RuntimeError("Camera not initialized")
        
        self._streaming = True
        print("🎥 视频流已开启")
    
    def stream_stop(self):
        """停止视频流"""
        self._streaming = False
        print("⏹️  视频流已停止")
    
    def stream_frame(self):
        """
        获取流中的一帧
        
        Returns:
            bytes: 图像数据，如果流未开启返回None
        """
        if not self._streaming:
            return None
        
        return self.capture()
    
    def deinit(self):
        """释放摄像头资源"""
        if self._initialized:
            camera.deinit()
            self._initialized = False
            self._streaming = False
            print("📷 摄像头已释放")
    
    # 设置参数
    def set_brightness(self, value):
        """设置亮度 (-2到2)"""
        camera.set(camera.BRIGHTNESS, value)
    
    def set_contrast(self, value):
        """设置对比度 (-2到2)"""
        camera.set(camera.CONTRAST, value)
    
    def set_saturation(self, value):
        """设置饱和度 (-2到2)"""
        camera.set(camera.SATURATION, value)
    
    def set_effect(self, effect):
        """设置特效"""
        camera.set(camera.SPECIAL_EFFECT, effect)
    
    def set_whitebalance(self, enable):
        """设置自动白平衡"""
        camera.set(camera.WHITEBALANCE, 1 if enable else 0)
    
    def set_awb_gain(self, enable):
        """设置自动白平衡增益"""
        camera.set(camera.AWB_GAIN, 1 if enable else 0)
    
    def set_exposure_ctrl(self, enable):
        """设置自动曝光控制"""
        camera.set(camera.EXPOSURE_CTRL, 1 if enable else 0)
    
    def set_aec_value(self, value):
        """设置曝光值 (0-1200)"""
        camera.set(camera.AEC_VALUE, value)
    
    def set_gain_ctrl(self, enable):
        """设置自动增益控制"""
        camera.set(camera.GAIN_CTRL, 1 if enable else 0)
    
    def set_agc_gain(self, value):
        """设置增益值 (0-30)"""
        camera.set(camera.AGC_GAIN, value)
    
    def set_hmirror(self, enable):
        """设置水平镜像"""
        camera.set(camera.HMIRROR, 1 if enable else 0)
    
    def set_vflip(self, enable):
        """设置垂直翻转"""
        camera.set(camera.VFLIP, 1 if enable else 0)
    
    # 辅助方法
    def _format_name(self, format):
        """获取格式名称"""
        names = {0: 'JPEG', 1: 'RGB565', 2: 'YUV422', 3: 'GRAYSCALE'}
        return names.get(format, 'Unknown')
    
    def _framesize_name(self, framesize):
        """获取分辨率名称"""
        names = {
            0: 'QVGA (320x240)',
            1: 'VGA (640x480)',
            2: 'SVGA (800x600)',
            3: 'XGA (1024x768)',
            4: 'HD (1280x720)',
            5: 'SXGA (1280x1024)',
            6: 'UXGA (1600x1200)'
        }
        return names.get(framesize, 'Unknown')
    
    @property
    def is_initialized(self):
        """检查是否已初始化"""
        return self._initialized
    
    @property
    def is_streaming(self):
        """检查是否正在流式传输"""
        return self._streaming


# 全局摄像头实例
_camera = None

def init(format=Camera.JPEG, framesize=Camera.VGA, quality=10):
    """
    初始化摄像头
    
    Returns:
        Camera: 摄像头实例
    """
    global _camera
    if _camera is None:
        _camera = Camera()
    _camera.init(format, framesize, quality)
    return _camera

def get():
    """获取摄像头实例"""
    global _camera
    if _camera is None or not _camera.is_initialized:
        raise RuntimeError("Camera not initialized. Call init() first")
    return _camera

def capture():
    """快捷拍照方法"""
    return get().capture()


if __name__ == '__main__':
    # 测试代码
    print("摄像头测试")
    print("-" * 40)
    
    if not CAMERA_AVAILABLE:
        print("❌ 此设备不支持摄像头")
        print("   仅ESP32-S3支持")
    else:
        try:
            # 初始化摄像头
            cam = init(format=Camera.JPEG, framesize=Camera.VGA)
            
            # 拍照
            print("\n拍摄测试照片...")
            img = cam.capture()
            if img:
                print(f"✅ 拍照成功，大小: {len(img)} 字节")
            
            # 设置特效
            print("\n应用灰度特效...")
            cam.set_effect(Camera.EFFECT_GRAYSCALE)
            
            # 再次拍照
            img2 = cam.capture()
            if img2:
                print(f"✅ 特效拍照成功，大小: {len(img2)} 字节")
            
            # 释放资源
            cam.deinit()
            print("\n✅ 测试完成")
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
