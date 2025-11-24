"""
ESP32-S3 AI推理支持库
基于 TensorFlow Lite Micro 和 ESP-NN 加速
搭豆智联 2.0 - MicroPython固件
"""

import gc
import time

try:
    import tflite
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  TFLite库不可用（需要编译支持）")


class TFLiteModel:
    """TensorFlow Lite模型类"""
    
    def __init__(self, model_path):
        """
        加载模型
        
        Args:
            model_path: 模型文件路径（.tflite）
        """
        if not AI_AVAILABLE:
            raise RuntimeError("TFLite not available on this device")
        
        self.model_path = model_path
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        
        print(f"🧠 加载AI模型: {model_path}")
        self._load_model()
    
    def _load_model(self):
        """加载模型到内存"""
        try:
            # 读取模型文件
            with open(self.model_path, 'rb') as f:
                model_data = f.read()
            
            # 创建解释器
            self._interpreter = tflite.Interpreter(model_content=model_data)
            self._interpreter.allocate_tensors()
            
            # 获取输入输出信息
            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()
            
            print(f"✅ 模型加载成功")
            print(f"   输入形状: {self._input_details[0]['shape']}")
            print(f"   输出形状: {self._output_details[0]['shape']}")
            
            # 释放模型数据内存
            del model_data
            gc.collect()
        
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise
    
    def predict(self, input_data):
        """
        执行推理
        
        Args:
            input_data: 输入数据（numpy数组或列表）
        
        Returns:
            输出数据
        """
        if self._interpreter is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # 设置输入张量
            self._interpreter.set_tensor(
                self._input_details[0]['index'],
                input_data
            )
            
            # 执行推理
            start_time = time.ticks_ms()
            self._interpreter.invoke()
            inference_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            # 获取输出
            output_data = self._interpreter.get_tensor(
                self._output_details[0]['index']
            )
            
            print(f"⚡ 推理完成 ({inference_time}ms)")
            return output_data
        
        except Exception as e:
            print(f"❌ 推理失败: {e}")
            return None
    
    def get_input_shape(self):
        """获取输入形状"""
        return self._input_details[0]['shape']
    
    def get_output_shape(self):
        """获取输出形状"""
        return self._output_details[0]['shape']


class ImageClassifier:
    """图像分类器"""
    
    def __init__(self, model_path, labels_path=None):
        """
        初始化分类器
        
        Args:
            model_path: 模型文件路径
            labels_path: 标签文件路径（可选）
        """
        self.model = TFLiteModel(model_path)
        self.labels = []
        
        if labels_path:
            self._load_labels(labels_path)
    
    def _load_labels(self, labels_path):
        """加载标签文件"""
        try:
            with open(labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
            print(f"✅ 加载了 {len(self.labels)} 个标签")
        except Exception as e:
            print(f"❌ 加载标签失败: {e}")
    
    def classify(self, image_data):
        """
        分类图像
        
        Args:
            image_data: 图像数据
        
        Returns:
            (label, confidence): 标签和置信度
        """
        # 预处理图像（需要根据模型要求调整）
        processed = self._preprocess_image(image_data)
        
        # 推理
        output = self.model.predict(processed)
        
        if output is None:
            return None, 0.0
        
        # 找到最大值的索引
        max_index = 0
        max_value = output[0][0]
        for i in range(len(output[0])):
            if output[0][i] > max_value:
                max_value = output[0][i]
                max_index = i
        
        # 返回标签和置信度
        label = self.labels[max_index] if max_index < len(self.labels) else f"Class_{max_index}"
        confidence = float(max_value)
        
        print(f"🏷️  分类结果: {label} ({confidence:.2%})")
        return label, confidence
    
    def _preprocess_image(self, image_data):
        """
        预处理图像
        
        Args:
            image_data: 原始图像数据
        
        Returns:
            预处理后的数据
        """
        # TODO: 根据具体模型实现图像预处理
        # 例如：调整大小、归一化等
        return image_data


class ObjectDetector:
    """物体检测器"""
    
    def __init__(self, model_path, labels_path=None, threshold=0.5):
        """
        初始化检测器
        
        Args:
            model_path: 模型文件路径
            labels_path: 标签文件路径
            threshold: 检测阈值
        """
        self.model = TFLiteModel(model_path)
        self.labels = []
        self.threshold = threshold
        
        if labels_path:
            self._load_labels(labels_path)
    
    def _load_labels(self, labels_path):
        """加载标签"""
        try:
            with open(labels_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
        except Exception as e:
            print(f"❌ 加载标签失败: {e}")
    
    def detect(self, image_data):
        """
        检测物体
        
        Args:
            image_data: 图像数据
        
        Returns:
            list: 检测结果列表 [(label, confidence, box), ...]
        """
        # 预处理
        processed = self._preprocess_image(image_data)
        
        # 推理
        output = self.model.predict(processed)
        
        if output is None:
            return []
        
        # 解析输出（需要根据模型格式调整）
        detections = self._parse_output(output)
        
        # 过滤低置信度检测
        filtered = [d for d in detections if d[1] >= self.threshold]
        
        print(f"🎯 检测到 {len(filtered)} 个物体")
        return filtered
    
    def _preprocess_image(self, image_data):
        """预处理图像"""
        # TODO: 实现图像预处理
        return image_data
    
    def _parse_output(self, output):
        """解析模型输出"""
        # TODO: 根据模型格式解析输出
        detections = []
        return detections


# 全局实例
_classifier = None
_detector = None

def load_classifier(model_path, labels_path=None):
    """
    加载图像分类器
    
    Returns:
        ImageClassifier: 分类器实例
    """
    global _classifier
    _classifier = ImageClassifier(model_path, labels_path)
    return _classifier

def load_detector(model_path, labels_path=None, threshold=0.5):
    """
    加载物体检测器
    
    Returns:
        ObjectDetector: 检测器实例
    """
    global _detector
    _detector = ObjectDetector(model_path, labels_path, threshold)
    return _detector

def get_classifier():
    """获取分类器实例"""
    if _classifier is None:
        raise RuntimeError("Classifier not loaded. Call load_classifier() first")
    return _classifier

def get_detector():
    """获取检测器实例"""
    if _detector is None:
        raise RuntimeError("Detector not loaded. Call load_detector() first")
    return _detector


if __name__ == '__main__':
    # 测试代码
    print("AI推理测试")
    print("-" * 40)
    
    if not AI_AVAILABLE:
        print("❌ TFLite不可用")
        print("   需要编译包含TFLite支持的固件")
    else:
        print("✅ TFLite可用")
        print("   可以加载和运行TensorFlow Lite模型")
        print("\n使用示例:")
        print("  1. 加载分类器: classifier = ai_helper.load_classifier('model.tflite', 'labels.txt')")
        print("  2. 分类图像: label, conf = classifier.classify(image_data)")
        print("  3. 加载检测器: detector = ai_helper.load_detector('detect.tflite')")
        print("  4. 检测物体: results = detector.detect(image_data)")
