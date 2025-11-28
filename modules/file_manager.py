# -*- coding: utf-8 -*-
# TansuoDou IoT - File Manager Module
# 设备文件管理 HTTP API
# 支持：文件列表、读取、删除、上传

import os
try:
    import ujson as json
except:
    import json

def url_decode(s):
    """简单的URL解码"""
    s = s.replace('%2F', '/')
    s = s.replace('%20', ' ')
    s = s.replace('%3A', ':')
    s = s.replace('%2E', '.')
    return s

def list_files(path='/'):
    """列出目录下的文件和文件夹"""
    files = []
    try:
        if path == '' or path is None:
            path = '/'
        
        items = os.listdir(path if path != '/' else '/')
        
        for item in items:
            try:
                if path == '/':
                    full_path = '/' + item
                else:
                    full_path = path + '/' + item
                
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
    """读取文件内容"""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        raise Exception('读取文件失败: ' + str(e))

def delete_file(path):
    """删除文件"""
    try:
        os.remove(path)
        return True
    except Exception as e:
        raise Exception('删除文件失败: ' + str(e))

def handle_file_api(path, query, method, body=''):
    """处理文件管理API请求"""
    try:
        if path == '/files' and method == 'GET':
            # 列出文件
            file_path = '/'
            if query:
                params = query.split('&')
                for param in params:
                    if param.startswith('path='):
                        file_path = url_decode(param[5:])
            
            files = list_files(file_path)
            response = 'HTTP/1.1 200 OK\r\n'
            response += 'Content-Type: application/json\r\n'
            response += 'Access-Control-Allow-Origin: *\r\n'
            response += 'Connection: close\r\n\r\n'
            response += json.dumps({'files': files})
            return response.encode('utf-8')
        
        elif path == '/files/read' and method == 'GET':
            # 读取文件
            file_path = ''
            if query:
                params = query.split('&')
                for param in params:
                    if param.startswith('path='):
                        file_path = url_decode(param[5:])
            
            if not file_path:
                response = 'HTTP/1.1 400 Bad Request\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'error': '缺少path参数'})
            else:
                content = read_file(file_path)
                response = 'HTTP/1.1 200 OK\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'content': content})
            return response.encode('utf-8')
        
        elif path == '/files/delete' and method == 'POST':
            # 删除文件
            if not body:
                response = 'HTTP/1.1 400 Bad Request\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'error': '缺少请求体'})
                return response.encode('utf-8')
            
            data = json.loads(body)
            file_path = data.get('path', '')
            
            if not file_path:
                response = 'HTTP/1.1 400 Bad Request\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'error': '缺少path参数'})
            else:
                delete_file(file_path)
                response = 'HTTP/1.1 200 OK\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'success': True})
            return response.encode('utf-8')
        
        elif path == '/files/upload' and method == 'POST':
            # 上传文件
            if not body:
                response = 'HTTP/1.1 400 Bad Request\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'error': '缺少请求体'})
                return response.encode('utf-8')
            
            data = json.loads(body)
            file_path = data.get('path', '')
            content = data.get('content', '')
            
            if not file_path:
                response = 'HTTP/1.1 400 Bad Request\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'error': '缺少path参数'})
            else:
                with open(file_path, 'w') as f:
                    f.write(content)
                response = 'HTTP/1.1 200 OK\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += 'Connection: close\r\n\r\n'
                response += json.dumps({'success': True})
            return response.encode('utf-8')
        
        else:
            # 404 - 未知端点
            response = 'HTTP/1.1 404 Not Found\r\n'
            response += 'Content-Type: application/json\r\n'
            response += 'Access-Control-Allow-Origin: *\r\n'
            response += 'Connection: close\r\n\r\n'
            response += json.dumps({'error': '未知的端点'})
            return response.encode('utf-8')
            
    except json.JSONDecodeError as e:
        # JSON解析错误
        response = 'HTTP/1.1 400 Bad Request\r\n'
        response += 'Content-Type: application/json\r\n'
        response += 'Access-Control-Allow-Origin: *\r\n'
        response += 'Connection: close\r\n\r\n'
        response += json.dumps({'error': 'JSON格式错误: ' + str(e)})
        return response.encode('utf-8')
    
    except Exception as e:
        # 通用错误
        response = 'HTTP/1.1 500 Internal Server Error\r\n'
        response += 'Content-Type: application/json\r\n'
        response += 'Access-Control-Allow-Origin: *\r\n'
        response += 'Connection: close\r\n\r\n'
        response += json.dumps({'error': str(e)})
        return response.encode('utf-8')
