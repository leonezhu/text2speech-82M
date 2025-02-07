from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import json
from datetime import datetime
import re
from models import Sentence, Article

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
        filepath = os.path.join(AUDIO_DIR, filename)

        # 生成语音并记录每个句子的时间戳
        all_audio = []
        sentences = []
        current_time = 0
        generator = pipeline(text, voice='af_heart', speed=1)
        max_retries = 3  # 最大重试次数
        
        print(f"[DEBUG] 原始输入文本: {text}")
        # 简化文本处理，先处理所有换行符，再进行句子分割
        text = text.strip().replace('\n\n+', ' ').replace('\n', ' ')
        print(f"[DEBUG] 处理换行符后的文本: {text}")

        # 替换所有连续的空格为一个空格
        text = re.sub(r'\s+', ' ', text)
        print(f"[DEBUG] 处理空格后的文本: {text}")

        # 改进句子分割的正则表达式
        # 匹配句号/问号/感叹号，后面可能跟着空格
        sentence_parts = re.split(r'([。！？.!?][\s]*)', text)
        text_sentences = []
        
        print(f"[DEBUG] 分割后的句子部分: {sentence_parts}")
        # 组合句子和分隔符，处理最后一个可能没有标点的句子
        current_sentence = ''
        for i in range(len(sentence_parts)):
            part = sentence_parts[i].strip()
            if not part:
                continue
                
            if re.search(r'[。！？.!?][\s]*$', part):
                # 这部分是标点符号（可能带空格）
                current_sentence += part
                if current_sentence.strip():
                    text_sentences.append(current_sentence.strip())
                    print(f"[DEBUG] 添加完整句子: {current_sentence.strip()}")
                current_sentence = ''
            else:
                # 这部分是句子内容
                current_sentence += part
                print(f"[DEBUG] 当前处理的句子部分: {current_sentence}")

        # 处理最后一个可能没有标点的句子
        if current_sentence.strip():
            text_sentences.append(current_sentence.strip())
        
        print(f"[DEBUG] 最终分割的句子列表: {text_sentences}")
        # 生成每个句子的音频并记录时间戳
        for i, sentence in enumerate(text_sentences):
            retry_count = 0
            while retry_count < max_retries:
                try:
                    print(f"[DEBUG] 正在处理第{i+1}个句子: {sentence} (尝试 {retry_count + 1}/{max_retries})")
                    # 尝试从生成器获取下一个音频片段
                    _, _, audio = next(generator)
                    duration = len(audio) / 24000  # 计算音频时长（采样率24000）
                    print(f"[DEBUG] 生成音频片段长度: {len(audio)}, 持续时间: {duration}秒")
                    sentences.append({
                        'text': sentence,
                        'start_time': current_time,
                        'end_time': current_time + duration
                    })
                    current_time += duration
                    all_audio.append(audio)
                    print(f"[DEBUG] 成功处理句子，当前总时长: {current_time}秒")
                    break  # 成功生成音频，跳出重试循环

                except StopIteration as e:
                    print(f"[ERROR] 生成器在处理第{i+1}个句子时提前结束: {str(e)}")
                    if retry_count == max_retries - 1:
                        # 如果是最后一次重试，则返回已生成的部分
                        print(f"[WARNING] 达到最大重试次数，将返回已生成的{len(all_audio)}个音频片段")
                        break
                    retry_count += 1
                    # 重新初始化生成器
                    generator = pipeline(text, voice='af_heart', speed=1)

                    print(f"[INFO] 重新初始化生成器，准备第{retry_count + 1}次重试")
                    
                except Exception as e:
                    print(f"[ERROR] 处理第{i+1}个句子时发生错误: {str(e)}")
                    if retry_count == max_retries - 1:
                        raise Exception(f"处理句子'{sentence}'时发生错误: {str(e)}")
                    retry_count += 1
                    # 重新初始化生成器
                    generator = pipeline(text, voice='af_heart', speed=1)
                    print(f"[INFO] 重新初始化生成器，准备第{retry_count + 1}次重试")

        # 将所有音频段拼接成一个完整的音频
        if all_audio:
            combined_audio = np.concatenate(all_audio)
            # 保存合并后的音频文件
            sf.write(filepath, combined_audio, 24000)

            # 保存文章内容
            article_id = timestamp
            article_data = {
                'id': article_id,
                'title': text[:30] + '...' if len(text) > 30 else text,
                'content': text,
                'audio_filename': filename,
                'created_at': datetime.now().isoformat(),
                'sentences': sentences
            }
            
            # 保存文章文件
            article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
            with open(article_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False)

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