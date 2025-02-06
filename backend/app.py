from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import json
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

# 添加文章存储目录
ARTICLES_DIR = "articles"
if not os.path.exists(ARTICLES_DIR):
    os.makedirs(ARTICLES_DIR)

# 修改 text_to_speech 函数
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = get_safe_filename(text, timestamp)
        
        # 保存文章内容
        article_id = timestamp
        article_data = {
            'id': article_id,
            'title': text[:30] + '...' if len(text) > 30 else text,
            'content': text,
            'audio_filename': filename,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存文章文件
        article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
        with open(article_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False)

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
                'filename': filename,
                'article_id': article_id
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 添加获取文章列表的接口
@app.route('/api/articles', methods=['GET'])
def get_articles():
    try:
        articles = []
        for filename in os.listdir(ARTICLES_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(ARTICLES_DIR, filename), 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    articles.append(article)
        
        # 按创建时间倒序排序
        articles.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify(articles)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 添加获取单个文章的接口
@app.route('/api/articles/<article_id>', methods=['GET'])
def get_article(article_id):
    try:
        article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
        if not os.path.exists(article_path):
            return jsonify({'error': 'Article not found'}), 404
            
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
            return jsonify(article)
    
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