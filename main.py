from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)
DOWNLOAD_DIR = '/tmp/ytdlp'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup(filepath):
    import time
    time.sleep(300)
    if os.path.exists(filepath):
        os.remove(filepath)

def get_ydl_opts(filepath=None):
    opts = {
        'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
        },
    }
    if filepath:
        opts['outtmpl'] = filepath
    else:
        opts['skip_download'] = True
    return opts

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'yt-dlp API ishlayapti!'})

@app.route('/info')
def info():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'success': False, 'error': 'url yo\'q'}), 400
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            data = ydl.extract_info(url, download=False)
        return jsonify({
            'success'  : True,
            'title'    : data.get('title', ''),
            'duration' : data.get('duration', 0),
            'thumbnail': data.get('thumbnail', ''),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download')
def download():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'success': False, 'error': 'url yo\'q'}), 400

    filename = str(uuid.uuid4()) + '.mp4'
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(filepath)) as ydl:
            ydl.download([url])

        # yt-dlp ba'zan boshqa kengaytma qo'shadi
        actual = filepath
        if not os.path.exists(filepath):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(filename.replace('.mp4', '')):
                    actual = os.path.join(DOWNLOAD_DIR, f)
                    break

        filesize = os.path.getsize(actual) if os.path.exists(actual) else 0

        if filesize < 10000:
            return jsonify({'success': False, 'error': 'Fayl yuklanmadi'}), 500

        if filesize > 52428800:
            os.remove(actual)
            return jsonify({
                'success': False,
                'error': f'Juda katta: {round(filesize/1048576,1)}MB (max 50MB)'
            }), 400

        threading.Thread(target=cleanup, args=(actual,), daemon=True).start()
        return send_file(actual, mimetype='video/mp4', as_attachment=True, download_name='video.mp4')

    except yt_dlp.utils.DownloadError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if name == 'main':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
