"""Validate a static STRIKE release at a subpath, including offline operation."""
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from threading import Thread
import io, json, math, os, shutil, struct, tempfile, wave
import jsonschema
from PIL import Image
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parents[1]
meta = json.loads((APP/'boiler-room.json').read_text())
manifest = json.loads((APP/'manifest.webmanifest').read_text())
jsonschema.Draft202012Validator(json.loads((APP/'boiler-room.schema.json').read_text()), format_checker=jsonschema.FormatChecker()).validate(meta)
assert not meta['created'] or meta['created'] <= meta['updated']
assert set('id name short_name description lang categories start_url scope display background_color theme_color icons'.split()) <= manifest.keys()
assert meta['offline'] == {'mode':'full','limitations':[]}
assert 'version' not in manifest and 'files' not in manifest
for name in meta['files'] + [meta['changelog']]:
    assert (APP/name).is_file(), name
assert len(set(meta['files'])) == len(meta['files'])
for icon in manifest['icons']:
    with Image.open(APP/icon['src']) as image:
        assert f'{image.width}x{image.height}' == icon['sizes']
        assert image.format == 'PNG'
print('PASS: Schema with date checking; manifest and icon sizes; local resource list', flush=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

with tempfile.TemporaryDirectory() as root, sync_playwright() as pw:
    root = Path(root)
    target = root/'apps'/'strike'; target.parent.mkdir(); shutil.copytree(APP,target)
    (root/'workspace.html').write_text('<iframe src="/apps/strike/" width="1200" height="850" allow="autoplay"></iframe>')
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(root)))
    Thread(target=server.serve_forever,daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}/'; base = urljoin(origin,'apps/strike/')
    urls = [urljoin(base, name) for name in meta['files']]
    assert len(urls) == len(set(urls)) and all(url.startswith(base) for url in urls)
    chromium = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
    browser = pw.chromium.launch(executable_path=chromium, args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    context = browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page = context.new_page(); page.set_default_timeout(15000)
    errors=[]; page.on('pageerror',lambda err:errors.append(str(err)))
    try:
        for url in urls+[urljoin(base,meta['changelog'])]:
            res=context.request.get(url); assert res.ok, url
            if url.endswith('.webmanifest'): assert 'json' in res.headers['content-type']
            if url.endswith('sw.js'): assert 'javascript' in res.headers['content-type']
        page.goto(base); page.wait_for_function('navigator.serviceWorker.controller !== null'); page.wait_for_function("document.getElementById('pwaStatus').textContent.includes('Offline bereit')")
        cached=page.evaluate('''async () => {const name=(await caches.keys()).find(n=>n.startsWith('strike-shell:')&&n.endsWith(':2'));return (await (await caches.open(name)).keys()).map(r=>r.url)}''')
        assert sorted(cached)==sorted(urls), (cached,urls)
        assert page.locator('.pad').count()==16 and page.locator('.step').count()==256
        cdp=context.new_cdp_session(page)
        try:
            result=cdp.send('Page.getInstallabilityErrors')
        except Exception as exc:
            print('NOT TESTED: CDP installability diagnostic unavailable:',exc,flush=True)
        else:
            assert not result['installabilityErrors'], result
            print('PASS: Chromium installability diagnostic reports no errors',flush=True)
        iframe_page=context.new_page(); iframe_page.goto(urljoin(origin,'workspace.html'))
        frame=iframe_page.frame_locator('iframe'); frame.locator('.pad').first.click(); frame.locator('#status').get_by_text('Audio aktiv').wait_for()
        iframe_page.close()
        print('PASS: all HTTP resources, service-worker scope, complete cache, same-origin iframe audio',flush=True)
        context.set_offline(True)
        page.reload(wait_until='load'); page.wait_for_function('navigator.serviceWorker.controller !== null')
        page.goto(base+'index.html?offline=1'); assert page.locator('.pad').count()==16
        for name in ['manifest.webmanifest','boiler-room.json','sw.js','icons/icon-192.png','icons/icon-512.png','icons/icon-maskable-512.png']:
            assert page.evaluate('async name => (await fetch(name)).ok',name), name
        page.locator('.pad').first.click(); page.locator('#status').get_by_text('Audio aktiv').wait_for()
        page.locator('#play').click(); page.wait_for_function('playing === true'); page.wait_for_timeout(300); page.locator('#stop').click(); assert page.evaluate('!playing')
        page.locator('#steps').select_option('32'); assert page.locator('.step').count()==512
        page.locator('#steps').select_option('16')
        # Import an original synthetic PCM test signal, with no external dependency.
        buf=io.BytesIO()
        with wave.open(buf,'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(44100)
            wav.writeframes(b''.join(struct.pack('<h',int(15000*math.sin(2*math.pi*330*i/44100)*math.exp(-i/1800))) for i in range(4410)))
        page.locator('#sampleFile').set_input_files({'name':'offline-test.wav','mimeType':'audio/wav','buffer':buf.getvalue()})
        page.wait_for_function("state.pads[0].sampleName === 'offline-test.wav'")
        page.locator('.pad').first.click(); page.locator('#status').get_by_text('Audio aktiv').wait_for()
        with page.expect_download() as project_info: page.locator('#saveProject').click()
        project=project_info.value.path(); saved=json.loads(project.read_text()); assert saved['version']==1 and saved['pads'][0]['sample']['length']==4410
        page.locator('#padName').fill('Changed'); page.locator('#projectFile').set_input_files(str(project)); page.wait_for_function("state.pads[0].name === 'offline-test'")
        page.locator('#demo').click()
        with page.expect_download() as wav_info: page.locator('#exportWav').click()
        with wave.open(str(wav_info.value.path()),'rb') as wav:
            assert wav.getnchannels()==2 and wav.getframerate()==44100 and wav.getsampwidth()==2
            pcm=wav.readframes(wav.getnframes()); assert max(abs(v[0]) for v in struct.iter_unpack('<h',pcm))>0
        assert not errors,errors
        print('PASS: offline reload at base and entry URL; audio, playback, 32 steps, sample import, project round trip, non-silent WAV export',flush=True)
        for size in [(1440,1000),(390,844)]:
            page.set_viewport_size({'width':size[0],'height':size[1]}); page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),size
        print('PASS: desktop and mobile viewport without horizontal document overflow',flush=True)
    finally:
        browser.close(); server.shutdown()
