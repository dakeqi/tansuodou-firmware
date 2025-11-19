# ...
# ...
# ...

import network
import socket
import machine
import ubinascii
import time
import _thread
import errno

try:
    import ujson as json
except:
    import json

try:
    import ota_manager
except:
    print("⚠️  OTA模块未找到")

try:
    import ota_http_server
except:
    print("⚠️  OTA HTTP服务器模块未找到")

# 从 boot.py 导入版本信息（延迟导入）
try:
    import boot
    FIRMWARE_VERSION = boot.FIRMWARE_VERSION
    FIRMWARE_BUILD = boot.FIRMWARE_BUILD
    print("✅ 版本信息导入成功: v" + FIRMWARE_VERSION)
except Exception as e:
    print("⚠️  版本信息导入失败: " + str(e))
    FIRMWARE_VERSION = "3.0.0"
    FIRMWARE_BUILD = "20251119-v3"

# 云端API地址配置
# 生产环境：使用云托管公网地址（默认）
# 开发环境：通过WiFi配置传入api_base覆盖
CLOUD_API_BASE = "https://tansuodou.com/api"  # 云托管公网地址
WS_PORT = 8266  # WebSocket端口
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

# ...
class TansuodouDevice:
    def __init__(self, config):
        self.config = config
        self.device_id = self.get_device_id()
        self.device_name = config.get('device_name', self.device_id)
        self.wlan = None
        self.ip = None
        self.ws_clients = []
        self.running = True
        self.ota_server = None  # OTA HTTP 服务器
        
    def get_device_id(self):
        """Get unique device ID"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = ubinascii.hexlify(wlan.config('mac')).decode()
        return "TSD-" + mac[-8:].upper()
    
    # ...
    def connect_wifi(self):
        """连接到WiFi（优化版：详细状态检测）"""
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        
        ssid = self.config['ssid']
        password = self.config['password']
        
        print("\n" + "="*50)
        print("📶 WiFi连接配置")
        print("="*50)
        print("   SSID: " + str(ssid))
        print("   密码长度: " + str(len(password)) + " 个字符")
        print("   API地址: " + str(self.config.get('api_base', CLOUD_API_BASE)))
        print("   用户ID: " + str(self.config.get('user_id', '(未设置)')))
        print("="*50)
        
        if not self.wlan.isconnected():
            print("\n🔄 开始连接WiFi...")
            
            # 检查是否已经有其他WiFi配置残留
            if self.wlan.status() != network.STAT_IDLE:
                print("   ℹ️  断开旧连接...")
                self.wlan.disconnect()
                time.sleep(1)
            
            self.wlan.connect(ssid, password)
            
            # 等待连接（详细状态）
            timeout = 30  # 增加到30秒
            last_status = None
            
            while not self.wlan.isconnected() and timeout > 0:
                status = self.wlan.status()
                
                # 只在状态变化时打印
                if status != last_status:
                    status_text = self.get_wifi_status_text(status)
                    print("   " + status_text)
                    last_status = status
                
                # MicroPython不支持end参数，改用sys.stdout.write
                import sys
                sys.stdout.write('.')
                time.sleep(1)
                timeout -= 1
            
            print()  # 换行
            
            if self.wlan.isconnected():
                self.ip = self.wlan.ifconfig()[0]
                print("\n" + "="*50)
                print("✅ WiFi连接成功！")
                print("="*50)
                print("   IP地址: " + str(self.ip))
                print("   子网掩码: " + str(self.wlan.ifconfig()[1]))
                print("   网关: " + str(self.wlan.ifconfig()[2]))
                print("   DNS: " + str(self.wlan.ifconfig()[3]))
                print("   信号强度: " + str(self.wlan.status('rssi')) + " dBm")
                print("   MAC地址: " + ubinascii.hexlify(self.wlan.config('mac')).decode())
                print("="*50)
                
                # 测试网络连通性
                print("\n🌐 测试网络连通性...")
                if self.test_network_connectivity():
                    print("✅ 网络连接正常，可以访问互联网")
                    return True
                else:
                    print("⚠️  网络连接异常，可能无法访问云端")
                    print("   但设备将继续运行（本地模式）")
                    return True  # 仍然返回True，让设备继续运行
            else:
                # 连接失败，显示详细原因
                final_status = self.wlan.status()
                print("\n" + "="*50)
                print("❌ WiFi连接失败！")
                print("="*50)
                print("   最终状态: " + self.get_wifi_status_text(final_status))
                print("\n可能原因:")
                
                # 兼容性检查：只在常量存在时才检查
                if hasattr(network, 'STAT_WRONG_PASSWORD') and final_status == network.STAT_WRONG_PASSWORD:
                    print("   ❌ WiFi密码错误（最常见）")
                    print("   💡 请检查密码是否正确，区分大小写")
                elif hasattr(network, 'STAT_NO_AP_FOUND') and final_status == network.STAT_NO_AP_FOUND:
                    print("   ❌ 找不到该WiFi网络")
                    print("   💡 请检查SSID是否正确，区分大小写")
                elif hasattr(network, 'STAT_CONNECT_FAIL') and final_status == network.STAT_CONNECT_FAIL:
                    print("   ❌ 连接被路由器拒绝")
                    print("   💡 路由器可能设置了MAC地址过滤")
                else:
                    print("   1. WiFi密码错误")
                    print("   2. WiFi信号太弱")
                    print("   3. WiFi名称不存在")
                    print("   4. 路由器拒绝连接")
                print("="*50)
                return False
        else:
            self.ip = self.wlan.ifconfig()[0]
            print("\n✅ WiFi已连接: " + str(self.ip))
            return True
    
    def get_wifi_status_text(self, status):
        """获取WiFi状态文字描述（兼容版本）"""
        status_map = {
            network.STAT_IDLE: "🔵 空闲",
            network.STAT_CONNECTING: "🔄 正在连接...",
        }
        
        # 安全地添加可能不存在的常量（MicroPython v1.26.1+）
        if hasattr(network, 'STAT_WRONG_PASSWORD'):
            status_map[network.STAT_WRONG_PASSWORD] = "❌ 密码错误"
        if hasattr(network, 'STAT_NO_AP_FOUND'):
            status_map[network.STAT_NO_AP_FOUND] = "❌ 未找到WiFi"
        if hasattr(network, 'STAT_CONNECT_FAIL'):
            status_map[network.STAT_CONNECT_FAIL] = "❌ 连接失败"
        if hasattr(network, 'STAT_GOT_IP'):
            status_map[network.STAT_GOT_IP] = "✅ 已获取IP"
        
        return status_map.get(status, "❓ 未知状态(" + str(status) + ")")
    
    def test_network_connectivity(self):
        """测试网络连通性"""
        try:
            import usocket
            # 尝试解析域名（测试DNS）
            addr = usocket.getaddrinfo('baidu.com', 80)[0][-1]
            print("   ✓ DNS解析正常")
            return True
        except Exception as e:
            print("   ✗ 网络测试失败: " + str(e))
            return False

    def register_to_cloud(self):
        """注册设备到云端（增强版：详细状态反馈）"""
        try:
            import urequests
            
            # 优先使用配置文件中的API地址
            api_base = self.config.get('api_base', CLOUD_API_BASE)
            
            # 使用动态版本号
            firmware_version = "tansuodou-v" + FIRMWARE_VERSION
            
            data = {
                'deviceId': self.device_id,
                'deviceName': self.device_name,
                'ip': self.ip,
                'type': self.get_chip_type(),
                'firmware': firmware_version,
                'mac': ubinascii.hexlify(self.wlan.config('mac')).decode()
            }
            
            # 如果配置中有user_id，则传入实现自动绑定
            if 'user_id' in self.config and self.config['user_id']:
                data['userId'] = self.config['user_id']
            
            print("\n" + "="*50)
            print("🌐 注册设备到云端")
            print("="*50)
            print("   API地址: " + str(api_base))
            print("   注册端点: /devices/register")
            print("   设备ID: " + str(self.device_id))
            print("   设备名称: " + str(self.device_name))
            print("   IP地址: " + str(self.ip))
            print("   芯片类型: " + str(data['type']))
            print("   固件版本: " + str(data['firmware']))
            print("   MAC地址: " + str(data['mac']))
            
            if 'userId' in data:
                print("   🔗 用户ID: " + str(data['userId']) + " (自动绑定)")
            else:
                print("   ℹ️  用户ID: 未设置（需手动绑定）")
            
            print("\n📤 发送注册请求...")
            
            try:
                response = urequests.post(
                    str(api_base) + "/devices/register",
                    json=data,
                    headers={'Content-Type': 'application/json'},
                    timeout=15  # 增加超时时间到15秒
                )
                
                print("   ✓ 收到响应，状态码: " + str(response.status_code))
                
                if response.status_code == 200:
                    result = response.json()
                    response.close()
                    
                    if result.get('success'):
                        print("\n" + "="*50)
                        print("✅ 设备注册成功！")
                        print("="*50)
                        print("   消息: " + str(result.get('message', '')))
                        
                        if result.get('autoBound'):
                            print("   🎉 已自动绑定到用户账户")
                        elif result.get('existed'):
                            print("   ℹ️  设备已存在，信息已更新")
                        else:
                            print("   ℹ️  新设备已注册")
                        
                        print("="*50)
                        return True
                    else:
                        print("\n⚠️  注册失败: " + str(result.get('error', result.get('message', 'Unknown'))))
                        return False
                else:
                    error_text = response.text
                    response.close()
                    print("\n❌ 注册失败，HTTP " + str(response.status_code))
                    print("   响应: " + str(error_text[:200]))
                    return False
                    
            except Exception as req_error:
                print("\n❌ 请求失败: " + str(req_error))
                print("   错误类型: " + str(type(req_error).__name__))
                print("\n可能原因:")
                print("   1. 网络不通（无法访问互联网）")
                print("   2. API地址错误: " + str(api_base))
                print("   3. 云端服务未运行")
                print("   4. 防火墙阻止连接")
                return False
                
        except ImportError:
            print("❌ 缺少urequests模块，无法注册到云端")
            return False
        except Exception as e:
            print("❌ 云端注册异常: " + str(e))
            print("   错误类型: " + str(type(e).__name__))
            return False
    
    def get_chip_type(self):
        """获取芯片类型"""
        try:
            import esp
            chip_id = esp.chip_id()
            # ...
            return "esp32"
        except:
            return "esp32"
    
    # ...
    def heartbeat_thread(self):
        """心跳线程 - 定期向云端发送心跳（生产环境优化）"""
        print("\n💓 心跳线程已启动（间隔" + str(HEARTBEAT_INTERVAL) + "秒）")
        
        # 使用配置中的API地址，支持本地测试
        api_base = self.config.get('api_base', CLOUD_API_BASE)
        heartbeat_count = 0
        error_count = 0
        
        while self.running:
            try:
                import urequests
                
                data = {'deviceId': self.device_id}
                response = urequests.post(
                    str(api_base) + "/devices/heartbeat",
                    json=data,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                response.close()
                
                heartbeat_count += 1
                error_count = 0  # 重置错误计数
                
                # 每10次心跳才打印一次日志，减少日志干扰
                if heartbeat_count % 10 == 0:
                    # 格式化时间为字符串
                    t = time.localtime()
                    time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
                    print("💓 心跳发送成功 [" + str(heartbeat_count) + "] - " + time_str)
                
            except Exception as e:
                error_count += 1
                # 只打印前3次错误，避免日志洪水
                if error_count <= 3:
                    print("⚠️  心跳发送失败 [" + str(error_count) + "]: " + str(e))
                    if error_count == 3:
                        print("   (后续心跳错误将不再显示)")
            
            # ...
            time.sleep(HEARTBEAT_INTERVAL)
    
    # ...
    def start_ota_http_server(self):
        """启动 OTA HTTP 服务器"""
        try:
            if 'ota_http_server' not in globals():
                print("   ⏸️  OTA HTTP 服务器模块未找到")
                return
            
            # 获取 API 地址
            api_base = self.config.get('api_base', CLOUD_API_BASE)
            
            # 启动服务器（非阻塞）
            self.ota_server = ota_http_server.start_ota_server(80, api_base)
            
            if self.ota_server:
                print("   ✅ OTA HTTP 服务器已启动")
                print("   📡 端点: http://" + str(self.ip) + ":80")
                
                # 在独立线程中运行服务器
                _thread.start_new_thread(self.run_ota_server, ())
            else:
                print("   ❌ OTA HTTP 服务器启动失败")
                
        except Exception as e:
            print("   ❌ OTA 服务器错误: " + str(e))
    
    def run_ota_server(self):
        """OTA 服务器运行线程"""
        while self.running and self.ota_server:
            try:
                # 处理请求（非阻塞）
                self.ota_server.handle_request()
                time.sleep(0.01)  # 小延迟防止 CPU 占用过高
            except Exception as e:
                print("❌ OTA 服务器线程错误: " + str(e))
                break
    
    # ...
    def start_websocket_server(self):
        """启动WebSocket服务器（增强版：连接池管理）"""
        print("\n🔌 启动WebSocket服务器...")
        print("   端口: " + str(WS_PORT))
        
        addr = socket.getaddrinfo('0.0.0.0', WS_PORT)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1.0)  # 设置accept超时，避免阻塞
        s.bind(addr)
        s.listen(5)
        
        print("✅ WebSocket服务器已启动")
        print("   连接地址: ws://" + str(self.ip) + ":" + str(WS_PORT))
        print("   最大连接数: 5")
        
        error_count = 0
        while self.running:
            try:
                try:
                    conn, addr = s.accept()
                except OSError as e:
                    # MicroPython中安全地处理超时错误
                    err = e.errno if hasattr(e, 'errno') else (e.args[0] if e.args else None)
                    # 检查常见的非阻塞错误码
                    if err == errno.EAGAIN or err == errno.ETIMEDOUT or err == 11:  # 11 = EAGAIN/EWOULDBLOCK
                        time.sleep(0.05)
                        continue
                    raise
                
                conn.settimeout(30.0)  # 设置连接超时30秒
                print("\n🔗 新客户端连接: " + str(addr))
                print("   当前连接数: " + str(len(self.ws_clients)))
                
                # 启动独立线程处理客户端
                _thread.start_new_thread(self.handle_websocket_client, (conn, addr))
                error_count = 0  # 有新连接时重置错误计数
                
            except OSError as e:
                # 处理超时和其他OSError
                err = e.errno if hasattr(e, 'errno') else (e.args[0] if e.args else None)
                # 检查常见的非阻塞错误码
                if err == errno.EAGAIN or err == errno.ETIMEDOUT or err == 11:  # 11 = EAGAIN/EWOULDBLOCK
                    continue
                # 其他OSError
                error_count += 1
                if error_count <= 3 or error_count % 30 == 0:
                    print("❌ Socket错误: " + str(e))
                time.sleep(0.2)
    
    def handle_websocket_client(self, conn, addr):
        """处理WebSocket客户端连接（增强版：心跳检测+异常处理）"""
        client_active = True
        last_ping_time = time.time()
        
        try:
            # 接收HTTP握手请求
            request = conn.recv(1024).decode('utf-8')
            
            # 检查WebSocket升级请求
            if 'Upgrade: websocket' in request:
                # 提取WebSocket密钥
                key = None
                for line in request.split('\r\n'):
                    if line.startswith('Sec-WebSocket-Key:'):
                        key = line.split(':', 1)[1].strip()
                        break
                
                if key:
                    # 发送握手响应
                    response = self.create_websocket_handshake(key)
                    conn.send(response.encode())
                    
                    print("✅ WebSocket连接建立: " + str(addr))
                    
                    # 添加到客户端列表
                    self.ws_clients.append(conn)
                    print("   活跃连接数: " + str(len(self.ws_clients)))
                    
                    # 主循环：接收和处理消息
                    while client_active and self.running:
                        try:
                            # 设置非阻塞超时
                            conn.settimeout(0.5)
                            data = conn.recv(1024)
                            
                            if not data:
                                print("   客户端关闭连接")
                                break
                            
                            # 解析WebSocket帧
                            message = self.parse_websocket_frame(data)
                            if message:
                                # 限制日志输出长度
                                log_msg = message[:50] + "..." if len(message) > 50 else message
                                print("📨 收到消息: " + log_msg)
                                self.handle_message(conn, message)
                                last_ping_time = time.time()  # 更新活跃时间
                                
                        except OSError as e:
                            # 超时或EAGAIN错误，检查心跳
                            if time.time() - last_ping_time > 60:
                                print("   ⏱️ 客户端超时（60秒无活动）")
                                client_active = False
                                break
                            time.sleep(0.01)
                            continue
                        except Exception as e:
                            print("❌ 消息处理错误: " + str(e))
                            client_active = False
                            break
                    
                    # 清理：从客户端列表移除
                    if conn in self.ws_clients:
                        self.ws_clients.remove(conn)
                        print("   已移除客户端，剩余: " + str(len(self.ws_clients)))
                    
                    print("🔌 客户端断开: " + str(addr))
            
        except Exception as e:
            print("❌ WebSocket错误: " + str(e))
            # 确保从客户端列表移除
            if conn in self.ws_clients:
                self.ws_clients.remove(conn)
        finally:
            try:
                conn.close()
            except:
                pass
    
    def create_websocket_handshake(self, key):
        """创建WebSocket握手响应"""
        import uhashlib
        
        magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash_key = uhashlib.sha1((key + magic).encode()).digest()
        accept = ubinascii.b2a_base64(hash_key).decode().strip()
        
        response = 'HTTP/1.1 101 Switching Protocols\r\n'
        response += 'Upgrade: websocket\r\n'
        response += 'Connection: Upgrade\r\n'
        response += 'Sec-WebSocket-Accept: ' + str(accept) + '\r\n\r\n'
        
        return response
    
    def parse_websocket_frame(self, data):
        """解析WebSocket帧（带边界检查）"""
        if len(data) < 6:  # 最小帧长度：2字节头 + 4字节mask
            return None
        
        try:
            # ...
            payload_len = data[1] & 0x7F
            mask_start = 2
            
            if payload_len == 126:
                if len(data) < 8:  # 2 + 2(extended len) + 4(mask)
                    return None
                mask_start = 4
                payload_len = int.from_bytes(data[2:4], 'big')
            elif payload_len == 127:
                if len(data) < 14:  # 2 + 8(extended len) + 4(mask)
                    return None
                mask_start = 10
                payload_len = int.from_bytes(data[2:10], 'big')
            
            # ...
            total_len = mask_start + 4 + payload_len
            if len(data) < total_len:
                return None
            
            # ...
            mask = data[mask_start:mask_start+4]
            if len(mask) != 4:
                return None
            
            # ...
            payload = data[mask_start+4:mask_start+4+payload_len]
            
            # ...
            decoded = bytearray()
            for i, byte in enumerate(payload):
                decoded.append(byte ^ mask[i % 4])
            
            return decoded.decode('utf-8', 'ignore')  # 忽略解码错误
        except Exception as e:
            print("⚠️  WebSocket帧解析失败: " + str(e))
            return None
    
    def handle_message(self, conn, message):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                # ...
                self.send_websocket_message(conn, json.dumps({
                    'type': 'pong',
                    'timestamp': time.time()
                }))
                
            elif msg_type == 'execute':
                # 处理两种格式: {"command": "..."} 或直接字符串
                payload = data.get('data', {})
                print("🔍 调试: payload 类型 =", type(payload), ", 值 =", str(payload)[:100])
                
                if isinstance(payload, dict):
                    cmd = payload.get('command', '')
                else:
                    cmd = str(payload) if payload else ''
                    
                print("⚙️  执行命令 (长度:" + str(len(cmd)) + "): " + str(cmd)[:100])
                
                try:
                    # ...
                    if cmd == 'get_info':
                        result = {
                            'deviceId': self.device_id,
                            'ip': self.ip,
                            'rssi': self.wlan.status('rssi') if self.wlan else None,
                            'uptime': time.time()
                        }
                        self.send_websocket_message(conn, json.dumps({
                            'type': 'output',
                            'data': result
                        }))
                    elif cmd == 'reboot':
                        self.send_websocket_message(conn, json.dumps({
                            'type': 'output',
                            'data': '✅ 设备将在3秒后重启'
                        }))
                        time.sleep(3)
                        machine.reset()
                    elif cmd == 'reset_config':
                        import os
                        try:
                            os.remove('/wifi_config.json')
                            self.send_websocket_message(conn, json.dumps({
                                'type': 'output',
                                'data': '✅ 配置已重置，设备将重启'
                            }))
                            time.sleep(2)
                            machine.reset()
                        except:
                            pass
                    elif cmd == 'ctrl_c':
                        # Ctrl+C: 中断当前程序，进入REPL模式
                        self.send_websocket_message(conn, json.dumps({
                            'type': 'output',
                            'data': '\n[收到 Ctrl+C 中断信号 - 这是模拟信号，设备将继续运行]\n>>> '
                        }))
                        print("🛑 收到 Ctrl+C 信号（WiFi模式下仅模拟）")
                        # 注意：WiFi模式下不能真正中断，因为设备需要保持运行以维持连接
                    elif cmd == 'ctrl_d':
                        # Ctrl+D: 软重启MicroPython
                        self.send_websocket_message(conn, json.dumps({
                            'type': 'output',
                            'data': '\n[收到 Ctrl+D 软重启信号 - 设备将重启]\n'
                        }))
                        print("🔄 收到 Ctrl+D 软重启信号，3秒后重启...")
                        time.sleep(3)
                        machine.reset()  # 真正重启设备
                    else:
                        # 其他命令当作 Python 代码执行
                        if cmd and not cmd.startswith('get_') and not cmd.startswith('reset_') and cmd != 'ctrl_c' and cmd != 'ctrl_d':
                            try:
                                # 捕获 print 输出：重定向 stdout
                                import sys
                                import io
                                
                                # 创建字符串缓冲区捕获输出
                                output_buffer = io.StringIO()
                                original_stdout = sys.stdout
                                sys.stdout = output_buffer
                                
                                try:
                                    # 执行 Python 代码（使用全局环境，确保模块可用）
                                    exec(cmd, globals())
                                    
                                    # 恢复 stdout
                                    sys.stdout = original_stdout
                                    
                                    # 获取输出内容
                                    output = output_buffer.getvalue()
                                    
                                    # 如果有输出，返回输出内容；否则返回OK
                                    if output:
                                        self.send_websocket_message(conn, json.dumps({
                                            'type': 'output',
                                            'data': output.rstrip()  # 去除末尾换行
                                        }))
                                    else:
                                        self.send_websocket_message(conn, json.dumps({
                                            'type': 'output',
                                            'data': 'OK'
                                        }))
                                finally:
                                    # 确保 stdout始终恢复
                                    sys.stdout = original_stdout
                                    output_buffer.close()
                                    
                            except Exception as e:
                                self.send_websocket_message(conn, json.dumps({
                                    'type': 'error',
                                    'data': str(e)
                                }))
                        else:
                            self.send_websocket_message(conn, json.dumps({
                                'type': 'error',
                                'data': '不支持的命令: ' + cmd
                            }))
                except Exception as e:
                    self.send_websocket_message(conn, json.dumps({
                        'type': 'error',
                        'data': str(e)
                    }))
                    
            elif msg_type == 'info':
                # ...
                try:
                    firmware_info = ota_manager.get_firmware_info()
                except:
                    firmware_info = {'version': 'v2.0.2', 'partition': 'unknown'}
                
                self.send_websocket_message(conn, json.dumps({
                    'type': 'info',
                    'data': {
                        'deviceId': self.device_id,
                        'deviceName': self.device_name,
                        'ip': self.ip,
                        'firmware': firmware_info.get('version', 'v2.0.2'),
                        'partition': firmware_info.get('partition', 'unknown')
                    }
                }))
            
            elif msg_type == 'ota_check':
                # ...
                try:
                    ota = ota_manager.OTAManager(CLOUD_API_BASE)
                    update_info = ota.check_for_updates()
                    self.send_websocket_message(conn, json.dumps({
                        'type': 'ota_check_result',
                        'data': update_info
                    }))
                except Exception as e:
                    self.send_websocket_message(conn, json.dumps({
                        'type': 'error',
                        'data': 'OTA检查失败: ' + str(e)
                    }))
            
            elif msg_type == 'ota_update':
                # ...
                try:
                    update_info = data.get('data')
                    print("🚀 开始OTA升级...")
                    
                    # ...
                    ota = ota_manager.OTAManager(CLOUD_API_BASE)
                    
                    # ...
                    def progress_callback(progress_data):
                        self.send_websocket_message(conn, json.dumps({
                            'type': 'ota_progress',
                            'data': progress_data
                        }))
                    
                    ota.set_progress_callback(progress_callback)
                    
                    # ...
                    _thread.start_new_thread(ota.perform_ota_update, (update_info,))
                    
                    self.send_websocket_message(conn, json.dumps({
                        'type': 'ota_started',
                        'data': 'OTA升级已启动'
                    }))
                    
                except Exception as e:
                    self.send_websocket_message(conn, json.dumps({
                        'type': 'error',
                        'data': 'OTA失败: ' + str(e)
                    }))
                
        except Exception as e:
            print("❌ 消息处理失败: " + str(e))
    
    def send_websocket_message(self, conn, message):
        """发送WebSocket消息（增强版：错误处理+超时）"""
        try:
            # 检查连接是否有效
            if conn not in self.ws_clients:
                print("⚠️  连接已失效，跳过发送")
                return False
            
            # 编码消息为UTF-8
            msg_bytes = message.encode('utf-8')
            frame = bytearray()
            frame.append(0x81)  # FIN + Text frame
            
            # 计算并添加payload长度
            length = len(msg_bytes)
            if length < 126:
                frame.append(length)
            elif length < 65536:
                frame.append(126)
                frame.extend(length.to_bytes(2, 'big'))
            else:
                frame.append(127)
                frame.extend(length.to_bytes(8, 'big'))
            
            frame.extend(msg_bytes)
            
            # 发送数据（带超时）
            conn.settimeout(5.0)
            conn.send(bytes(frame))
            return True
            
        except OSError as e:
            print("❌ 发送失败(OSError): " + str(e))
            # 连接已断开，从列表移除
            if conn in self.ws_clients:
                self.ws_clients.remove(conn)
            return False
        except Exception as e:
            print("❌ 发送消息失败: " + str(e))
            return False
    
    # ...
    def start_mdns(self):
        """启动mDNS广播（可选）"""
        try:
            import mdns
            mdns.start(self.device_name, '_tansuodou._tcp', WS_PORT)
            print("✅ mDNS广播已启动: " + str(self.device_name) + ".local")
        except:
            print("⚠️  mDNS不可用（跳过）")
    
    # ...
    def run(self):
        """运行主程序（生产环境标准：完整错误处理）"""
        print("\n" + "="*50)
        print("  🚀 搅豆物联主程序")
        print("  固件版本: v" + FIRMWARE_VERSION + " (Build " + FIRMWARE_BUILD + ")")
        print("="*50)
        
        # 步骤1: WiFi连接
        print("\n[步骤 1/4] WiFi连接")
        if not self.connect_wifi():
            print("\n" + "="*50)
            print("❌ WiFi连接失败，进入配网模式")
            print("="*50)
            import config_portal
            config_portal.start()
            return
        
        # 步骤2: 云端注册
        print("\n[步骤 2/4] 云端注册")
        registration_success = self.register_to_cloud()
        
        if not registration_success:
            print("\n⚠️  云端注册失败，但设备将继续运行（本地模式）")
            print("   您可以稍后在平台手动绑定此设备")
            print("   设备ID: " + str(self.device_id))
        
        # 步骤3: 启动mDNS（可选）
        print("\n[步骤 3/4] mDNS广播")
        self.start_mdns()
        
        # 步骤4: 启动心跳线程（仅在注册成功时）
        print("\n[步骤 4/4] 心跳服务")
        if registration_success:
            _thread.start_new_thread(self.heartbeat_thread, ())
        else:
            print("   ⏸️  心跳服务未启动（云端注册失败）")
        
        # 显示设备就绪信息
        print("\n" + "="*50)
        print("🎉 设备已就绪！")
        print("="*50)
        print("📋 设备ID: " + str(self.device_id))
        print("🏷️ 设备名称: " + str(self.device_name))
        print("📍 IP地址: " + str(self.ip))
        print("🔌 WebSocket: ws://" + str(self.ip) + ":" + str(WS_PORT))
        
        if registration_success:
            print("☁️  云端状态: ✅ 已注册")
        else:
            print("☁️  云端状态: ⚠️  本地模式")
        
        print("="*50 + "\n")
        
        # 启动 OTA HTTP 服务器
        print("\n[额外服务] OTA更新服务")
        self.start_ota_http_server()
        
        # 启动WebSocket服务器
        self.start_websocket_server()

# Main Entry
def start(config):
    """启动主程序"""
    device = TansuodouDevice(config)
    device.run()
