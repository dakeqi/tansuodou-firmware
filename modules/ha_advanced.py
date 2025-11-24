"""
Home Assistant 高级功能支持库
集成摄像头、AI检测等高级功能
搭豆智联 2.0 - MicroPython固件
"""

import time
import json

# 导入可能的依赖（按需导入）
try:
    from camera_helper import get as get_camera
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False

try:
    from ai_helper import get_classifier, get_detector
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False


class MotionDetector:
    """动作检测器（基于帧差法）"""
    
    def __init__(self, threshold=30, min_area=100):
        """
        初始化动作检测器
        
        Args:
            threshold: 像素差异阈值
            min_area: 最小变化区域面积
        """
        self.threshold = threshold
        self.min_area = min_area
        self.prev_frame = None
        print("👁️  动作检测器已初始化")
    
    def detect(self, frame=None):
        """
        检测是否有动作
        
        Args:
            frame: 当前帧图像数据（如果为None则自动拍摄）
        
        Returns:
            bool: True表示检测到动作
        """
        if not CAMERA_AVAILABLE:
            print("⚠️  摄像头不可用")
            return False
        
        # 获取当前帧
        if frame is None:
            cam = get_camera()
            frame = cam.capture()
        
        if frame is None:
            return False
        
        # 首次运行，保存参考帧
        if self.prev_frame is None:
            self.prev_frame = frame
            return False
        
        # 简化的帧差检测（实际应用中需要更复杂的算法）
        # 这里仅作为示例
        motion_detected = self._compare_frames(self.prev_frame, frame)
        
        # 更新参考帧
        self.prev_frame = frame
        
        return motion_detected
    
    def _compare_frames(self, frame1, frame2):
        """
        比较两帧图像
        
        Returns:
            bool: True表示有显著差异
        """
        # TODO: 实现真实的帧差算法
        # 这里简化处理
        if len(frame1) != len(frame2):
            return True
        
        # 采样比较（避免全像素比较）
        sample_size = min(100, len(frame1))
        step = len(frame1) // sample_size
        
        diff_count = 0
        for i in range(0, len(frame1), step):
            if abs(frame1[i] - frame2[i]) > self.threshold:
                diff_count += 1
        
        # 如果超过20%的采样点有差异，认为有动作
        return (diff_count / sample_size) > 0.2


class HomeAssistantCamera:
    """Home Assistant 摄像头集成"""
    
    def __init__(self, mqtt_client, entity_id="camera.esp32"):
        """
        初始化HA摄像头
        
        Args:
            mqtt_client: MQTT客户端实例
            entity_id: 摄像头实体ID
        """
        self.mqtt = mqtt_client
        self.entity_id = entity_id
        self.topic_snapshot = f"homeassistant/{entity_id}/snapshot"
        self.topic_state = f"homeassistant/{entity_id}/state"
        print(f"📷 HA摄像头: {entity_id}")
    
    def send_snapshot(self, image_data=None):
        """
        发送快照到Home Assistant
        
        Args:
            image_data: 图像数据（如果为None则自动拍摄）
        """
        if not CAMERA_AVAILABLE:
            print("⚠️  摄像头不可用")
            return False
        
        # 拍摄照片
        if image_data is None:
            cam = get_camera()
            image_data = cam.capture()
        
        if image_data is None:
            return False
        
        # 发送到MQTT
        try:
            self.mqtt.publish(self.topic_snapshot, image_data)
            print(f"📤 快照已发送 ({len(image_data)} 字节)")
            return True
        except Exception as e:
            print(f"❌ 发送快照失败: {e}")
            return False
    
    def update_state(self, state):
        """
        更新摄像头状态
        
        Args:
            state: 状态字符串
        """
        try:
            self.mqtt.publish(self.topic_state, state)
        except Exception as e:
            print(f"❌ 更新状态失败: {e}")


class PersonDetector:
    """人员检测器（基于AI模型）"""
    
    def __init__(self, model_path=None, threshold=0.5):
        """
        初始化人员检测器
        
        Args:
            model_path: AI模型路径
            threshold: 检测阈值
        """
        self.threshold = threshold
        self.detector = None
        
        if AI_AVAILABLE and model_path:
            try:
                from ai_helper import load_detector
                self.detector = load_detector(model_path, threshold=threshold)
                print("👤 人员检测器已初始化")
            except Exception as e:
                print(f"❌ 加载检测器失败: {e}")
    
    def detect(self, image_data=None):
        """
        检测图像中是否有人
        
        Args:
            image_data: 图像数据（如果为None则自动拍摄）
        
        Returns:
            bool: True表示检测到人
        """
        if not self.detector:
            print("⚠️  检测器未初始化")
            return False
        
        # 获取图像
        if image_data is None and CAMERA_AVAILABLE:
            cam = get_camera()
            image_data = cam.capture()
        
        if image_data is None:
            return False
        
        # AI检测
        try:
            results = self.detector.detect(image_data)
            
            # 检查结果中是否有"person"类别
            for label, confidence, box in results:
                if "person" in label.lower() and confidence >= self.threshold:
                    print(f"👤 检测到人员 (置信度: {confidence:.2%})")
                    return True
            
            return False
        
        except Exception as e:
            print(f"❌ 检测失败: {e}")
            return False


class FaceRecognizer:
    """人脸识别器"""
    
    def __init__(self, model_path=None, faces_db=None):
        """
        初始化人脸识别器
        
        Args:
            model_path: 人脸识别模型路径
            faces_db: 人脸数据库文件
        """
        self.model_path = model_path
        self.faces_db = {}
        
        if faces_db:
            self._load_faces_db(faces_db)
        
        print("👨 人脸识别器已初始化")
    
    def _load_faces_db(self, db_path):
        """加载人脸数据库"""
        try:
            with open(db_path, 'r') as f:
                self.faces_db = json.load(f)
            print(f"✅ 加载了 {len(self.faces_db)} 个人脸")
        except Exception as e:
            print(f"❌ 加载人脸数据库失败: {e}")
    
    def recognize(self, image_data=None):
        """
        识别人脸
        
        Args:
            image_data: 图像数据
        
        Returns:
            str: 识别到的人员姓名，未识别返回"Unknown"
        """
        if not AI_AVAILABLE:
            print("⚠️  AI不可用")
            return "Unknown"
        
        # 获取图像
        if image_data is None and CAMERA_AVAILABLE:
            cam = get_camera()
            image_data = cam.capture()
        
        if image_data is None:
            return "Unknown"
        
        # TODO: 实现真实的人脸识别
        # 这里仅作为示例框架
        print("🔍 执行人脸识别...")
        
        # 模拟识别结果
        return "Unknown"
    
    def add_face(self, name, image_data):
        """
        添加人脸到数据库
        
        Args:
            name: 人员姓名
            image_data: 人脸图像
        """
        # TODO: 提取人脸特征并保存
        self.faces_db[name] = {"added_at": time.time()}
        print(f"✅ 已添加人脸: {name}")


# 全局实例
_motion_detector = None
_person_detector = None
_face_recognizer = None

def motion_detector():
    """获取动作检测器实例"""
    global _motion_detector
    if _motion_detector is None:
        _motion_detector = MotionDetector()
    return _motion_detector

def person_detector(model_path=None):
    """获取人员检测器实例"""
    global _person_detector
    if _person_detector is None:
        _person_detector = PersonDetector(model_path)
    return _person_detector

def face_recognizer(model_path=None, faces_db=None):
    """获取人脸识别器实例"""
    global _face_recognizer
    if _face_recognizer is None:
        _face_recognizer = FaceRecognizer(model_path, faces_db)
    return _face_recognizer


if __name__ == '__main__':
    # 测试代码
    print("HA高级功能测试")
    print("-" * 40)
    
    print(f"摄像头可用: {CAMERA_AVAILABLE}")
    print(f"AI可用: {AI_AVAILABLE}")
    
    if CAMERA_AVAILABLE:
        print("\n✅ 可以使用动作检测和摄像头快照功能")
    
    if AI_AVAILABLE:
        print("✅ 可以使用AI检测和识别功能")
