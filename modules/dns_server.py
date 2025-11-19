# TansuoDou 2.0 - DNS Server for Captive Portal
# Based on: https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal

import socket
import time

class DNSServer:
    """Simple DNS server that returns the AP IP for all queries"""
    
    def __init__(self, ip):
        self.ip = ip
        self.sock = None
        
    def start(self):
        """Start DNS server on port 53"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', 53))
            self.sock.setblocking(False)
            print("[OK] DNS服务器已启动")
            print("   监听端口: 53")
            print("   返回IP: " + self.ip)
            return True
        except Exception as e:
            print("[ERROR] DNS服务器启动失败: " + str(e))
            return False
    
    def process(self):
        """Process DNS queries (call this in a loop)"""
        try:
            data, addr = self.sock.recvfrom(512)
            if data:
                # Parse DNS query
                domain = self.parse_dns_query(data)
                if domain:
                    print("[DNS] 查询: " + domain + " -> " + self.ip)
                    # Build DNS response
                    response = self.build_dns_response(data, self.ip)
                    self.sock.sendto(response, addr)
        except OSError:
            # No data available (non-blocking)
            pass
        except Exception as e:
            print("[ERROR] DNS处理错误: " + str(e))
    
    def parse_dns_query(self, data):
        """Extract domain from DNS query"""
        try:
            # Skip DNS header (12 bytes)
            i = 12
            domain_parts = []
            
            while i < len(data):
                length = data[i]
                if length == 0:
                    break
                i += 1
                domain_parts.append(data[i:i+length].decode('utf-8', 'ignore'))
                i += length
            
            return '.'.join(domain_parts)
        except:
            return None
    
    def build_dns_response(self, query, ip):
        """Build DNS response packet"""
        # DNS response header
        response = bytearray(query[:2])  # Transaction ID
        response += b'\x81\x80'  # Flags: Response, No error
        response += query[4:6]   # Questions count
        response += query[4:6]   # Answer RRs
        response += b'\x00\x00'  # Authority RRs
        response += b'\x00\x00'  # Additional RRs
        
        # Copy question section
        response += query[12:]
        
        # Answer section
        response += b'\xc0\x0c'  # Pointer to domain name
        response += b'\x00\x01'  # Type A
        response += b'\x00\x01'  # Class IN
        response += b'\x00\x00\x00\x3c'  # TTL (60 seconds)
        response += b'\x00\x04'  # Data length
        
        # IP address (convert string to bytes)
        ip_parts = ip.split('.')
        for part in ip_parts:
            response += bytes([int(part)])
        
        return bytes(response)
    
    def stop(self):
        """Stop DNS server"""
        if self.sock:
            try:
                self.sock.close()
                print("[OK] DNS服务器已停止")
            except:
                pass
