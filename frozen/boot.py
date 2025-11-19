# 搭豆物联 2.0 - 启动脚本
# 版本: v3.0.1
# 职责：系统初始化 + 启动编排

import sys
import json
import time

# 固件版本信息
FIRMWARE_VERSION = "3.0.3"
FIRMWARE_BUILD = "20251119-v3.5"
FIRMWARE_NAME = "搭豆物联 TansuoDou IoT Platform"

print("\n" + "="*50)
print("    🔌 " + FIRMWARE_NAME)
print("    版本: v" + FIRMWARE_VERSION + " (Build " + FIRMWARE_BUILD + ")")
print("="*50)

# ========== Step 1: 检查 WiFi 配置 ==========
has_wifi_config = False
try:
    with open('/wifi_config.json', 'r') as f:
        config = json.load(f)
        has_wifi_config = bool(config.get('ssid'))
except:
    pass

# ========== Step 2: WiFi 配置流程 ==========
if not has_wifi_config:
    print("\n📶 未检测到 WiFi 配置")
    try:
        import wifi_config_helper
        print("🔧 启动 WiFi 配置助手...")
        wifi_config_helper.start()  # 阻塞式配置，完成后自动重启
    except ImportError:
        print("❌ WiFi 配置助手未找到（wifi_config_helper.py）")
        print("⚠️  请通过串口或 Web 配置 WiFi")
    except Exception as e:
        print(f"❌ WiFi 配置失败: {e}")

# ========== Step 3: 启动 IDE Helper（后台服务）==========
try:
    import ide_helper
    if ide_helper.start_background():
        print("✅ IDE Helper 后台服务已启动")
    else:
        print("⚠️  IDE Helper 无法启动后台线程，需手动调用 listen()")
except ImportError:
    print("⚠️  IDE Helper 未找到（ide_helper.py）")
except Exception as e:
    print(f"⚠️  IDE Helper 启动失败: {e}")

# ========== Step 4: 执行用户启动代码（可选）==========
try:
    import user_code.main
    print("✅ 用户启动代码已加载 (user_code/main.py)")
except ImportError:
    pass  # 用户没有 main.py，正常
except Exception as e:
    print(f"⚠️  用户代码错误: {e}")

# ========== Step 5: 启动主程序 ==========
print("\n🚀 启动主程序...")
try:
    # 加载WiFi配置
    try:
        with open('/wifi_config.json', 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    # 启动主程序
    import tansuodou_main
    tansuodou_main.start(config)
except ImportError:
    print("❌ 主程序未找到（tansuodou_main.py）")
except Exception as e:
    print(f"❌ 主程序异常: {e}")
    import machine
    print("🔄 3秒后重启...")
    time.sleep(3)
    machine.reset()
