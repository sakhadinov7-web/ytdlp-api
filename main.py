from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)
DOWNLOAD_DIR = '/tmp/ytdlp'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup(filepath):
    """Faylni 5 daqiqadan keyin o'chirish"""
    import time
    time.sleep(300)
    if os.path.exists(filepath):
        os.remove(filepath)

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'yt-dlp API ishlayapti!'})

@app.route('/download')
def download():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'success': False, 'error': 'url parametri yo\'q'}), 400

    # YouTube URL tekshirish
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'success': False, 'error': 'Faqat YouTube URL'}), 400

    filename = str(uuid.uuid4()) + '.mp4'
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    ydl_opts = {
        'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
        'outtmpl': filepath,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title    = info.get('title', 'video')
            duration = info.get('duration', 0)
            filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        if not os.path.exists(filepath) or filesize < 10000:
            return jsonify({'success': False, 'error': 'Yuklab bo\'lmadi'}), 500

        # 50MB dan katta bo'lsa rad etish
        if filesize > 52428800:
            os.remove(filepath)
            return jsonify({
                'success': False,
                'error': f'Video juda katta: {round(filesize/1048576,1)}MB (max 50MB)'
            }), 400

        # Faylni yuborish va 5 daqiqadan keyin o'chirish
        threading.Thread(target=cleanup, args=(filepath,), daemon=True).start()

        return send_file(
            filepath,
            mimetype='video/mp4',
            as_attachment=True,
            download_name='video.mp4'
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/info')
def info():
    """Faqat video ma'lumot — yuklamaydi"""
    url = request.args.get('url', '')
    if not url:
        return jsonify({'success': False, 'error': 'url yo\'q'}), 400

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'socket_timeout': 15,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({
            'success': True,
            'title'   : info.get('title', ''),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
