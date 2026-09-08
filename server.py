"""Local mars USB status dashboard and one-time, in-memory SIM PIN inbox."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,json,math,os,subprocess,threading,time

ROOT=Path(__file__).resolve().parent
SERIAL=''
EDL_CHIP_ID=''

def configure(path):
    global SERIAL,EDL_CHIP_ID
    config=json.loads(Path(path).read_text())
    serial=config.get('serial','')
    chip=config.get('edl_chip_id','')
    if not isinstance(serial,str) or not serial.strip():
        raise ValueError('配置 serial 必须是非空字符串')
    if not isinstance(chip,str) or not chip or any(c not in '0123456789abcdefABCDEF' for c in chip):
        raise ValueError('配置 edl_chip_id 必须是非空十六进制字符串')
    SERIAL=serial.strip();EDL_CHIP_ID=chip.upper()
def scan_usb(base=Path('/sys/bus/usb/devices')):
    devices=[]
    for p in base.iterdir():
        try:
            if not (p/'idVendor').exists():continue
            def read(name):return (p/name).read_text().strip() if (p/name).exists() else ''
            vendor,product=read('idVendor'),read('idProduct')
            desc,serial=read('product'),read('serial')
            if (vendor,product)==('05c6','9008') or (bool(SERIAL) and serial==SERIAL) or 'mars' in (desc+' '+serial).lower():
                bus,number=int(read('busnum')),int(read('devnum'))
                node=f'/dev/bus/usb/{bus:03}/{number:03}'
                devices.append({'vid':vendor,'pid':product,'product':desc,'serial':serial,'path':node,'readable':os.access(node,os.R_OK),'writable':os.access(node,os.W_OK),'target_match':bool(SERIAL) and serial==SERIAL,'expected_edl':(vendor,product)==('05c6','9008') and bool(EDL_CHIP_ID) and '_SN:' in desc.upper() and desc.upper().split('_SN:')[-1].strip()==EDL_CHIP_ID})
        except FileNotFoundError:continue # device disconnected during enumeration
    return devices

def command_devices(tool):
    try:
        r=subprocess.run([tool,'devices'],capture_output=True,text=True,timeout=1.5)
        return {'ok':r.returncode==0,'lines':r.stdout.splitlines()}
    except (OSError,subprocess.TimeoutExpired):return {'ok':False,'lines':[]}

def classify(devices,adb,fastboot):
    edl=[d for d in devices if (d['vid'],d['pid'])==('05c6','9008')]
    if edl:
        if len(edl)==1 and edl[0]['expected_edl']:return 'edl'
        return 'edl_unknown'
    for line in adb['lines']:
        parts=line.split()
        if len(parts)>=2 and parts[0]==SERIAL:
            return 'adb' if parts[1]=='device' else 'adb_unauthorized' if parts[1]=='unauthorized' else 'adb_offline'
    if any(line.split()[:1]==[SERIAL] for line in fastboot['lines']):return 'fastboot'
    if any('mars' in (d['product']+' '+d['serial']).lower() and d['pid']=='0104' for d in devices):return 'ram_linux'
    if devices:return 'usb'
    return 'disconnected' if adb['ok'] and fastboot['ok'] else 'unknown'

class Monitor:
    def __init__(self):
        self.lock=threading.Lock();self.value={'state':'loading','events':[],'checked_at':None};self.events=[];self.last=None
    def poll(self):
        while True:
            started=time.monotonic()
            try:
                devices=scan_usb()
                if any(d['pid']=='9008' and d['vid']=='05c6' for d in devices):
                    adb=fastboot={'ok':True,'lines':[]}
                else:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        a=pool.submit(command_devices,'adb');f=pool.submit(command_devices,'fastboot')
                        adb,fastboot=a.result(),f.result()
                state=classify(devices,adb,fastboot)
                error=None
            except Exception:
                state='unknown';devices=[];error='检测服务暂时无法读取设备状态'
            now=datetime.now().astimezone().isoformat(timespec='seconds')
            with self.lock:
                if state!=self.last:
                    self.events.insert(0,{'state':state,'time':now});self.events=self.events[:12];self.last=state
                self.value={'state':state,'devices':devices,'checked_at':now,'events':list(self.events),'error':error,'poll_seconds':2}
            time.sleep(max(.1,2-(time.monotonic()-started)))
    def snapshot(self):
        with self.lock:return dict(self.value)

monitor=Monitor()

class PinInbox:
    """Hold one PIN in memory for a short time and erase it after one read."""
    def __init__(self,ttl_seconds=300,clock=time.monotonic):
        self.lock=threading.Lock();self.ttl=ttl_seconds;self.clock=clock;self.value=None;self.expires_at=0
    @staticmethod
    def validate(value):
        return isinstance(value,str) and 4<=len(value)<=8 and value.isascii() and value.isdigit()
    def _clear_locked(self):
        if self.value is not None:
            for i in range(len(self.value)):self.value[i]=0
        self.value=None;self.expires_at=0
    def put(self,value):
        if not self.validate(value):raise ValueError('PIN 必须是 4–8 位数字')
        with self.lock:
            self._clear_locked();self.value=bytearray(value,'ascii');self.expires_at=self.clock()+self.ttl
    def status(self):
        with self.lock:
            remaining=self.expires_at-self.clock()
            if self.value is None or remaining<=0:
                self._clear_locked();return {'pending':False,'expires_in':0}
            return {'pending':True,'expires_in':math.ceil(remaining)}
    def take(self):
        with self.lock:
            if self.value is None or self.expires_at<=self.clock():
                self._clear_locked();return None
            result=bytes(self.value);self._clear_locked();return result

pin_inbox=PinInbox()

class Handler(BaseHTTPRequestHandler):
    def allowed(self):
        host=self.headers.get('Host','').split(':')[0]
        return self.client_address[0] in {'127.0.0.1','::1'} and host in {'127.0.0.1','localhost'}
    def send_bytes(self,status,data,mime):
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'self'; form-action 'self'")
        self.end_headers();self.wfile.write(data)
    def send_json(self,status,value):
        self.send_bytes(status,json.dumps(value,ensure_ascii=False).encode(),'application/json; charset=utf-8')
    def do_GET(self):
        if not self.allowed():self.send_error(403);return
        path=self.path.split('?',1)[0]
        if path=='/api/status':data=json.dumps(monitor.snapshot(),ensure_ascii=False).encode();mime='application/json; charset=utf-8'
        elif path=='/api/pin/status':data=json.dumps(pin_inbox.status(),ensure_ascii=False).encode();mime='application/json; charset=utf-8'
        elif path in {'/','/app.js','/style.css'}:
            file=ROOT/({'/':'index.html'}.get(path,path[1:]));data=file.read_bytes()
            mime='text/html; charset=utf-8' if path=='/' else 'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8'
        else:self.send_error(404);return
        self.send_bytes(200,data,mime)
    def do_POST(self):
        if not self.allowed():self.send_error(403);return
        path=self.path.split('?',1)[0]
        if path=='/api/pin/consume':
            if self.headers.get('X-Mars-Pin-Consumer')!='codex-local-v1':self.send_error(403);return
            value=pin_inbox.take()
            if value is None:self.send_json(404,{'ok':False,'error':'没有待使用的 PIN'});return
            self.send_bytes(200,value,'application/octet-stream');return
        if path!='/api/pin':self.send_error(404);return
        try:
            if self.headers.get_content_type()!='application/json':raise ValueError('只接受 JSON 请求')
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>128:raise ValueError('请求长度无效')
            payload=json.loads(self.rfile.read(length))
            pin_inbox.put(payload.get('pin') if isinstance(payload,dict) else None)
        except (ValueError,TypeError,json.JSONDecodeError) as error:
            self.send_json(400,{'ok':False,'error':str(error)});return
        self.send_json(202,{'ok':True,**pin_inbox.status()})
    def log_message(self,*args):pass

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Local phone USB status dashboard')
    p.add_argument('--port',type=int,default=8787)
    p.add_argument('--config',type=Path,default=ROOT/'config.local.json')
    a=p.parse_args()
    try:configure(a.config)
    except (OSError,ValueError,TypeError,AttributeError) as error:p.error(f'无法加载本地设备配置：{error}')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    threading.Thread(target=monitor.poll,daemon=True).start()
    print(f'Mars device status: http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()
