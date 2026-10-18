"""Ejecuta la práctica con Docker y guarda sus resultados reales."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.request

BASE = Path(__file__).resolve().parent
EVIDENCIAS = BASE / 'evidencias'
EVIDENCIAS.mkdir(exist_ok=True)
log = []

def ejecutar(args, cwd=None):
    orden = '$ ' + ' '.join(args)
    print(orden, flush=True)
    log.append(orden)
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.append(result.stdout.rstrip())
    print(result.stdout, flush=True)
    (EVIDENCIAS / 'comandos.txt').write_text('\n'.join(log)+'\n', encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Falló el comando: {args[0]}')
    return result.stdout

inicio = time.perf_counter()
ejecutar(['docker','--version'])
for nombre in ['nginx1','nginx2']:
    existe = subprocess.run(['docker','container','inspect',nombre], capture_output=True)
    if existe.returncode == 0:
        raise RuntimeError(f'Ya existe {nombre}. Usa un entorno sin contenedores con estos nombres.')

ejecutar(['docker','run','-d','--name','nginx1','-p','8089:80','nginx'])
ejecutar(['docker','run','-d','--name','nginx2','-p','8090:80','nginx'])
with tempfile.TemporaryDirectory(prefix='practica-nginx-') as carpeta:
    for numero in [1,2]:
        nombre = f'nginx{numero}'
        archivo = f'index{numero}.html'
        ejecutar(['docker','cp',f'{nombre}:/usr/share/nginx/html/index.html',f'./{archivo}'], cwd=carpeta)
        original = Path(carpeta)/archivo
        assert 'Welcome to nginx!' in original.read_text(encoding='utf-8')
        log.append(f'# Editar {archivo} con Vim y guardar el contenido personalizado.')
        ejecutar(['vim','-Nu','NONE','-n','-es',archivo,'-c','%delete _','-c',f'0read {BASE/archivo}','-c','wq'],cwd=carpeta)
        assert original.read_bytes() == (BASE/archivo).read_bytes()
        ejecutar(['docker','cp',archivo,f'{nombre}:/usr/share/nginx/html/index.html'],cwd=carpeta)

datos=[]
for numero,puerto in [(1,8089),(2,8090)]:
    url=f'http://localhost:{puerto}'
    for intento in range(20):
        try:
            with urllib.request.urlopen(url,timeout=5) as response:
                cuerpo=response.read()
                status=response.status
                server=response.headers.get('Server')
            break
        except Exception:
            if intento==19: raise
            time.sleep(1)
    assert status==200
    assert cuerpo==(BASE/f'index{numero}.html').read_bytes()
    datos.append({'contenedor':f'nginx{numero}','url':url,'estado_http':status,'servidor':server,'sha256':hashlib.sha256(cuerpo).hexdigest()})
    ejecutar(['curl','--fail','--silent','--show-error','--head',url])

estado=ejecutar(['docker','ps','--filter','name=nginx','--format','table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'])
(EVIDENCIAS/'contenedores.txt').write_text(estado,encoding='utf-8')
inspeccion=json.loads(ejecutar(['docker','inspect','nginx1','nginx2']))
for numero,puerto in [(1,8089),(2,8090)]:
    info=next(c for c in inspeccion if c['Name']==f'/nginx{numero}')
    assert info['State']['Running']
    assert any(p['HostPort']==str(puerto) for p in info['NetworkSettings']['Ports']['80/tcp'])
imagen=json.loads(ejecutar(['docker','image','inspect','nginx','--format','{{json .RepoDigests}}']))
verificacion={'servidores':datos,'imagen':imagen,'duracion_ejecucion_segundos':round(time.perf_counter()-inicio,2),'entorno':'Ubuntu 24.04 en GitHub Actions' if os.environ.get('GITHUB_ACTIONS') else 'Equipo con Docker','ejecucion':os.environ.get('GITHUB_RUN_ID')}
(EVIDENCIAS/'verificacion.json').write_text(json.dumps(verificacion,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Dos contenedores activos, puertos correctos y páginas personalizadas verificadas.',flush=True)
