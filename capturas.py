"""Capturas del navegador de los dos servidores en ejecución."""
from pathlib import Path
import html
from playwright.sync_api import sync_playwright

base=Path(__file__).resolve().parent
ev=base/'evidencias'
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':800,'height':650},device_scale_factor=1)
    for numero,puerto in [(1,8089),(2,8090)]:
        response=page.goto(f'http://localhost:{puerto}',wait_until='networkidle')
        assert response.status==200
        assert page.locator('h1').inner_text()==('Instituto Tecnológico Sudamericano' if numero==1 else 'Carlos Zhuzhingo')
        page.screenshot(path=str(ev/f'nginx{numero}.png'),full_page=True)
    # This capture shows a viewer of the actual docker ps output.
    salida=(ev/'contenedores.txt').read_text(encoding='utf-8')
    page.set_content('<html lang="es"><meta charset="utf-8"><style>body{margin:0;padding:24px;background:#f3f5f7;color:#1b2d3e;font:16px Arial}h1{font-size:22px}pre{background:#17212c;color:#edf3f9;padding:20px;font:12px/1.8 monospace;white-space:pre-wrap;overflow-wrap:anywhere;border-radius:6px}p{font-size:13px}</style><h1>Contenedores Nginx en ejecución</h1><pre>$ docker ps --filter name=nginx\n'+html.escape(salida)+'</pre><p>Captura del visor de la salida real de Docker.</p></html>')
    page.locator('body').screenshot(path=str(ev/'contenedores.png'))
    browser.close()
