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

def flush_stdout():
    """在MicroPython下安全刷新stdout（忽略不支持flush的实现）"""
    try:
        sys.stdout.flush()
    except AttributeError:
        pass
    except Exception:
        pass

# 搭豆智联固件 - MicroPython v1.22.0 + ESP-IDF v5.0.4（原始成功配置）
# 版本信息统一从 version.py 导入
import version
FIRMWARE_VERSION = version.FIRMWARE_VERSION
FIRMWARE_BUILD = version.FIRMWARE_BUILD
FIRMWARE_NAME = version.FIRMWARE_NAME

# 简化版：不显示大banner

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
def wait_for_serial_config():
    """等待串口配置命令（支持Improv Serial协议和自定义JSON协议）"""
    import sys
    import uos
    
    print("\n" + "="*50)
    print("  📶 等待串口WiFi配置...")
    print("  💡 支持Improv Serial协议和自定义JSON命令")
    print("  ⏰ 无时间限制，随时可以配置")
    print("="*50)
    
    buffer = ""
    improv_buffer = bytearray()
    
    print("👂 开始监听串口输入...")
    print("💡 支持协议: Improv Serial, JSON (PING/CONFIG/INFO)")
    
    # Improv Serial协议常量
    IMPROV_SERIAL_VERSION = 1
    
    # Improv命令类型
    IMPROV_TYPE_CURRENT_STATE = 0x01
    IMPROV_TYPE_ERROR_STATE = 0x02
    IMPROV_TYPE_RPC_COMMAND = 0x03
    IMPROV_TYPE_RPC_RESULT = 0x04
    
    # Improv RPC命令
    IMPROV_CMD_WIFI_SETTINGS = 0x01
    IMPROV_CMD_IDENTIFY = 0x02
    IMPROV_CMD_GET_CURRENT_STATE = 0x02
    IMPROV_CMD_GET_DEVICE_INFO = 0x03
    IMPROV_CMD_GET_WIFI_NETWORKS = 0x04
    
    # Improv状态
    IMPROV_STATE_AUTHORIZED = 0x00
    IMPROV_STATE_AWAITING_AUTHORIZATION = 0x01  
    IMPROV_STATE_PROVISIONING = 0x03
    IMPROV_STATE_PROVISIONED = 0x04
    
    # Improv错误
    IMPROV_ERROR_NONE = 0x00
    IMPROV_ERROR_INVALID_RPC = 0x01
    IMPROV_ERROR_UNKNOWN_RPC = 0x02
    IMPROV_ERROR_UNABLE_TO_CONNECT = 0x03
    IMPROV_ERROR_NOT_AUTHORIZED = 0x04
    IMPROV_ERROR_UNKNOWN = 0xFF
    
    def send_improv_response(packet_type, data=b''):
        """发送Improv响应包"""
        # 格式: IMPROV, version, type, length, data, checksum
        header = b'IMPROV'
        version = bytes([IMPROV_SERIAL_VERSION])
        ptype = bytes([packet_type])
        length = bytes([len(data)])
        
        # 计算校验和
        checksum = sum(header + version + ptype + length + data) & 0xFF
        
        packet = header + version + ptype + length + data + bytes([checksum])
        sys.stdout.write(packet.decode('latin-1'))  # 二进制输出
        flush_stdout()
    
    def send_improv_state(state, buffer_str=""):
        """发送Improv状态"""
        data = bytes([state])
        if buffer_str:
            buffer_bytes = buffer_str.encode('utf-8')
            data += bytes([len(buffer_bytes)]) + buffer_bytes
        send_improv_response(IMPROV_TYPE_CURRENT_STATE, data)
    
    def send_improv_error(error_code):
        """发送Improv错误"""
        send_improv_response(IMPROV_TYPE_ERROR_STATE, bytes([error_code]))
    
    def parse_improv_packet(data):
        """解析Improv数据包"""
        if len(data) < 11:  # 最小包长度
            return None
        
        # 检查header
        if data[:6] != b'IMPROV':
            return None
        
        version = data[6]
        ptype = data[7]
        length = data[8]
        
        if len(data) < 9 + length + 1:
            return None
        
        payload = data[9:9+length]
        checksum = data[9+length]
        
        # 验证校验和
        calculated_checksum = sum(data[:9+length]) & 0xFF
        if checksum != calculated_checksum:
            return None
        
        return {'type': ptype, 'data': payload}
    
    def handle_improv_rpc(command, data):
        """处理Improv RPC命令"""
        if command == IMPROV_CMD_WIFI_SETTINGS:
            # WiFi配置: [ssid_len, ssid, password_len, password]
            if len(data) < 2:
                send_improv_error(IMPROV_ERROR_INVALID_RPC)
                return False
            
            ssid_len = data[0]
            if len(data) < 1 + ssid_len + 1:
                send_improv_error(IMPROV_ERROR_INVALID_RPC)
                return False
            
            ssid = data[1:1+ssid_len].decode('utf-8')
            password_len = data[1+ssid_len]
            
            if len(data) < 1 + ssid_len + 1 + password_len:
                send_improv_error(IMPROV_ERROR_INVALID_RPC)
                return False
            
            password = data[1+ssid_len+1:1+ssid_len+1+password_len].decode('utf-8')
            
            print(f"📶 Improv: 配置WiFi '{ssid}'")
            
            # 保存配置
            config_data = {
                'ssid': ssid,
                'password': password,
                'api_base': '',
                'device_name': get_device_id(),
                'user_id': ''
            }
            
            try:
                # 删除旧配置
                try:
                    import os
                    os.remove('/wifi_config.json')
                except:
                    pass
                
                # 保存新配置
                f = open('/wifi_config.json', 'w')
                try:
                    f.write(json.dumps(config_data))
                finally:
                    f.close()
                
                # 发送成功状态
                send_improv_state(IMPROV_STATE_PROVISIONING)
                
                # 发送RPC结果
                redirect_url = b'http://' + ssid.encode('utf-8') + b'.local'
                result_data = bytes([len(redirect_url)]) + redirect_url
                send_improv_response(IMPROV_TYPE_RPC_RESULT, result_data)
                
                print("✅ Improv: 配置已保存，3秒后重启...")
                time.sleep(3)
                machine.reset()
                return True
                
            except Exception as e:
                print(f"❌ Improv: 保存失败 - {e}")
                send_improv_error(IMPROV_ERROR_UNKNOWN)
                return False
        
        elif command == IMPROV_CMD_GET_CURRENT_STATE:
            send_improv_state(IMPROV_STATE_AWAITING_AUTHORIZATION)
            return False
        
        elif command == IMPROV_CMD_GET_DEVICE_INFO:
            # 返回设备信息: firmware, version, chip, device_name
            info_str = f"{FIRMWARE_NAME}\n{FIRMWARE_VERSION}\nESP32-S3\n{get_device_id()}"
            info_data = info_str.encode('utf-8')
            send_improv_response(IMPROV_TYPE_RPC_RESULT, info_data)
            return False
        
        else:
            send_improv_error(IMPROV_ERROR_UNKNOWN_RPC)
            return False
    
    # 使用更可靠的串口读取方法
    while True:
        try:
            # 直接使用 uselect.poll 监听串口输入
            try:
                import uselect
                poll = uselect.poll()
                poll.register(sys.stdin, uselect.POLLIN)
                events = poll.poll(0)
                
                if events:
                    # 读取一个字符
                    char = sys.stdin.read(1)
                    if char:
                        # 尝试Improv协议（二进制）
                        char_byte = char.encode('latin-1') if isinstance(char, str) else bytes([ord(char)])
                        improv_buffer.extend(char_byte)
                        
                        # 检查Improv包头
                        if len(improv_buffer) >= 6 and improv_buffer[:6] == b'IMPROV':
                            # 等待完整包
                            if len(improv_buffer) >= 9:
                                length = improv_buffer[8]
                                total_len = 9 + length + 1
                                
                                if len(improv_buffer) >= total_len:
                                    packet_data = bytes(improv_buffer[:total_len])
                                    improv_buffer = improv_buffer[total_len:]
                                    
                                    # 解析Improv包
                                    packet = parse_improv_packet(packet_data)
                                    if packet and packet['type'] == IMPROV_TYPE_RPC_COMMAND:
                                        if len(packet['data']) > 0:
                                            rpc_command = packet['data'][0]
                                            rpc_data = packet['data'][1:]
                                            if handle_improv_rpc(rpc_command, rpc_data):
                                                return  # 配置成功，退出
                        
                        # 清除过长的Improv缓冲区
                        if len(improv_buffer) > 256:
                            improv_buffer = bytearray()
                        
                        # 同时支持JSON协议（向后兼容）
                        buffer += char
                        if char == '\n':
                            line = buffer.strip()
                            buffer = ""
                            
                            # 检查是否是JSON命令
                            if line and line.startswith('{'):
                                try:
                                    cmd = json.loads(line)
                                    cmd_type = cmd.get('cmd', '').upper()
                                    
                                    # PING命令
                                    if cmd_type == 'PING':
                                        response = {
                                            "status": "READY",
                                            "version": FIRMWARE_VERSION,
                                            "build": FIRMWARE_BUILD,
                                            "device_id": get_device_id(),
                                            "improv": True  # 标识支持Improv
                                        }
                                        print(json.dumps(response))
                                        flush_stdout()
                                        continue
                                    
                                    # INFO命令
                                    if cmd_type == 'INFO':
                                        import gc
                                        response = {
                                            "status": "OK",
                                            "device_id": get_device_id(),
                                            "firmware": {
                                                "version": FIRMWARE_VERSION,
                                                "build": FIRMWARE_BUILD,
                                                "name": FIRMWARE_NAME
                                            },
                                            "memory": {
                                                "free": gc.mem_free() if hasattr(gc, 'mem_free') else 0
                                            },
                                            "capabilities": ["PING", "INFO", "CONFIG", "ENTER_LISTEN", "IMPROV_SERIAL"]
                                        }
                                        print(json.dumps(response))
                                        flush_stdout()
                                        continue
                                    
                                    # ENTER_LISTEN命令
                                    if cmd_type == 'ENTER_LISTEN':
                                        response = {
                                            "status": "LISTENING",
                                            "msg": "设备已在监听模式，支持CONFIG和Improv Serial"
                                        }
                                        print(json.dumps(response))
                                        flush_stdout()
                                        continue
                                    
                                    # CONFIG命令（JSON方式）
                                    if cmd_type == 'CONFIG':
                                        if 'ssid' not in cmd:
                                            error_response = {"status": "ERROR", "msg": "缺少ssid字段"}
                                            print(json.dumps(error_response))
                                            continue
                                        
                                        if not cmd['ssid']:
                                            error_response = {"status": "ERROR", "msg": "SSID不能为空"}
                                            print(json.dumps(error_response))
                                            continue
                                        
                                        config_data = {
                                            'ssid': cmd['ssid'],
                                            'password': cmd.get('password', ''),
                                            'api_base': cmd.get('api_base', ''),
                                            'device_name': cmd.get('device_name', get_device_id()),
                                            'user_id': cmd.get('user_id', '')
                                        }
                                        
                                        try:
                                            try:
                                                import os
                                                os.remove('/wifi_config.json')
                                            except:
                                                pass
                                            
                                            f = open('/wifi_config.json', 'w')
                                            try:
                                                f.write(json.dumps(config_data))
                                            finally:
                                                f.close()
                                            
                                            success_response = {
                                                "status": "OK",
                                                "msg": "WiFi配置已保存",
                                                "ssid": cmd['ssid']
                                            }
                                            print(json.dumps(success_response))
                                            flush_stdout()
                                            print("🔄 3秒后重启设备...")
                                            time.sleep(3)
                                            machine.reset()
                                            return config_data
                                        except Exception as e:
                                            error_response = {"status": "ERROR", "msg": "保存失败: " + str(e)}
                                            print(json.dumps(error_response))
                                            flush_stdout()
                                            continue
                                    
                                    else:
                                        error_response = {"status": "ERROR", "msg": "未知命令: " + cmd_type}
                                        print(json.dumps(error_response))
                                        flush_stdout()
                                        
                                except ValueError as e:
                                    error_response = {"status": "ERROR", "msg": "JSON解析错误"}
                                    print(json.dumps(error_response))
                                    flush_stdout()
                                except Exception as e:
                                    error_response = {"status": "ERROR", "msg": str(e)}
                                    print(json.dumps(error_response))
                                    flush_stdout()
            except ImportError:
                # 如果 uselect 不可用，回退到简单的读取方式
                try:
                    char = sys.stdin.read(1) if hasattr(sys.stdin, 'read') else None
                    if char:
                        buffer += char
                        if char == '\n':
                            line = buffer.strip()
                            buffer = ""
                            if line and line.startswith('{'):
                                try:
                                    cmd = json.loads(line)
                                    if cmd.get('cmd') == 'CONFIG' and 'ssid' in cmd:
                                        config_data = {
                                            'ssid': cmd['ssid'],
                                            'password': cmd.get('password', ''),
                                            'api_base': cmd.get('api_base', ''),
                                            'device_name': cmd.get('device_name', get_device_id()),
                                            'user_id': cmd.get('user_id', '')
                                        }
                                        # 🔥 修复：手动管理文件
                                        try:
                                            import os
                                            os.remove('/wifi_config.json')
                                        except:
                                            pass
                                        f = open('/wifi_config.json', 'w')
                                        try:
                                            f.write(json.dumps(config_data))
                                        finally:
                                            f.close()
                                        print(json.dumps({"status": "OK"}))
                                        flush_stdout()
                                        time.sleep(3)
                                        machine.reset()
                                        return config_data
                                except Exception:
                                    pass
                except Exception:
                    pass  # 静默忽略读取错误
        except Exception as e:
            # 静默忽略poll相关错误，避免日志刷屏
            pass
        
        time.sleep(0.05)  # 减少延迟，提高响应速度

def check_wifi_config():
    """检查WiFi配置文件（带详细错误处理）"""
    try:
        with open('/wifi_config.json', 'r') as f:
            config = json.load(f)
            # 验证配置的有效性
            if config.get('ssid') and isinstance(config['ssid'], str) and len(config['ssid']) > 0:
                # 添加缺失的必要字段
                if 'password' not in config:
                    config['password'] = ''
                # 添加设备名称
                if 'device_name' not in config:
                    config['device_name'] = get_device_id()
                print("📝 配置文件验证成功")
                return config
            else:
                print("⚠️  配置文件中SSID无效或为空")
                return None
    except OSError as e:
        # 文件不存在或无法读取（静默处理，不打印错误）
        pass
    except ValueError as e:
        # JSON格式错误
        print("⚠️  配置文件格式错误: " + str(e))
    except Exception as e:
        print("⚠️  读取配置时出错: " + str(e))
    
    return None

def start_serial_listen_mode():
    """串口监听模式（持续监听串口命令）"""
    import sys
    import select  # 添加select导入
    
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
            # 使用 uselect.poll 替代 select.select
            try:
                import uselect
                poll = uselect.poll()
                poll.register(sys.stdin, uselect.POLLIN)
                # 使用poll检查是否有输入可用
                events = poll.poll(0)  # 非阻塞检查，返回列表
                if events:  # 如果有事件，读取输入
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
                                        
                                        # 保存配置（🔥 手动管理文件）
                                        f = open('/wifi_config.json', 'w')
                                        f.write(json.dumps(config))
                                        f.close()
                                        
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
            except ImportError:
                # 如果 uselect 不可用，回退到简单的读取方式
                try:
                    char = sys.stdin.read(1) if hasattr(sys.stdin, 'read') else None
                    if char:
                        buffer += char
                        if char == '\n':
                            line = buffer.strip()
                            buffer = ""
                            if line.startswith('WIFI_CONFIG:'):
                                try:
                                    config_json = line[12:]
                                    config = json.loads(config_json)
                                    if 'ssid' in config and config['ssid']:
                                        # 🔥 手动管理文件
                                        f = open('/wifi_config.json', 'w')
                                        f.write(json.dumps(config))
                                        f.close()
                                        print("✅ WiFi配置已保存")
                                        print("🔄 3秒后重启设备...\n")
                                        time.sleep(3)
                                        machine.reset()
                                except Exception as e:
                                    print("❌ 配置处理失败: " + str(e))
                except Exception:
                    pass  # 静默忽略读取错误
            
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
    # 简化版：不显示模式提示
    
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
    # 简化版：只显示设备ID和版本
    device_id = get_device_id()
    print("\n📱 " + device_id + " | v" + FIRMWARE_VERSION)
    
    # 静默执行OTA验证
    try:
        import gc
        gc.collect()
        import ota_manager
        ota_manager.OTAManager.verify_new_firmware()
    except:
        pass
    
    # 检查现有配置
    config = check_wifi_config()
    
    if config is None:
        # 没有配置，无限等待接收串口配置
        print("\n⚠️  未找到有效的WiFi配置")
        print("📶 准备进入串口配置监听模式...")
        print("💡 适合青少年使用，没有时间压力\n")
        
        config = wait_for_serial_config()
        
        # 收到配置后会自动重启，下面的代码不会执行
    else:
        # 简化版：只显示SSID
        print("✅ WiFi: " + config['ssid'])
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
