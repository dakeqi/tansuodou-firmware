# TansuoDou 2.0 - WiFi Captive Portal with DNS Server
# Based on: https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal

import network
import socket
import machine
import ubinascii
import time
import _thread

try:
    import ujson as json
except:
    import json

# Device ID
def get_device_id():
    """Get unique device ID"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac = ubinascii.hexlify(wlan.config('mac')).decode()
    return "TSD-" + mac[-8:].upper()

# AP Hotspot
def create_ap_hotspot():
    """Create AP hotspot"""
    device_id = get_device_id()
    ap_name = "TansuoDou-" + device_id[-4:]
    
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_name, password='', authmode=network.AUTH_OPEN)
    
    # ...
    while not ap.active():
        time.sleep(0.1)
    
    ip_info = ap.ifconfig()
    
    print("\n[OK] AP热点已创建")
    print("   SSID: " + ap_name)
    print("   IP地址: " + ip_info[0])
    print("   配网地址: http://" + ip_info[0])
    
    return ap, ap_name

# HTML Config Page
def get_config_html(device_id):
    """Generate config page - 分段构建避免MicroPython字符串限制"""
    # ...
    html = "HTTP/1.1 200 OK\r\n"
    html += "Content-Type: text/html; charset=utf-8\r\n"
    html += "Connection: close\r\n\r\n"
    
    # ...
    html += '<!DOCTYPE html><html lang="zh-CN"><head>'
    html += '<meta charset="UTF-8">'
    html += '<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">'
    html += '<title>TansuoDou WiFi Setup</title>'
    
    # ...
    html += '<style>'
    html += '*{margin:0;padding:0;box-sizing:border-box}'
    html += 'body{font-family:sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);'
    html += 'min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}'
    html += '.container{background:#fff;border-radius:24px;padding:40px 30px;max-width:420px;width:100%;'
    html += 'box-shadow:0 20px 60px rgba(0,0,0,0.3)}'
    html += '.logo{text-align:center;margin-bottom:30px}'
    html += '.logo-icon{width:60px;height:60px;background:linear-gradient(135deg,#667eea,#764ba2);'
    html += 'border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:32px;margin-bottom:12px}'
    html += 'h1{color:#1a1a1a;font-size:26px;font-weight:700;text-align:center;margin-bottom:8px}'
    html += '.subtitle{text-align:center;color:#666;font-size:14px;margin-bottom:20px}'
    html += '.device-id-box{background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);'
    html += 'padding:16px;border-radius:12px;margin-bottom:30px;text-align:center}'
    html += '.device-id-label{font-size:12px;color:#666;margin-bottom:4px}'
    html += '.device-id-value{font-family:monospace;font-size:18px;font-weight:bold;color:#667eea;letter-spacing:2px}'
    html += '.form-group{margin-bottom:20px}'
    html += 'label{display:block;margin-bottom:8px;color:#333;font-weight:600;font-size:14px}'
    html += 'input{width:100%;padding:14px 16px;border:2px solid #e0e0e0;border-radius:12px;'
    html += 'font-size:16px;background:#f9f9f9}'
    html += 'input:focus{outline:none;border-color:#667eea;background:#fff;'
    html += 'box-shadow:0 0 0 4px rgba(102,126,234,0.1)}'
    html += 'button{width:100%;padding:16px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);'
    html += 'color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;margin-top:10px}'
    html += '.tips{margin-top:24px;padding:16px;background:#fff3cd;border-left:4px solid #ffc107;'
    html += 'border-radius:8px;font-size:13px;color:#856404;line-height:1.6}'
    html += '.tips-title{font-weight:700;margin-bottom:8px}'
    html += '.tips ul{margin-left:20px}'
    html += '.tips li{margin-bottom:4px}'
    html += '</style></head>'
    
    # ...
    html += '<body><div class="container">'
    html += '<div class="logo"><div class="logo-icon">&#128268;</div></div>'
    html += '<h1>TansuoDou IoT 2.0</h1>'
    html += '<div class="subtitle">WiFi Configuration Portal</div>'
    html += '<div class="device-id-box">'
    html += '<div class="device-id-label">Device ID</div>'
    html += '<div class="device-id-value">' + device_id + '</div>'
    html += '</div>'
    
    # ...
    html += '<form method="POST" action="/config">'
    html += '<div class="form-group">'
    html += '<label for="ssid">&#128246; WiFi名称 (SSID)</label>'
    html += '<input type="text" id="ssid" name="ssid" required placeholder="请输入WiFi名称" autocomplete="off">'
    html += '</div>'
    html += '<div class="form-group">'
    html += '<label for="password">&#128274; WiFi密码</label>'
    html += '<input type="password" id="password" name="password" placeholder="请输入WiFi密码（无密码可留空）">'
    html += '</div>'
    html += '<div class="form-group">'
    html += '<label for="api_base">&#127760; API地址（可选）</label>'
    html += '<input type="text" id="api_base" name="api_base" value="http://192.168.1.105:3001/api" placeholder="本地测试或云端API">'
    html += '</div>'
    html += '<div class="form-group">'
    html += '<label for="device_name">&#127991; 设备名称（可选）</label>'
    html += '<input type="text" id="device_name" name="device_name" value="' + device_id + '" placeholder="例如：客厅-智能灯">'
    html += '</div>'
    html += '<button type="submit">&#9989; 连接WiFi</button>'
    html += '</form>'
    
    # ...
    html += '<div class="tips">'
    html += '<div class="tips-title">&#128161; 温馨提示</div>'
    html += '<ul>'
    html += '<li>请确保输入正确的WiFi账号和密码</li>'
    html += '<li>设备将在连接成功后自动重启</li>'
    html += '<li>请记住设备ID，稍后在平台中使用</li>'
    html += '</ul></div>'
    html += '</div></body></html>'
    
    return html.encode('utf-8')

# Success Page
def get_success_html():
    """Success page - 分段构建"""
    html = "HTTP/1.1 200 OK\r\n"
    html += "Content-Type: text/html; charset=utf-8\r\n"
    html += "Connection: close\r\n\r\n"
    html += '<!DOCTYPE html><html><head>'
    html += '<meta charset="utf-8">'
    html += '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
    html += '<title>配置成功</title>'
    html += '<style>'
    html += 'body{font-family:sans-serif;text-align:center;padding:50px 20px;'
    html += 'background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:#fff;'
    html += 'min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}'
    html += '.success-icon{font-size:80px;margin-bottom:20px}'
    html += 'h1{font-size:36px;margin-bottom:20px}'
    html += 'p{font-size:18px;line-height:1.8}'
    html += '</style></head>'
    html += '<body>'
    html += '<div class="success-icon">&#9989;</div>'
    html += '<h1>配置成功！</h1>'
    html += '<p>设备正在连接WiFi...</p>'
    html += '<p>Please connect to TansuoDou platform later</p>'
    html += '<p style="margin-top:30px;font-size:14px;opacity:0.9">设备将在3秒后自动重启</p>'
    html += '</body></html>'
    return html.encode('utf-8')

# HTTP Parser
def url_decode(s):
    """Complete URL decode function"""
    result = ""
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                # ...
                hex_str = s[i+1:i+3]
                char_code = int(hex_str, 16)
                result += chr(char_code)
                i += 3
            except:
                result += s[i]
                i += 1
        elif s[i] == '+':
            result += ' '
            i += 1
        else:
            result += s[i]
            i += 1
    return result

def parse_post_data(request_body):
    """Parse POST data（完整URL解码）"""
    params = {}
    try:
        if not request_body:
            return params
        
        for param in request_body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # ...
                params[key] = url_decode(value)
            else:
                # ...
                params[param] = ''
        
        return params
    except Exception as e:
        print("解析参数失败: " + str(e))
        return params

# Save Config
def save_wifi_config(ssid, password, device_name, api_base='http://192.168.1.105:3001/api'):
    """Save WiFi config"""
    config = {
        'ssid': ssid,
        'password': password,
        'device_name': device_name,
        'api_base': api_base
    }
    try:
        with open('/wifi_config.json', 'w') as f:
            json.dump(config, f)
        print("[OK] WiFi配置已保存: " + ssid)
        print("     API地址: " + api_base)
        return True
    except Exception as e:
        print("[ERROR] 保存配置失败: " + str(e))
        return False

# HTTP Server
def start_http_server():
    """Start HTTP server（带超时和错误处理）"""
    device_id = get_device_id()
    
    # Createsocket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print("\n[OK] HTTP配网服务器已启动")
    print("   监听端口: 80")
    
    while True:
        conn = None
        try:
            conn, addr = s.accept()
            conn.settimeout(5.0)  # 设置5秒超时
            print("\n[CONN] 客户端连接: " + str(addr))
            
            # ...
            request = b""
            max_request_size = 2048
            
            while len(request) < max_request_size:
                try:
                    chunk = conn.recv(512)
                    if not chunk:
                        break
                    request += chunk
                    if b'\r\n\r\n' in request:
                        break
                except OSError:
                    # ...
                    break
            
            if len(request) == 0:
                continue
            
            request_str = request.decode('utf-8', 'ignore')
            
            # ...
            if 'GET / ' in request_str or 'GET /index' in request_str:
                response = get_config_html(device_id)
                conn.send(response)
                
            # ...
            elif 'POST /config' in request_str:
                # ...
                if '\r\n\r\n' in request_str:
                    body = request_str.split('\r\n\r\n')[1]
                    params = parse_post_data(body)
                    
                    ssid = params.get('ssid', '')
                    password = params.get('password', '')
                    device_name = params.get('device_name', device_id)
                    api_base = params.get('api_base', 'http://192.168.1.105:3001/api')  # 本地测试默认值
                    
                    if ssid:
                        # ...
                        if save_wifi_config(ssid, password, device_name, api_base):
                            # ...
                            response = get_success_html()
                            conn.send(response)
                            conn.close()
                            
                            print("\n[OK] WiFi配置完成")
                            print("   SSID: " + ssid)
                            print("   设备名称: " + device_name)
                            print("\n[INFO] 3秒后重启设备...")
                            
                            time.sleep(3)
                            machine.reset()
                    else:
                        conn.send(b'HTTP/1.1 400 Bad Request\r\n\r\n')
            
            # ...
            else:
                redirect = b'HTTP/1.1 302 Found\r\nLocation: http://192.168.4.1/\r\n\r\n'
                conn.send(redirect)
            
            
        except Exception as e:
            print("[ERROR] 服务器错误: " + str(e))
        finally:
            # ...
            if conn:
                try:
                    conn.close()
                except:
                    pass

# DNS Server Thread
def dns_server_thread(ip):
    """DNS server thread"""
    try:
        import dns_server
        dns = dns_server.DNSServer(ip)
        if dns.start():
            # Keep processing DNS queries
            while True:
                dns.process()
                time.sleep(0.01)  # Small delay to prevent CPU overload
    except Exception as e:
        print("[ERROR] DNS线程错误: " + str(e))

# Main Entry
def start():
    """Start config portal with DNS server"""
    print("\n" + "="*50)
    print("  WiFi配网门户 + DNS服务器")
    print("="*50)
    
    # Create AP hotspot
    ap, ap_name = create_ap_hotspot()
    ap_ip = ap.ifconfig()[0]
    
    # Start DNS server in background thread
    print("\n[INFO] 启动DNS服务器线程...")
    try:
        _thread.start_new_thread(dns_server_thread, (ap_ip,))
        print("[OK] DNS服务器线程已启动")
    except Exception as e:
        print("[WARN] DNS服务器启动失败: " + str(e))
        print("       (将继续提供HTTP配网服务)")
    
    # Start HTTP server (main thread)
    start_http_server()
