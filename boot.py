 # ...
# ...
# ...

import network
import machine
import ubinascii
import time
import sys
import select

try:
    import ujson as json
except ImportError:
    import json

# 搭豆物联固件 - MicroPython v1.22.0 + ESP-IDF v5.0.4（原始成功配置）
FIRMWARE_VERSION = "2.1.1"
FIRMWARE_BUILD = "20250112-07"  # 禁用AP热点功能，仅支持串口配置
FIRMWARE_NAME = "搭豆物联 TansuoDou IoT Platform"

print("\n" + "="*50)
print("    🔌 " + FIRMWARE_NAME)
print("    版本: v" + FIRMWARE_VERSION + " (Build " + FIRMWARE_BUILD + ")")
print("="*50)

# ...
def get_device_id():
    """Get unique device ID（基于MAC地址）"""
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = ubinascii.hexlify(wlan.config('mac')).decode()
        device_id = "TSD-" + mac[-8:].upper()
        return device_id
    except Exception as e:
        print("❌ 获取设备ID失败: " + str(e))
        return "TSD-UNKNOWN"

# ...
def wait_for_serial_config(timeout=5):
    """等待串口配置命令（用于烧录后自动配置）"""
    import sys
    
    print("\n" + "="*50)
    print("  📶 等待串口WiFi配置...")
    print("  超时: " + str(timeout) + "秒（仅首次启动）")
    print("="*50)
    
    start_time = time.time()
    buffer = ""
    
    while time.time() - start_time < timeout:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)
            if char:
                buffer += char
                if char == '\n':
                    line = buffer.strip()
                    buffer = ""
                    
                    # 检查是否是WiFi配置命令
                    if line.startswith('WIFI_CONFIG:'):
                        try:
                            config_json = line[12:]  # 移除"WIFI_CONFIG:"前缀
                            config = json.loads(config_json)
                            
                            if 'ssid' in config and config['ssid']:
                                print("\n✅ 收到WiFi配置")
                                print("   SSID: " + config['ssid'])
                                
                                # 保存配置
                                with open('/wifi_config.json', 'w') as f:
                                    json.dump(config, f)
                                
                                print("✅ WiFi配置已保存")
                                return config
                        except Exception as e:
                            print("❌ 配置解析失败: " + str(e))
        
        time.sleep(0.1)
    
    print("\n⏱️  串口配置超时（将进入串口监听模式）")
    return None

def check_wifi_config():
    """检查WiFi配置文件（带详细错误处理）"""
    try:
        with open('/wifi_config.json', 'r') as f:
            config = json.load(f)
            # ...
            if config.get('ssid') and isinstance(config['ssid'], str) and len(config['ssid']) > 0:
                # ...
                if 'password' not in config:
                    config['password'] = ''
                # ...
                if 'device_name' not in config:
                    config['device_name'] = get_device_id()
                return config
    except OSError as e:
        # ...
        print("📄 配置文件不存在或无法读取")
    except ValueError as e:
        # ...
        print("⚠️  配置文件格式错误: " + str(e))
    except Exception as e:
        print("⚠️  读取配置时出错: " + str(e))
    
    return None

def start_serial_listen_mode():
    """串口监听模式（持续监听串口命令）"""
    import sys
    
    print("\n" + "="*50)
    print("  🔌 串口监听模式")
    print("="*50)
    print("💡 说明：")
    print("   - 可随时通过串口发送 WIFI_CONFIG 命令配置")
    print("   - 按 Ctrl+C 退出监听")
    print("   - ⚠️  AP热点功能已禁用，仅支持串口配置")
    print("="*50 + "\n")
    
    buffer = ""
    
    while True:
        try:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if char:
                    buffer += char
                    if char == '\n':
                        line = buffer.strip()
                        buffer = ""
                        
                        # WiFi配置命令
                        if line.startswith('WIFI_CONFIG:'):
                            try:
                                config_json = line[12:]
                                config = json.loads(config_json)
                                
                                if 'ssid' in config and config['ssid']:
                                    print("\n✅ 收到WiFi配置")
                                    print("   SSID: " + config['ssid'])
                                    
                                    # 保存配置
                                    with open('/wifi_config.json', 'w') as f:
                                        json.dump(config, f)
                                    
                                    print("✅ WiFi配置已保存")
                                    print("🔄 3秒后重启设备...\n")
                                    time.sleep(3)
                                    machine.reset()
                            except Exception as e:
                                print("❌ 配置解析失败: " + str(e))
                        
                        # AP热点模式命令 - 已禁用
                        elif line == 'AP_MODE':
                            print("\n⚠️  AP热点功能已禁用")
                            print("💡 请使用串口发送 WIFI_CONFIG 命令配置\n")
                        
                        # 帮助命令
                        elif line == 'HELP':
                            print("\n📝 支持的命令：")
                            print("   WIFI_CONFIG:{\"ssid\":\"xxx\",\"password\":\"xxx\",\"api_base\":\"http://xxx\",\"user_id\":\"xxx\"}")
                            print("   HELP - 显示帮助\n")
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\n\n👋 退出串口监听模式")
            break
        except Exception as e:
            print("❌ 监听错误: " + str(e))
            time.sleep(1)

def start_config_mode(manual=False):
    """启动WiFi配罡模式（带重试机制）"""
    if manual:
        print("\n" + "-"*50)
        print("  📱 手动启动WiFi配网模式")
        print("-"*50)
    else:
        print("\n" + "-"*50)
        print("  📱 进入WiFi配网模式")
        print("-"*50)
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            import config_portal
            config_portal.start()
            break  # 如果成功启动，退出循环
        except ImportError as e:
            print("❌ 无法导入配网模块: " + str(e))
            break  # 模块缺失，不重试
        except Exception as e:
            retry_count += 1
            print("❌ 配网模式启动失败 (尝试 " + str(retry_count) + "/" + str(max_retries) + "): " + str(e))
            if retry_count < max_retries:
                print("   3秒后重试...")
                time.sleep(3)
            else:
                print("   已达最大重试次数，系统将重启...")
                time.sleep(5)
                machine.reset()

def start_normal_mode(config):
    """启动正常工作模式（带错误恢复）"""
    print("\n" + "-"*50)
    print("  🚀 启动正常工作模式")
    print("-"*50)
    
    try:
        import tansuodou_main
        tansuodou_main.start(config)
    except ImportError as e:
        print("❌ 无法导入主程序: " + str(e))
        print("   可能固件不完整，请重新烧录")
        print("   5秒后进入配网模式...")
        time.sleep(5)
        start_config_mode()
    except Exception as e:
        print("❌ 主程序启动失败: " + str(e))
        print("   WiFi配置可能有误，5秒后重置配置...")
        time.sleep(5)
        # ...
        try:
            import os
            os.remove('/wifi_config.json')
            print("   配置已重置")
        except:
            pass
        machine.reset()

# ...
def main():
    """主启动流程（带完整错误处理）"""
    # ...
    device_id = get_device_id()
    print("\n📋 设备ID: " + device_id)
    print("💾 芯片ID: " + machine.unique_id().hex().upper())
    
    # ...
    print("🔧 固件版本: v" + FIRMWARE_VERSION)
    print("📅 构建日期: " + FIRMWARE_BUILD)
    
    # ...
    try:
        import gc
        gc.collect()
        print("💾 可用内存: " + str(gc.mem_free()) + " bytes")
    except:
        pass
    
    # ...
    try:
        import ota_manager
        ota_manager.OTAManager.verify_new_firmware()
    except:
        pass
    
    # 检查现有配置
    config = check_wifi_config()
    
    if config is None:
        # 没有配置，直接进入串口监听模式
        print("\n⚠️  未找到有效的WiFi配置")
        print("\n🔌 进入串口监听模式")
        print("💡 随时可发送 WIFI_CONFIG 命令配置")
        print("💡 或发送 'AP_MODE' 启动热点配置\n")
        start_serial_listen_mode()
    else:
        # 有配置，直接启动
        print("\n✅ 发现WiFi配置")
        print("   SSID: " + config['ssid'])
        print("   设备名: " + config.get('device_name', device_id))
        start_normal_mode(config)

# ...
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止 (Ctrl+C)")
        sys.exit(0)
    except MemoryError:
        print("\n\n❌ 内存不足！")
        print("   尝试释放内存并重启...")
        try:
            import gc
            gc.collect()
        except:
            pass
        time.sleep(3)
        machine.reset()
    except Exception as e:
        print("\n\n❌ 系统错误: " + str(e))
        print("   错误类型: " + str(type(e).__name__))
        # ...
        try:
            sys.print_exception(e)
        except:
            pass
        print("\n系统将在5秒后重启...")
        time.sleep(5)
        machine.reset()
