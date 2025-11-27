# TansuoDou IoT - File Manager Module
# 设备文件管理 HTTP API
# 支持：文件列表、读取、删除、上传

import os
try:
    import ujson as json
except:
    import json

def url_decode(s):
    \"\"\"简单的URL解码\"\"\"
    s = s.replace('%2F', '/')
    s = s.replace('%20', ' ')
    s = s.replace('%3A', ':')
    s = s.replace('%2E', '.')
    return s

def list_files(path='/'):
    \"\"\"列出目录下的文件和文件夹\"\"\"
    files = []
    try:
        # 确保路径有效
        if path == '' or path is None:
            path = '/'
        
        # 获取目录列表
        items = os.listdir(path if path != '/' else '/')
        
        for item in items:
            try:
                # 构建完整路径
                if path == '/':
                    full_path = '/' + item
                else:
                    full_path = path + '/' + item
                
                # 获取文件信息
                stat = os.stat(full_path)
                is_dir = (stat[0] & 0x4000) != 0
                
                files.append({
                    'name': item,
                    'type': 'dir' if is_dir else 'file',
                    'size': stat[6] if not is_dir else 0
                })
            except Exception as e:
                print('[WARN] 无法获取文件信息:', item, str(e))
                continue
                
    except Exception as e:
        print('[ERROR] 列出文件失败:', str(e))
        return []
    
    return files

def read_file(path):
    \"\"\"读取文件内容\"\"\"
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        raise Exception('读取文件失败: ' + str(e))

def delete_file(path):
    \"\"\"删除文件\"\"\"
    try:
        os.remove(path)
        return True
    except Exception as e:
        raise Exception('删除文件失败: ' + str(e))

def handle_file_api(path, query, method, body=''):
    \"\"\"处理文件管理API请求\"\"\"
    response = 'HTTP/1.1 200 OK\\r\\n'
    response += 'Content-Type: application/json\\r\\n'
    response += 'Access-Control-Allow-Origin: *\\r\\n'
    response += 'Connection: close\\r\\n\\r\\n'
    
    try:
        # 1. 文件列表
        if path == '/files' and method == 'GET':
            # 解析查询参数
            file_path = '/'
            if query:
                params = query.split('&')
                for param in params:
                    if param.startswith('path='):
                        file_path = url_decode(param[5:])
            
            files = list_files(file_path)
            response += json.dumps({'files': files})
        
        # 2. 读取文件
        elif path == '/files/read' and method == 'GET':
            # 解析查询参数
            file_path = ''
            if query:
                params = query.split('&')
                for param in params:
                    if param.startswith('path='):
                        file_path = url_decode(param[5:])
            
            if not file_path:
                response = 'HTTP/1.1 400 Bad Request\\r\\n\\r\\n'
                response += json.dumps({'error': '缺少path参数'})
            else:
                content = read_file(file_path)
                response += json.dumps({'content': content})
        
        # 3. 删除文件
        elif path == '/files/delete' and method == 'POST':
            # 解析请求体
            data = json.loads(body)
            file_path = data.get('path', '')
            
            if not file_path:
                response = 'HTTP/1.1 400 Bad Request\\r\\n\\r\\n'
                response += json.dumps({'error': '缺少path参数'})
            else:
                delete_file(file_path)
                response += json.dumps({'success': True})
        
        # 4. 上传文件（简化版：接收Base64编码的文件内容）
        elif path == '/files/upload' and method == 'POST':
            data = json.loads(body)
            file_path = data.get('path', '')
            content = data.get('content', '')
            
            if not file_path or not content:
                response = 'HTTP/1.1 400 Bad Request\\r\\n\\r\\n'
                response += json.dumps({'error': '缺少path或content参数'})
            else:
                # 写入文件
                with open(file_path, 'w') as f:
                    f.write(content)
                response += json.dumps({'success': True})
        
        else:
            response = 'HTTP/1.1 404 Not Found\\r\\n\\r\\n'
            response += json.dumps({'error': '未知的端点'})
            
    except Exception as e:
        response = 'HTTP/1.1 500 Internal Server Error\\r\\n'
        response += 'Content-Type: application/json\\r\\n\\r\\n'
        response += json.dumps({'error': str(e)})
    
    return response.encode('utf-8')
