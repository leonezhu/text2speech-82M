from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from kokoro import KPipeline
import soundfile as sf
import numpy as np
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# 音频文件保存目录
AUDIO_DIR = "audio_files"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# 初始化 Kokoro pipeline
pipeline = KPipeline(lang_code='a')

def get_safe_filename(text, timestamp):
    # 获取第一句话（以。！？.!?为分隔）
    first_sentence = re.split(r'[。！？.!?]', text.strip())[0]
    
    # 如果第一句话太长，截取前20个字符
    if len(first_sentence) > 20:
        first_sentence = first_sentence[:20] + '...'
    
    # 移除不安全的文件名字符
    safe_name = re.sub(r'[\\/:*?"<>|\s]', '_', first_sentence)
    
    # 组合文件名：第一句话_时间戳.wav
    return f'{safe_name}_{timestamp}.wav'

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成文件名
        filename = get_safe_filename(text, timestamp)
        filepath = os.path.join(AUDIO_DIR, filename)

        # 生成语音并合并所有音频段
        all_audio = []
        generator = pipeline(text, voice='af_heart', speed=1)
        for _, _, audio in generator:
            all_audio.append(audio)
        
        # 将所有音频段拼接成一个完整的音频
        if all_audio:
            combined_audio = np.concatenate(all_audio)
            # 保存合并后的音频文件
            sf.write(filepath, combined_audio, 24000)

            return jsonify({
                'success': True,
                'filename': filename
            })
        else:
            return jsonify({'error': '音频生成失败'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/<filename>', methods=['GET'])
def get_audio(filename):
    try:
        return send_file(
            os.path.join(AUDIO_DIR, filename),
            mimetype='audio/wav'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True) 