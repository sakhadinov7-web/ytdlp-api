from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import os
import uuid
import threading

app = Flask(name)
DOWNLOAD_DIR = '/tmp/ytdlp'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup(filepath):
    import time
    time.sleep(300)
    if os.path.exists(filepath):
        os.remove(filepath)

def get_ydl_opts(filepath=None):
    opts = {
        # Eng kichik + audio bor format — tezroq yuklanadi
        'format': (
            'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/'
            'best[ext=mp4][height<=480]/'
            'best[ext=mp4][height<=720]/'
            'best[ext=mp4]/best'
        ),
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'retries': 3,
        'merge_output_format': 'mp4',
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
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
        return jsonify({'success': False, 'error': 'url yoq'}), 400
    try:
        opts = {
            'quiet': True,
            'skip_download': True,
            'socket_timeout': 15,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
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
        return jsonify({'success': False, 'error': 'url yoq'}), 400

    filename = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, filename + '.%(ext)s')

    try:
        opts = get_ydl_opts(outtmpl)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # Yuklangan faylni topish
        actual = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(filename):
                actual = os.path.join(DOWNLOAD_DIR, f)
                break

        if not actual or not os.path.exists(actual):
            return jsonify({'success': False, 'error': 'Fayl topilmadi'}), 500

        filesize = os.path.getsize(actual)

        if filesize < 10000:
            os.remove(actual)
            return jsonify({'success': False, 'error': 'Fayl juda kichik'}), 500

        if filesize > 52428800:
            os.remove(actual)
            return jsonify({
                'success': False,
                'error': f'Juda katta: {round(filesize/1048576,1)}MB (max 50MB)'
            }), 400

        threading.Thread(target=cleanup, args=(actual,), daemon=True).start()
        return send_file(
            actual,
            mimetype='video/mp4',
            as_attachment=True,
            download_name='video.mp4'
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if name == 'main':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
