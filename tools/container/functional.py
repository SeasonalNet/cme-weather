import io,json,os,socket,subprocess,sys,threading,time,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree
from PIL import Image
calls=[]
class Fixture(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  calls.append(self.path)
  base=f'http://127.0.0.1:{self.server.server_port}'
  if self.path=='/us/20794':data={'places':[{'latitude':'39','longitude':'-76','place name':'Jessup','state abbreviation':'MD'}]}
  elif self.path.startswith('/points/'):data={'properties':{'observationStations':base+'/stations','forecast':base+'/forecast'}}
  elif self.path=='/stations':data={'features':[{'properties':{'stationIdentifier':'MOCK'}}]}
  elif self.path=='/stations/MOCK/observations/latest':data={'properties':{'temperature':{'value':20},'textDescription':'Light Rain','relativeHumidity':{'value':55},'windSpeed':{'value':12,'unitCode':'wmoUnit:km_h-1'},'timestamp':'2026-10-21T12:00:00Z'}}
  elif self.path=='/forecast':data={'properties':{'periods':[{'name':'This Afternoon','temperature':72,'temperatureUnit':'F','isDaytime':True,'shortForecast':'Showers likely','detailedForecast':'Fixture forecast'},{'name':'Tonight','temperature':61,'temperatureUnit':'F','isDaytime':False,'shortForecast':'Cloudy','detailedForecast':'Cloudy tonight'}]}}
  elif self.path.startswith('/alerts/active'):data={'features':[{'id':'warning-id','properties':{'event':'Severe Thunderstorm Warning','severity':'Severe','urgency':'Immediate','certainty':'Observed','expires':'2026-10-22T12:00:00Z','headline':'Fixture warning'}}]}
  elif self.path=='/alerts/warning-id':data={'properties':{'event':'Severe Thunderstorm Warning','severity':'Severe','urgency':'Immediate','certainty':'Observed','effective':'2026-10-21T00:00:00Z','expires':'2026-10-22T12:00:00Z','headline':'Fixture warning','description':'Fixture description','instruction':'Move indoors.'}}
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
mock=ThreadingHTTPServer(('127.0.0.1',0),Fixture);threading.Thread(target=mock.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{mock.server_port}'
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
Path('/tmp/weather.yaml').write_text(f'nws:\n  base_url: {base}\nzippopotam:\n  base_url: {base}\nicons:\n  ws_icon_dir: /app/icons/ws4kp18\n')
env={**os.environ,'CME_WEATHER_CONFIG':'/tmp/weather.yaml'}
p=subprocess.Popen([sys.executable,'-m','gunicorn','--bind',f'127.0.0.1:{port}','--workers','1','--threads','4','--timeout','15','--worker-tmp-dir','/tmp','wsgi:app'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def get(path):
 with urllib.request.urlopen(f'http://127.0.0.1:{port}/cme/services'+path,timeout=5) as r:
  assert r.status==200;return r.read()
try:
 for attempt in range(50):
  try:get('/healthz');break
  except OSError:time.sleep(.1)
 else:raise AssertionError('Gunicorn did not become healthy')
 for path,expected in [('/weather/show?q=20794','Light Rain'),('/weather/current?q=20794','55'),('/weather/forecast?q=20794&mode=today','Showers likely'),('/weather/alerts?q=20794','Severe Thunderstorm Warning'),('/weather/alert?q=20794&id=warning-id','Move indoors.')]:
  payload=get(path);ElementTree.fromstring(payload);assert expected in payload.decode(),(path,payload)
 for index in [0,6,9]:
  payload=get(f'/weather/icon.png?i={index}');img=Image.open(io.BytesIO(payload));assert img.size==(18,18);img.load()
 assert any(x.startswith('/points/') for x in calls);assert '/stations/MOCK/observations/latest' in calls;assert '/forecast' in calls;assert '/alerts/warning-id' in calls
 count=len(calls);get('/weather/current?q=20794');assert len(calls)==count,'cache missed'
 print('PASS CME actual Gunicorn HTTP, ZIP->NWS points/station/observation/forecast/alerts, valid Cisco XML, caching, file-backed and Pillow-generated PNG decoding')
finally:
 p.terminate();_,err=p.communicate(timeout=10);mock.shutdown()
 if p.returncode not in [0,-15]:print(err.decode());raise AssertionError(p.returncode)
