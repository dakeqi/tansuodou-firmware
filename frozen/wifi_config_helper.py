# WiFi 配置助手 - 支持 Improv Serial + 自定义 JSON 协议
# 搭豆物联 2.0
# 版本: 1.0.0

import sys
import json
import time
import network
import machine
import ubinascii

# ========== 工具函数 ==========
def flush_stdout():
    """安全刷新 stdout"""
    try:
        sys.stdout.flush()
    except:
        pass

def get_device_id():
    """获取设备 ID"""
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = ubinascii.hexlify(wlan.config('mac')).decode()
        return "TSD-" + mac[-8:].upper()
    except:
        return "TSD-UNKNOWN"

# ========== Improv Serial 协议 ==========
IMPROV_SERIAL_VERSION = 1

# Improv 包类型
IMPROV_TYPE_CURRENT_STATE = 0x01
IMPROV_TYPE_ERROR_STATE = 0x02
IMPROV_TYPE_RPC_COMMAND = 0x03
IMPROV_TYPE_RPC_RESULT = 0x04

# Improv RPC 命令
IMPROV_CMD_WIFI_SETTINGS = 0x01
IMPROV_CMD_GET_CURRENT_STATE = 0x02
IMPROV_CMD_GET_DEVICE_INFO = 0x03
IMPROV_CMD_GET_WIFI_NETWORKS = 0x04

# Improv 状态
IMPROV_STATE_AUTHORIZED = 0x00
IMPROV_STATE_AWAITING_AUTHORIZATION = 0x01
IMPROV_STATE_PROVISIONING = 0x03
IMPROV_STATE_PROVISIONED = 0x04

# Improv 错误
IMPROV_ERROR_NONE = 0x00
IMPROV_ERROR_INVALID_RPC = 0x01
IMPROV_ERROR_UNKNOWN_RPC = 0x02
IMPROV_ERROR_UNABLE_TO_CONNECT = 0x03
IMPROV_ERROR_NOT_AUTHORIZED = 0x04
IMPROV_ERROR_UNKNOWN = 0xFF

def send_improv_response(packet_type, data=b''):
    """发送 Improv 响应包"""
    header = b'IMPROV'
    version = bytes([IMPROV_SERIAL_VERSION])
    ptype = bytes([packet_type])
    length = bytes([len(data)])
    
    checksum = sum(header + version + ptype + length + data) & 0xFF
    packet = header + version + ptype + length + data + bytes([checksum])
    
    sys.stdout.write(packet.decode('latin-1'))
    flush_stdout()

def send_improv_state(state):
    """发送 Improv 状态"""
    send_improv_response(IMPROV_TYPE_CURRENT_STATE, bytes([state]))

def send_improv_error(error_code):
    """发送 Improv 错误"""
    send_improv_response(IMPROV_TYPE_ERROR_STATE, bytes([error_code]))

def parse_improv_packet(data):
    """解析 Improv 数据包"""
    if len(data) < 11:
        return None
    
    if data[:6] != b'IMPROV':
        return None
    
    version = data[6]
    ptype = data[7]
    length = data[8]
    
    if len(data) < 9 + length + 1:
        return None
    
    payload = data[9:9+length]
    checksum = data[9+length]
    
    calculated_checksum = sum(data[:9+length]) & 0xFF
    if checksum != calculated_checksum:
        return None
    
    return {'type': ptype, 'data': payload}

def handle_improv_wifi_settings(data):
    """处理 Improv WiFi 配置"""
    try:
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
        
        print(f"📶 Improv: 配置 WiFi '{ssid}'")
        
        # 保存配置
        config_data = {
            'ssid': ssid,
            'password': password,
            'device_name': get_device_id(),
            'api_base': '',
            'user_id': ''
        }
        
        save_config(config_data)
        
        send_improv_state(IMPROV_STATE_PROVISIONING)
        send_improv_response(IMPROV_TYPE_RPC_RESULT, b'')
        
        print("✅ Improv: 配置已保存，3秒后重启...")
        time.sleep(3)
        machine.reset()
        return True
        
    except Exception as e:
        print(f"❌ Improv: {e}")
        send_improv_error(IMPROV_ERROR_UNKNOWN)
        return False

def handle_improv_get_info(data):
    """处理 Improv 获取设备信息"""
    try:
        import boot
        info_str = f"{boot.FIRMWARE_NAME}\n{boot.FIRMWARE_VERSION}\nESP32-S3\n{get_device_id()}"
    except:
        info_str = f"搭豆智联 DaDou IoT\nunknown\nESP32\n{get_device_id()}"
    
    info_data = info_str.encode('utf-8')
    send_improv_response(IMPROV_TYPE_RPC_RESULT, info_data)
    return False

# ========== JSON 配置协议 ==========
def handle_json_command(cmd):
    """处理 JSON 配置命令"""
    cmd_type = cmd.get('cmd', '').upper()
    
    # PING 命令
    if cmd_type == 'PING':
        try:
            import boot
            version = boot.FIRMWARE_VERSION
            build = boot.FIRMWARE_BUILD
        except:
            version = "unknown"
            build = "unknown"
        
        response = {
            "status": "READY",
            "version": version,
            "build": build,
            "device_id": get_device_id()
        }
        print(json.dumps(response))
        flush_stdout()
        return False
    
    # INFO 命令
    if cmd_type == 'INFO':
        try:
            import boot
            import gc
            response = {
                "status": "OK",
                "device_id": get_device_id(),
                "firmware": {
                    "version": boot.FIRMWARE_VERSION,
                    "build": boot.FIRMWARE_BUILD,
                    "name": boot.FIRMWARE_NAME
                },
                "memory": {
                    "free": gc.mem_free()
                }
            }
        except:
            response = {"status": "OK", "device_id": get_device_id()}
        
        print(json.dumps(response))
        flush_stdout()
        return False
    
    # CONFIG 命令
    if cmd_type == 'CONFIG':
        if 'ssid' not in cmd or not cmd['ssid']:
            error = {"status": "ERROR", "msg": "缺少 SSID"}
            print(json.dumps(error))
            flush_stdout()
            return False
        
        config_data = {
            'ssid': cmd['ssid'],
            'password': cmd.get('password', ''),
            'device_name': cmd.get('device_name', get_device_id()),
            'api_base': cmd.get('api_base', ''),
            'user_id': cmd.get('user_id', '')
        }
        
        try:
            save_config(config_data)
            success = {"status": "OK", "msg": "配置已保存"}
            print(json.dumps(success))
            flush_stdout()
            print("🔄 3秒后重启...")
            time.sleep(3)
            machine.reset()
            return True
        except Exception as e:
            error = {"status": "ERROR", "msg": str(e)}
            print(json.dumps(error))
            flush_stdout()
            return False
    
    # 未知命令
    error = {"status": "ERROR", "msg": "未知命令: " + cmd_type}
    print(json.dumps(error))
    flush_stdout()
    return False

# ========== 配置保存 ==========
def save_config(config_data):
    """保存 WiFi 配置到文件"""
    try:
        import os
        try:
            os.remove('/wifi_config.json')
        except:
            pass
        
        with open('/wifi_config.json', 'w') as f:
            f.write(json.dumps(config_data))
        
        print("✅ WiFi 配置已保存")
        return True
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        raise

# ========== 主监听函数 ==========
def start():
    """
    启动 WiFi 配置监听（阻塞式）
    等待用户通过串口配置 WiFi
    """
    print("\n" + "="*50)
    print("  📶 WiFi 配置助手")
    print("="*50)
    print("💡 支持协议：")
    print("   - Improv Serial (Home Assistant)")
    print("   - JSON 配置 (自定义)")
    print("="*50)
    print("👂 等待串口输入...")
    
    buffer = ""
    improv_buffer = bytearray()
    
    while True:
        try:
            # 使用 uselect.poll 监听串口
            try:
                import uselect
                poll = uselect.poll()
                poll.register(sys.stdin, uselect.POLLIN)
                events = poll.poll(0)
                
                if events:
                    char = sys.stdin.read(1)
                    if char:
                        # Improv 协议（二进制）
                        char_byte = char.encode('latin-1') if isinstance(char, str) else bytes([ord(char)])
                        improv_buffer.extend(char_byte)
                        
                        # 检查 Improv 包头
                        if len(improv_buffer) >= 6 and improv_buffer[:6] == b'IMPROV':
                            if len(improv_buffer) >= 9:
                                length = improv_buffer[8]
                                total_len = 9 + length + 1
                                
                                if len(improv_buffer) >= total_len:
                                    packet_data = bytes(improv_buffer[:total_len])
                                    improv_buffer = improv_buffer[total_len:]
                                    
                                    packet = parse_improv_packet(packet_data)
                                    if packet and packet['type'] == IMPROV_TYPE_RPC_COMMAND:
                                        if len(packet['data']) > 0:
                                            rpc_command = packet['data'][0]
                                            rpc_data = packet['data'][1:]
                                            
                                            if rpc_command == IMPROV_CMD_WIFI_SETTINGS:
                                                if handle_improv_wifi_settings(rpc_data):
                                                    return  # 配置成功，退出
                                            elif rpc_command == IMPROV_CMD_GET_DEVICE_INFO:
                                                handle_improv_get_info(rpc_data)
                                            elif rpc_command == IMPROV_CMD_GET_CURRENT_STATE:
                                                send_improv_state(IMPROV_STATE_AWAITING_AUTHORIZATION)
                                            else:
                                                send_improv_error(IMPROV_ERROR_UNKNOWN_RPC)
                        
                        # 清除过长的 Improv 缓冲区
                        if len(improv_buffer) > 256:
                            improv_buffer = bytearray()
                        
                        # JSON 协议
                        buffer += char
                        if char == '\n':
                            line = buffer.strip()
                            buffer = ""
                            
                            if line and line.startswith('{'):
                                try:
                                    cmd = json.loads(line)
                                    if handle_json_command(cmd):
                                        return  # 配置成功，退出
                                except ValueError:
                                    error = {"status": "ERROR", "msg": "JSON 解析错误"}
                                    print(json.dumps(error))
                                    flush_stdout()
                                except Exception as e:
                                    error = {"status": "ERROR", "msg": str(e)}
                                    print(json.dumps(error))
                                    flush_stdout()
            
            except ImportError:
                # 回退到简单读取
                if hasattr(sys.stdin, 'read'):
                    char = sys.stdin.read(1)
                    if char:
                        buffer += char
                        if char == '\n':
                            line = buffer.strip()
                            buffer = ""
                            if line and line.startswith('{'):
                                try:
                                    cmd = json.loads(line)
                                    if handle_json_command(cmd):
                                        return
                                except:
                                    pass
        
        except Exception:
            pass
        
        time.sleep(0.05)
