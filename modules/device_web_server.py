# -*- coding: utf-8 -*-
# TansuoDou IoT 3.0 - Device Web Server
# 离线设备控制 Web 界面（类 ESPHome Web Server）
# 支持：传感器数据展示、开关控制、实时状态

import network
import socket
import machine
import ubinascii
import time
import _thread

# Import file manager
try:
    from file_manager import handle_file_api
    FILE_MANAGER_ENABLED = True
except:
    FILE_MANAGER_ENABLED = False
    print('[WARN] 文件管理模块未加载')

try:
    import ujson as json
except:
    import json

# Device state management
class DeviceState:
    def __init__(self):
        self.sensors = {}  # {sensor_name: value}
        self.switches = {}  # {switch_name: state}
        self.info = {}  # Device info
        
    def update_sensor(self, name, value, unit=''):
        self.sensors[name] = {'value': value, 'unit': unit, 'timestamp': time.time()}
    
    def update_switch(self, name, state):
        self.switches[name] = {'state': state, 'timestamp': time.time()}
    
    def get_json(self):
        return {
            'sensors': self.sensors,
            'switches': self.switches,
            'info': self.info
        }

# Global device state
device_state = DeviceState()

def get_device_id():
    """Get unique device ID"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac = ubinascii.hexlify(wlan.config('mac')).decode()
    return "TSD-" + mac[-8:].upper()

def get_device_info():
    """Get device information"""
    import sys
    import gc
    
    wlan = network.WLAN(network.STA_IF)
    device_id = get_device_id()
    
    info = {
        'device_id': device_id,
        'chip_id': machine.unique_id().hex().upper(),
        'platform': sys.platform,
        'version': sys.version,
        'free_memory': gc.mem_free(),
        'ip': wlan.ifconfig()[0] if wlan.isconnected() else 'N/A',
        'rssi': wlan.status('rssi') if wlan.isconnected() else 0,
        'uptime': time.time()
    }
    
    device_state.info = info
    return info

def get_dashboard_html():
    """Generate device dashboard HTML"""
    device_info = get_device_info()
    device_id = device_info['device_id']
    ip = device_info['ip']
    
    html = "HTTP/1.1 200 OK\r\n"
    html += "Content-Type: text/html; charset=utf-8\r\n"
    html += "Connection: close\r\n\r\n"
    
    html += '<!DOCTYPE html><html lang="zh-CN"><head>'
    html += '<meta charset="UTF-8">'
    html += '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
    html += '<title>设备控制 - ' + device_id + '</title>'
    
    # Embedded CSS
    html += '<style>'
    html += '*{margin:0;padding:0;box-sizing:border-box}'
    html += 'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
    html += 'background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}'
    html += '.container{max-width:1200px;margin:0 auto}'
    html += 'header{background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}'
    html += 'h1{font-size:24px;color:#1a1a1a;margin-bottom:8px}'
    html += '.device-id{font-family:monospace;color:#667eea;font-size:14px}'
    html += '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}'
    html += '.card{background:#fff;border-radius:16px;padding:24px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}'
    html += '.card-title{font-size:18px;font-weight:600;margin-bottom:16px;color:#1a1a1a}'
    html += '.sensor-item{display:flex;justify-content:space-between;align-items:center;'
    html += 'padding:12px;background:#f5f5f5;border-radius:8px;margin-bottom:8px}'
    html += '.sensor-label{color:#666;font-size:14px}'
    html += '.sensor-value{font-size:20px;font-weight:600;color:#667eea}'
    html += '.switch-item{display:flex;justify-content:space-between;align-items:center;'
    html += 'padding:16px;background:#f5f5f5;border-radius:8px;margin-bottom:12px}'
    html += '.switch-label{font-size:16px;color:#333}'
    html += '.toggle-btn{width:60px;height:32px;background:#ccc;border-radius:16px;position:relative;'
    html += 'cursor:pointer;transition:background 0.3s}'
    html += '.toggle-btn.on{background:#667eea}'
    html += '.toggle-btn::after{content:"";position:absolute;width:28px;height:28px;background:#fff;'
    html += 'border-radius:50%;top:2px;left:2px;transition:left 0.3s}'
    html += '.toggle-btn.on::after{left:30px}'
    html += '.info-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee}'
    html += '.info-label{color:#666;font-size:14px}'
    html += '.info-value{color:#333;font-size:14px;font-weight:500}'
    html += '.status-online{color:#10b981;font-weight:600}'
    html += '.refresh-btn{background:#667eea;color:#fff;border:none;padding:12px 24px;'
    html += 'border-radius:8px;cursor:pointer;font-size:14px;margin-top:16px}'
    html += '.refresh-btn:hover{background:#5568d3}'
    html += '</style></head>'
    
    html += '<body><div class="container">'
    
    # Header
    html += '<header>'
    html += '<h1>🎛️ 设备控制中心</h1>'
    html += '<div class="device-id">设备ID: ' + device_id + '</div>'
    html += '</header>'
    
    html += '<div class="grid">'
    
    # Device Info Card
    html += '<div class="card">'
    html += '<div class="card-title">📊 设备信息</div>'
    html += '<div class="info-item"><span class="info-label">状态</span>'
    html += '<span class="status-online">● 在线</span></div>'
    html += '<div class="info-item"><span class="info-label">IP地址</span>'
    html += '<span class="info-value">' + ip + '</span></div>'
    html += '<div class="info-item"><span class="info-label">WiFi信号</span>'
    html += '<span class="info-value">' + str(device_info['rssi']) + ' dBm</span></div>'
    html += '<div class="info-item"><span class="info-label">可用内存</span>'
    html += '<span class="info-value">' + str(device_info['free_memory'] // 1024) + ' KB</span></div>'
    html += '<div class="info-item"><span class="info-label">运行时间</span>'
    html += '<span class="info-value">' + str(int(device_info['uptime'])) + ' 秒</span></div>'
    html += '<button class="refresh-btn" onclick="location.reload()">🔄 刷新</button>'
    html += '</div>'
    
    # Sensors Card
    html += '<div class="card">'
    html += '<div class="card-title">🌡️ 传感器数据</div>'
    
    if device_state.sensors:
        for name, data in device_state.sensors.items():
            html += '<div class="sensor-item">'
            html += '<span class="sensor-label">' + name + '</span>'
            html += '<span class="sensor-value">' + str(data['value']) + ' ' + data['unit'] + '</span>'
            html += '</div>'
    else:
        html += '<p style="color:#999;text-align:center;padding:20px">暂无传感器数据</p>'
    
    html += '</div>'
    
    # Switches Card
    html += '<div class="card">'
    html += '<div class="card-title">💡 开关控制</div>'
    
    if device_state.switches:
        for name, data in device_state.switches.items():
            state_class = 'on' if data['state'] else ''
            html += '<div class="switch-item">'
            html += '<span class="switch-label">' + name + '</span>'
            html += '<div class="toggle-btn ' + state_class + '" '
            html += 'onclick="toggleSwitch(\'' + name + '\',' + str(not data['state']).lower() + ')"></div>'
            html += '</div>'
    else:
        html += '<p style="color:#999;text-align:center;padding:20px">暂无开关设备</p>'
    
    html += '</div>'
    
    html += '</div>'  # grid
    
    # JavaScript
    html += '<script>'
    html += 'function toggleSwitch(name,state){'
    html += 'fetch("/api/switch?name="+encodeURIComponent(name)+"&state="+(state?"on":"off"))'
    html += '.then(r=>r.json()).then(d=>{if(d.success)location.reload()});'
    html += '}'
    html += 'setInterval(()=>{location.reload()},30000);'  # Auto refresh every 30s
    html += '</script>'
    
    html += '</div></body></html>'
    
    return html.encode('utf-8')

def handle_api_request(path, query):
    """Handle API requests"""
    response = "HTTP/1.1 200 OK\r\n"
    response += "Content-Type: application/json\r\n"
    response += "Connection: close\r\n\r\n"
    
    if path == '/api/status':
        # Return device state
        data = device_state.get_json()
        response += json.dumps(data)
    
    elif path == '/api/switch':
        # Handle switch control
        params = parse_query(query)
        name = params.get('name', '')
        state = params.get('state', '') == 'on'
        
        if name:
            device_state.update_switch(name, state)
            # TODO: 实际控制GPIO引脚
            # Example: machine.Pin(pin_number, machine.Pin.OUT).value(1 if state else 0)
            response += json.dumps({'success': True, 'name': name, 'state': state})
        else:
            response += json.dumps({'success': False, 'error': 'Missing name'})
    
    else:
        response += json.dumps({'error': 'Unknown endpoint'})
    
    return response.encode('utf-8')

def parse_query(query_string):
    """Parse URL query string"""
    params = {}
    if query_string:
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
    return params

def start_web_server(port=80):
    """Start device web server (设备控制界面 - 80端口)"""
    device_id = get_device_id()
    
    # Create socket
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(20)  # ESP32-S3 N16R8: 启用PSRAM后支持32个Socket，设置20个队列
    
    print("\n[OK] 设备Web服务器已启动")
    print("   监听端口: " + str(port))
    print("   设备ID: " + device_id)
    print("   访问地址: http://<设备IP>:" + str(port))
    
    while True:
        conn = None
        try:
            conn, addr = s.accept()
            conn.settimeout(5.0)
            
            # Read request
            request = b""
            max_size = 2048
            
            while len(request) < max_size:
                try:
                    chunk = conn.recv(512)
                    if not chunk:
                        break
                    request += chunk
                    if b'\r\n\r\n' in request:
                        break
                except OSError:
                    break
            
            if len(request) == 0:
                continue
            
            request_str = request.decode('utf-8', 'ignore')
            
            # Parse request line
            lines = request_str.split('\r\n')
            if len(lines) > 0:
                method, path_query, _ = lines[0].split(' ', 2)
                
                # Split path and query
                if '?' in path_query:
                    path, query = path_query.split('?', 1)
                else:
                    path, query = path_query, ''
                
                # Route requests
                if path == '/' or path == '/index.html':
                    response = get_dashboard_html()
                    conn.send(response)
                elif path.startswith('/api/'):
                    response = handle_api_request(path, query)
                    conn.send(response)
                else:
                    # 404
                    conn.send(b'HTTP/1.1 404 Not Found\r\n\r\n')
        
        except Exception as e:
            print("[ERROR] Web服务器错误: " + str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

# Helper functions for device integration
def register_sensor(name, value, unit=''):
    """Register a sensor reading"""
    device_state.update_sensor(name, value, unit)

def register_switch(name, state=False):
    """Register a switch"""
    device_state.update_switch(name, state)

def start_file_manager_server(port=8081):
    """文件管理服务器（独立线程 - 8081端口）"""
    device_id = get_device_id()
    
    print("\n[OK] 文件管理服务器已启动")
    print("   监听端口: " + str(port))
    print("   访问地址: http://<设备IP>:" + str(port) + "/files")
    
    # Create socket
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(20)
    
    while True:
        conn = None
        try:
            conn, addr = s.accept()
            conn.settimeout(5.0)
            
            # Read request
            request = b""
            max_size = 2048
            
            while len(request) < max_size:
                try:
                    chunk = conn.recv(512)
                    if not chunk:
                        break
                    request += chunk
                    if b'\r\n\r\n' in request:
                        break
                except OSError:
                    break
            
            if len(request) == 0:
                continue
            
            request_str = request.decode('utf-8', 'ignore')
            
            # Parse request line
            lines = request_str.split('\r\n')
            if len(lines) > 0:
                method, path_query, _ = lines[0].split(' ', 2)
                
                # Split path and query
                if '?' in path_query:
                    path, query = path_query.split('?', 1)
                else:
                    path, query = path_query, ''
                
                # 处理文件管理API请求
                if path.startswith('/files'):
                    body = ''
                    if method == 'POST' and '\r\n\r\n' in request_str:
                        body = request_str.split('\r\n\r\n', 1)[1]
                    response = handle_file_api(path, query, method, body)
                    conn.send(response)
                else:
                    # 404
                    conn.send(b'HTTP/1.1 404 Not Found\r\n\r\n')
        
        except Exception as e:
            print("[ERROR] 文件管理服务器错误: " + str(e))
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

def start():
    """Start web server (entry point)"""
    # 启动两个服务器：
    # 1. 设备控制界面 - 80端口
    # 2. 文件管理服务器 - 8081端口（独立线程）
    
    # 启动文件管理服务器（独立线程）
    if FILE_MANAGER_ENABLED:
        import _thread
        _thread.start_new_thread(start_file_manager_server, ())
    
    # 启动设备控制界面（主线程）
    start_web_server(80)
