"""Browser instrument regression with no network, independent of service worker."""
from pathlib import Path
import io,json,math,os,shutil,struct,wave
from playwright.sync_api import sync_playwright
APP=Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
    chromium=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
    browser=pw.chromium.launch(executable_path=chromium,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True,offline=True)
    page=context.new_page();page.set_default_timeout(10000)
    errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    try:
        page.set_content((APP/'index.html').read_text())
        assert page.locator('.pad').count()==16
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
        print('PASS: offline browser document; audio, playback, 32 steps, sample import, project round trip, non-silent WAV export',flush=True)
        for size in [(1440,1000),(390,844)]:
            page.set_viewport_size({'width':size[0],'height':size[1]}); page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),size
        print('PASS: desktop and mobile viewport without horizontal document overflow',flush=True)
    finally:
        browser.close()
