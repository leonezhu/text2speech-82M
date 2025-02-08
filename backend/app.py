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
    # 获取第一句话（以。！？.!?；;为分隔）
    first_sentence = re.split(r'[。！？.!?；;]', text.strip())[0]
    
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
        max_retries = 3  # 最大重试次数
        
        print(f"[DEBUG] 原始输入文本: {text}")
        # 处理连续的换行符，将多个换行符替换为单个换行符
        text = text.strip().replace('\n\n+', '\n').replace('\n\n', '\n')
        print(f"[DEBUG] 处理换行符后的文本: {text}")

        # 将文本按换行符分割，保存段落信息
        paragraphs = text.split('\n')
        text_sentences = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # 处理每个段落的句子，保留中文方括号内容
            paragraph = re.sub(r'\s+', ' ', paragraph.strip())
            # 先提取并保存中文方括号内容
            chinese_texts = re.findall(r'\[(.*?)\]', paragraph)
            # 临时替换中文方括号内容，以防止被句子分割
            temp_paragraph = re.sub(r'\[(.*?)\]', 'CHINESE_TEXT_PLACEHOLDER', paragraph)
            sentence_parts = re.split(r'([。！？.!?；;][\s]*)', temp_paragraph)
            
            current_sentence = ''
            chinese_index = 0
            for i in range(len(sentence_parts)):
                part = sentence_parts[i].strip()
                if not part:
                    continue
                    
                if re.search(r'[。！？.!?；;][\s]*$', part):
                    # 这部分是标点符号（可能带空格）
                    current_sentence += part
                    if current_sentence.strip():
                        # 还原中文方括号内容
                        if 'CHINESE_TEXT_PLACEHOLDER' in current_sentence and chinese_index < len(chinese_texts):
                            current_sentence = current_sentence.replace('CHINESE_TEXT_PLACEHOLDER', f'[{chinese_texts[chinese_index]}]')
                            chinese_index += 1
                        text_sentences.append(current_sentence.strip())
                        print(f"[DEBUG] 添加完整句子: {current_sentence.strip()}")
                    current_sentence = ''
                else:
                    # 这部分是句子内容
                    current_sentence += part
                    print(f"[DEBUG] 当前处理的句子部分: {current_sentence}")
            
            # 处理段落最后一个可能没有标点的句子
            if current_sentence.strip():
                # 还原中文方括号内容
                if 'CHINESE_TEXT_PLACEHOLDER' in current_sentence and chinese_index < len(chinese_texts):
                    current_sentence = current_sentence.replace('CHINESE_TEXT_PLACEHOLDER', f'[{chinese_texts[chinese_index]}]')
                text_sentences.append(current_sentence.strip())
            
            # 在段落结束添加换行标记
            text_sentences.append('\n')
        
        # 移除最后一个多余的换行标记
        if text_sentences and text_sentences[-1] == '\n':
            text_sentences.pop()
            
        print(f"[DEBUG] 最终分割的句子列表: {text_sentences}")
        # 生成每个句子的音频并记录时间戳
        for i, sentence in enumerate(text_sentences):
            # 如果是换行符，添加一个空的时间戳记录
            if sentence == '\n':
                sentences.append({
                    'text': '\n',
                    'start_time': current_time,
                    'end_time': current_time
                })
                continue
                
            # 检查句子是否只包含中文方括号内容
            if re.match(r'^\[.*\]$', sentence.strip()):
                # 如果是纯中文注释，添加一个空的时间戳记录
                sentences.append({
                    'text': sentence,
                    'start_time': current_time,
                    'end_time': current_time
                })
                continue

            retry_count = 0
            # 为每个句子创建新的生成器实例
            generator = pipeline(sentence, voice='af_heart', speed=1)
            while retry_count < max_retries:
                try:
                    print(f"[DEBUG] 正在处理第{i+1}个句子: {sentence} (尝试 {retry_count + 1}/{max_retries})")

                    # 获取音频片段
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
                    print(f"[INFO] 重新初始化生成器，准备重试处理句子: {sentence}，第{retry_count + 1}次重试")
                    generator = pipeline(sentence, voice='af_heart', speed=1)
                   
                    
                except Exception as e:
                    print(f"[ERROR] 处理第{i+1}个句子时发生错误: {str(e)}")
                    if retry_count == max_retries - 1:
                        raise Exception(f"处理句子'{sentence}'时发生错误: {str(e)}")
                    retry_count += 1
                    # 重新初始化生成器
                    generator = pipeline(sentence, voice='af_heart', speed=1)
                    print(f"[INFO] 重新初始化生成器，准备重试处理句子: {sentence}，第{retry_count + 1}次重试")

        # 将所有音频段拼接成一个完整的音频
        if all_audio:
            combined_audio = np.concatenate(all_audio)
            # 保存合并后的音频文件
            sf.write(filepath, combined_audio, 24000)

            # 保存文章内容
            article_id = timestamp
            first_sentence = text_sentences[0].strip() if text_sentences else text  # 获取第一句
            title = re.sub(r'[。！？.!?；;]$', '', first_sentence)  # 去掉后面的标点符号
            article_data = {
                'id': article_id,
                'title': title,  # 使用优化后的标题
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