# IDE Helper - Web Serial IDE 与 MicroPython 设备通信桥梁
# 搭豆物联 2.0
# 版本: 1.0.0
# 
# 功能：
# - 文件系统管理 (ls/read/write/delete)
# - WiFi 扫描和状态
# - 代码执行和输出捕获
# - 设备信息查询
# - 垃圾回收和系统操作

import sys
import json
import time

try:
    import os
except ImportError:
    import uos as os

try:
    import gc
except ImportError:
    gc = None

try:
    import network
except ImportError:
    network = None

try:
    import machine
except ImportError:
    machine = None


class IDEHelper:
    """Web Serial IDE 协议处理器"""
    
    def __init__(self):
        self.buffer = ""
        
    def send_response(self, data):
        """发送 JSON 响应"""
        try:
            response = json.dumps(data)
            print(response)
            self.flush_stdout()
        except Exception as e:
            error = json.dumps({"status": "ERROR", "msg": "response encoding failed: " + str(e)})
            print(error)
            self.flush_stdout()
    
    def flush_stdout(self):
        """安全刷新 stdout"""
        try:
            sys.stdout.flush()
        except:
            pass
    
    def send_error(self, message):
        """发送错误响应"""
        self.send_response({"status": "ERROR", "msg": message})
    
    def send_ok(self, data=None):
        """发送成功响应"""
        response = {"status": "OK"}
        if data:
            response.update(data)
        self.send_response(response)
    
    # ========== 设备信息 ==========
    def cmd_device_info(self, params):
        """获取设备信息"""
        try:
            # 导入 boot 模块获取版本信息
            try:
                import boot
                firmware_version = boot.FIRMWARE_VERSION
                firmware_build = boot.FIRMWARE_BUILD
                firmware_name = boot.FIRMWARE_NAME
            except:
                firmware_version = "unknown"
                firmware_build = "unknown"
                firmware_name = "搭豆智联 DaDou IoT"
            
            info = {
                "type": "device_info",
                "firmware": {
                    "name": firmware_name,
                    "version": firmware_version,
                    "build": firmware_build
                },
                "platform": sys.platform,
                "implementation": sys.implementation[0] if hasattr(sys, 'implementation') else "unknown"
            }
            
            # 内存信息
            if gc:
                info["memory"] = {
                    "free": gc.mem_free(),
                    "allocated": gc.mem_alloc()
                }
            
            # 存储信息
            try:
                stat = os.statvfs('/')
                info["storage"] = {
                    "total": stat[0] * stat[2],
                    "free": stat[0] * stat[3]
                }
            except:
                pass
            
            self.send_ok(info)
        except Exception as e:
            self.send_error("get device info failed: " + str(e))
    
    # ========== 文件系统操作 ==========
    def cmd_list_files(self, params):
        """列出文件"""
        try:
            path = params.get('path', '/')
            files = []
            
            for name in os.listdir(path):
                try:
                    full_path = path.rstrip('/') + '/' + name if path != '/' else '/' + name
                    stat = os.stat(full_path)
                    files.append({
                        "name": name,
                        "size": stat[6],
                        "is_dir": (stat[0] & 0x4000) != 0
                    })
                except:
                    pass
            
            self.send_ok({
                "type": "file_list",
                "path": path,
                "files": files
            })
        except Exception as e:
            self.send_error("list files failed: " + str(e))
    
    def cmd_read_file(self, params):
        """读取文件"""
        try:
            path = params.get('path') or params.get('name')
            if not path:
                self.send_error("missing 'path' parameter")
                return
            
            with open(path, 'r') as f:
                content = f.read()
            
            self.send_ok({
                "type": "file_content",
                "path": path,
                "content": content,
                "size": len(content)
            })
        except Exception as e:
            self.send_error("read file failed: " + str(e))
    
    def cmd_write_file(self, params):
        """写入文件"""
        try:
            path = params.get('path') or params.get('name')
            content = params.get('content') or params.get('data', '')
            
            if not path:
                self.send_error("missing 'path' parameter")
                return
            
            with open(path, 'w') as f:
                f.write(content)
            
            self.send_ok({
                "type": "file_write",
                "path": path,
                "size": len(content),
                "msg": "file saved successfully"
            })
        except Exception as e:
            self.send_error("write file failed: " + str(e))
    
    def cmd_delete_file(self, params):
        """删除文件"""
        try:
            path = params.get('path') or params.get('name')
            if not path:
                self.send_error("missing 'path' parameter")
                return
            
            os.remove(path)
            
            self.send_ok({
                "type": "file_delete",
                "path": path,
                "msg": "file deleted successfully"
            })
        except Exception as e:
            self.send_error("delete file failed: " + str(e))
    
    # ========== WiFi 操作 ==========
    def cmd_wifi_scan(self, params):
        """扫描 WiFi 网络"""
        try:
            if not network:
                self.send_error("network module not available")
                return
            
            sta = network.WLAN(network.STA_IF)
            sta.active(True)
            
            networks = []
            for ssid, bssid, channel, rssi, authmode, hidden in sta.scan():
                networks.append({
                    "ssid": ssid.decode('utf-8'),
                    "rssi": rssi,
                    "channel": channel,
                    "secure": authmode > 0
                })
            
            self.send_ok({
                "type": "wifi_scan",
                "networks": networks,
                "count": len(networks)
            })
        except Exception as e:
            self.send_error("wifi scan failed: " + str(e))
    
    def cmd_wifi_status(self, params):
        """获取 WiFi 状态"""
        try:
            if not network:
                self.send_error("network module not available")
                return
            
            sta = network.WLAN(network.STA_IF)
            
            status = {
                "type": "wifi_status",
                "connected": sta.isconnected(),
                "active": sta.active()
            }
            
            if sta.isconnected():
                ifconfig = sta.ifconfig()
                status.update({
                    "ip": ifconfig[0],
                    "netmask": ifconfig[1],
                    "gateway": ifconfig[2],
                    "dns": ifconfig[3]
                })
                try:
                    status["rssi"] = sta.status('rssi')
                except:
                    pass
            
            self.send_ok(status)
        except Exception as e:
            self.send_error("get wifi status failed: " + str(e))
    
    # ========== 代码执行 ==========
    def cmd_exec_code(self, params):
        """执行 Python 代码并捕获输出"""
        try:
            code = params.get('code')
            if not code:
                self.send_error("missing 'code' parameter")
                return
            
            # 捕获标准输出
            import io
            output_buffer = io.StringIO()
            original_stdout = sys.stdout
            sys.stdout = output_buffer
            
            error_msg = None
            try:
                exec(code, globals())
            except Exception as e:
                error_msg = str(e)
            finally:
                sys.stdout = original_stdout
                output = output_buffer.getvalue()
                output_buffer.close()
            
            if error_msg:
                self.send_response({
                    "status": "ERROR",
                    "type": "exec_result",
                    "error": error_msg,
                    "output": output
                })
            else:
                self.send_ok({
                    "type": "exec_result",
                    "output": output if output else "OK"
                })
        except Exception as e:
            self.send_error("code execution failed: " + str(e))
    
    # ========== 系统操作 ==========
    def cmd_reboot(self, params):
        """重启设备"""
        try:
            if not machine:
                self.send_error("machine module not available")
                return
            
            self.send_ok({"msg": "rebooting in 2 seconds..."})
            time.sleep(2)
            machine.reset()
        except Exception as e:
            self.send_error("reboot failed: " + str(e))
    
    def cmd_gc_collect(self, params):
        """触发垃圾回收"""
        try:
            if not gc:
                self.send_error("gc module not available")
                return
            
            before = gc.mem_free()
            gc.collect()
            after = gc.mem_free()
            
            self.send_ok({
                "type": "gc_collect",
                "freed": after - before,
                "mem_free": after
            })
        except Exception as e:
            self.send_error("gc collect failed: " + str(e))
    
    # ========== 命令分发 ==========
    def handle_command(self, cmd):
        """处理命令"""
        if not isinstance(cmd, dict):
            self.send_error("invalid command format")
            return
        
        cmd_type = cmd.get('cmd') or cmd.get('type')
        if not cmd_type:
            self.send_error("missing 'cmd' or 'type' field")
            return
        
        cmd_type = cmd_type.upper()
        
        # 命令映射表
        handlers = {
            'INFO': self.cmd_device_info,
            'DEVICE_INFO': self.cmd_device_info,
            
            'LS': self.cmd_list_files,
            'LIST_FILES': self.cmd_list_files,
            
            'CAT': self.cmd_read_file,
            'READ_FILE': self.cmd_read_file,
            
            'WRITE': self.cmd_write_file,
            'WRITE_FILE': self.cmd_write_file,
            
            'RM': self.cmd_delete_file,
            'DELETE_FILE': self.cmd_delete_file,
            
            'WIFI_SCAN': self.cmd_wifi_scan,
            'WIFI_STATUS': self.cmd_wifi_status,
            
            'EXEC': self.cmd_exec_code,
            'EXEC_CODE': self.cmd_exec_code,
            
            'REBOOT': self.cmd_reboot,
            'GC': self.cmd_gc_collect,
        }
        
        handler = handlers.get(cmd_type)
        if handler:
            handler(cmd)
        else:
            self.send_error("unknown command: " + cmd_type)
    
    def process_line(self, line):
        """处理一行输入"""
        line = line.strip()
        if not line:
            return
        
        # 只处理 JSON 格式的命令
        if line.startswith('{') and line.endswith('}'):
            try:
                cmd = json.loads(line)
                self.handle_command(cmd)
            except ValueError as e:
                self.send_error("JSON parse error: " + str(e))
            except Exception as e:
                self.send_error("command processing error: " + str(e))
    
    def listen(self, timeout_ms=50):
        """
        监听串口输入（非阻塞）
        
        Args:
            timeout_ms: 轮询超时（毫秒）
        
        Returns:
            bool: 是否处理了命令
        """
        try:
            # 使用 uselect.poll 非阻塞读取
            try:
                import uselect
                poll = uselect.poll()
                poll.register(sys.stdin, uselect.POLLIN)
                events = poll.poll(timeout_ms)
                
                if events:
                    char = sys.stdin.read(1)
                    if char:
                        self.buffer += char
                        if char == '\n':
                            line = self.buffer
                            self.buffer = ""
                            self.process_line(line)
                            return True
            except ImportError:
                # 回退到简单读取
                if hasattr(sys.stdin, 'read'):
                    char = sys.stdin.read(1)
                    if char:
                        self.buffer += char
                        if char == '\n':
                            line = self.buffer
                            self.buffer = ""
                            self.process_line(line)
                            return True
        except Exception:
            pass
        
        return False


# ========== 全局实例和便捷函数 ==========
_helper_instance = None

def get_instance():
    """获取全局 IDEHelper 实例"""
    global _helper_instance
    if _helper_instance is None:
        _helper_instance = IDEHelper()
    return _helper_instance

def listen(timeout_ms=50):
    """便捷函数：监听一次串口输入"""
    return get_instance().listen(timeout_ms)

def start_background():
    """
    启动后台监听线程（可选）
    
    注意：此功能需要设备支持 _thread 模块
    如果设备不支持多线程，可以在主循环中调用 listen()
    
    Returns:
        bool: 是否成功启动
    """
    try:
        # 运行时动态导入 _thread，避免编译时依赖
        import sys
        if '_thread' not in sys.modules:
            try:
                __import__('_thread')
            except ImportError:
                # 设备不支持线程，返回 False
                return False
        
        _thread = sys.modules['_thread']
        
        def listener_thread():
            helper = get_instance()
            while True:
                helper.listen(timeout_ms=100)
                time.sleep(0.01)
        
        _thread.start_new_thread(listener_thread, ())
        return True
    except ImportError:
        return False
    except Exception:
        return False
