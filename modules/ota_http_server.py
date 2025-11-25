# TansuoDou IoT - HTTP OTA Server for ESP32
# 提供 HTTP 端点用于 OTA 固件更新

import socket
import machine
import time
import gc

try:
    import ujson as json
except:
    import json

try:
    import ota_manager
except:
    print("⚠️  OTA模块未找到")

# 全局变量：OTA 进度状态
ota_progress = {
    'stage': 'idle',
    'progress': 0,
    'message': '',
    'timestamp': 0
}

class OTAHTTPServer:
    """HTTP OTA 服务器"""
    
    def __init__(self, port=8080):
        self.port = port
        self.sock = None
        self.ota_manager = None
        self.running = False
        
    def set_ota_manager(self, manager):
        """设置 OTA 管理器"""
        self.ota_manager = manager
        # 设置进度回调
        if manager:
            manager.set_progress_callback(self.update_progress)
    
    def update_progress(self, progress_data):
        """更新 OTA 进度（回调函数）"""
        global ota_progress
        ota_progress['stage'] = progress_data.get('stage', 'idle')
        ota_progress['progress'] = progress_data.get('progress', 0)
        ota_progress['message'] = progress_data.get('message', '')
        ota_progress['timestamp'] = time.time()
    
    def start(self):
        """启动 HTTP 服务器"""
        try:
            addr = socket.getaddrinfo('0.0.0.0', self.port)[0][-1]
            self.sock = socket.socket()
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(addr)
            self.sock.listen(3)
            self.sock.settimeout(2.0)  # 2秒超时
            self.running = True
            
            print("\n" + "="*50)
            print("🌐 HTTP OTA服务器已启动")
            print("="*50)
            print("   端口: " + str(self.port))
            print("   端点:")
            print("     POST /ota        - URL更新命令")
            print("     POST /update     - 上传固件")
            print("     GET  /ota-progress - 获取进度")
            print("     GET  /status     - 获取设备状态")
            print("="*50)
            
            return True
            
        except Exception as e:
            print("❌ HTTP服务器启动失败: " + str(e))
            return False
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
    
    def handle_request(self):
        """处理单个 HTTP 请求（非阻塞）"""
        if not self.running or not self.sock:
            return
        
        conn = None
        try:
            # 非阻塞接受连接
            conn, addr = self.sock.accept()
            conn.settimeout(5.0)
            
            # 读取请求
            request = conn.recv(1024).decode('utf-8')
            
            # 解析请求行
            lines = request.split('\r\n')
            if len(lines) < 1:
                self.send_response(conn, 400, {'error': 'Invalid request'})
                return
            
            method, path, _ = lines[0].split(' ', 2)
            
            # 路由处理
            if method == 'POST' and path == '/ota':
                self.handle_ota_url(conn, request)
            elif method == 'POST' and path == '/update':
                self.handle_ota_upload(conn, request)
            elif method == 'GET' and path == '/ota-progress':
                self.handle_get_progress(conn)
            elif method == 'GET' and path == '/status':
                self.handle_get_status(conn)
            else:
                self.send_response(conn, 404, {'error': 'Not found'})
            
        except OSError as e:
            # 超时或无连接，正常情况（静默处理）
            err = e.args[0] if e.args else None
            # 忽略 EAGAIN(11) 和 ETIMEDOUT(116)
            if err != 11 and err != 116:  # EAGAIN, ETIMEDOUT
                print("⚠️  Socket错误: " + str(e))
        except Exception as e:
            print("❌ 请求处理错误: " + str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def handle_ota_url(self, conn, request):
        """处理 POST /ota - 从 URL 下载固件更新"""
        try:
            # 解析 JSON body
            body_start = request.find('\r\n\r\n') + 4
            if body_start < 4:
                self.send_response(conn, 400, {'error': 'No body'})
                return
            
            body = request[body_start:]
            data = json.loads(body)
            
            firmware_url = data.get('url')
            if not firmware_url:
                self.send_response(conn, 400, {'error': 'Missing url parameter'})
                return
            
            # 立即返回响应（异步更新）
            self.send_response(conn, 200, {
                'success': True,
                'message': 'OTA update started',
                'url': firmware_url
            })
            
            # 延迟执行 OTA（给客户端时间接收响应）
            time.sleep(0.5)
            
            # 执行 OTA 更新
            self.perform_ota_from_url(firmware_url)
            
        except Exception as e:
            self.send_response(conn, 500, {'error': str(e)})
    
    def handle_ota_upload(self, conn, request):
        """处理 POST /update - 接收上传的固件"""
        try:
            # 查找 Content-Length
            content_length = 0
            for line in request.split('\r\n'):
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            
            if content_length == 0:
                self.send_response(conn, 400, {'error': 'No Content-Length'})
                return
            
            # 查找 boundary（multipart）
            boundary = None
            for line in request.split('\r\n'):
                if 'boundary=' in line:
                    boundary = '--' + line.split('boundary=')[1].strip()
                    break
            
            if not boundary:
                self.send_response(conn, 400, {'error': 'No boundary found'})
                return
            
            # 立即返回响应
            self.send_response(conn, 200, {
                'success': True,
                'message': 'Upload started',
                'size': content_length
            })
            
            # 接收并写入固件
            self.receive_and_flash_firmware(conn, content_length, boundary)
            
        except Exception as e:
            print("❌ 上传处理错误: " + str(e))
    
    def handle_get_progress(self, conn):
        """处理 GET /ota-progress - 获取 OTA 进度"""
        global ota_progress
        self.send_response(conn, 200, ota_progress)
    
    def handle_get_status(self, conn):
        """处理 GET /status - 获取设备状态"""
        import network
        wlan = network.WLAN(network.STA_IF)
        
        status = {
            'connected': wlan.isconnected(),
            'ip': wlan.ifconfig()[0] if wlan.isconnected() else None,
            'rssi': wlan.status('rssi') if wlan.isconnected() else None,
            'firmware': ota_manager.FIRMWARE_VERSION if 'ota_manager' in globals() else 'unknown',
            'free_memory': gc.mem_free(),
            'uptime': time.time()
        }
        
        self.send_response(conn, 200, status)
    
    def perform_ota_from_url(self, firmware_url):
        """从 URL 执行 OTA 更新"""
        try:
            if not self.ota_manager:
                print("❌ OTA管理器未设置")
                return
            
            print("\n🚀 开始从 URL 更新固件")
            print("   URL: " + firmware_url)
            
            # 简单的更新信息（实际项目中应该先检查版本）
            update_info = {
                'version': 'latest',
                'url': firmware_url,
                'size': 0,  # 需要从 HTTP HEAD 获取
                'checksum': ''  # 如果有的话
            }
            
            # 先获取文件大小
            try:
                import urequests
                response = urequests.head(firmware_url, timeout=10)
                update_info['size'] = int(response.headers.get('Content-Length', 0))
                response.close()
            except:
                # 如果 HEAD 失败，在下载时获取
                pass
            
            # 执行 OTA
            self.ota_manager.perform_ota_update(update_info)
            
        except Exception as e:
            print("❌ OTA失败: " + str(e))
            self.update_progress({
                'stage': 'error',
                'progress': 0,
                'message': str(e)
            })
    
    def receive_and_flash_firmware(self, conn, total_size, boundary):
        """接收上传的固件并烧录"""
        try:
            from esp32 import Partition
            
            # 获取 OTA 分区
            running = Partition(Partition.RUNNING)
            ota_partition = running.get_next_update()
            
            print("🔄 准备接收固件上传...")
            print("   大小: " + str(total_size) + " bytes")
            
            # 擦除分区
            self.update_progress({
                'stage': 'upload',
                'progress': 5,
                'message': '擦除Flash分区...'
            })
            ota_partition.erase()
            
            # 接收数据
            received = 0
            chunk_size = 4096
            write_offset = 0
            
            while received < total_size:
                chunk = conn.recv(min(chunk_size, total_size - received))
                if not chunk:
                    break
                
                chunk_len = len(chunk)
                
                # 写入分区（需要对齐）
                if chunk_len == chunk_size:
                    ota_partition.writeblocks(write_offset // chunk_size, chunk)
                else:
                    buffer = bytearray(chunk_size)
                    buffer[:chunk_len] = chunk
                    for i in range(chunk_len, chunk_size):
                        buffer[i] = 0xFF
                    ota_partition.writeblocks(write_offset // chunk_size, buffer)
                
                write_offset += chunk_len
                received += chunk_len
                
                # 更新进度
                progress = 5 + int((received / total_size) * 85)
                if received % (64 * 1024) == 0:
                    self.update_progress({
                        'stage': 'upload',
                        'progress': progress,
                        'message': str(received) + ' / ' + str(total_size) + ' bytes'
                    })
            
            # 设置启动分区
            self.update_progress({
                'stage': 'activate',
                'progress': 95,
                'message': '设置启动分区...'
            })
            ota_partition.set_boot()
            
            # 完成
            self.update_progress({
                'stage': 'complete',
                'progress': 100,
                'message': '更新完成，3秒后重启...'
            })
            
            print("✅ 固件上传完成，准备重启...")
            time.sleep(3)
            machine.reset()
            
        except Exception as e:
            print("❌ 烧录失败: " + str(e))
            self.update_progress({
                'stage': 'error',
                'progress': 0,
                'message': str(e)
            })
    
    def send_response(self, conn, status_code, data):
        """发送 JSON 响应"""
        try:
            status_text = {
                200: 'OK',
                400: 'Bad Request',
                404: 'Not Found',
                500: 'Internal Server Error'
            }.get(status_code, 'Unknown')
            
            response = 'HTTP/1.1 ' + str(status_code) + ' ' + status_text + '\r\n'
            response += 'Content-Type: application/json\r\n'
            response += 'Access-Control-Allow-Origin: *\r\n'
            response += 'Connection: close\r\n\r\n'
            
            body = json.dumps(data)
            response += body
            
            conn.send(response.encode('utf-8'))
            
        except Exception as e:
            print("❌ 响应发送失败: " + str(e))

# 便捷函数
def start_ota_server(port=80, cloud_api_base='https://tansuodou.com/api'):
    """启动 OTA HTTP 服务器"""
    try:
        # 创建 OTA 管理器
        manager = ota_manager.OTAManager(cloud_api_base)
        
        # 创建 HTTP 服务器
        server = OTAHTTPServer(port)
        server.set_ota_manager(manager)
        
        # 启动服务器
        if server.start():
            return server
        else:
            return None
            
    except Exception as e:
        print("❌ OTA服务器启动失败: " + str(e))
        return None
