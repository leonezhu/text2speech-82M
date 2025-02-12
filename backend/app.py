from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import json
from datetime import datetime
import re
import logging
from models import Sentence, Article

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 音频文件保存目录
AUDIO_DIR = "audio_files"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# 语音配置
LANG_CONFIG = {
    'zh': {
        'code': 'z',
        'voice': 'zm_yunxia'
    },
    'en': {
        'code': 'a',
        'voice': 'af_heart'
    }
}

# 初始化 Kokoro pipeline 字典
pipelines = {}
for lang, config in LANG_CONFIG.items():
    pipelines[lang] = KPipeline(lang_code=config['code'])

def get_safe_filename(text, timestamp, language):
    # 获取第一句话（以。！？.!?；;为分隔）
    first_sentence = re.split(r'[。！？.!?；;]', text.strip())[0]
    
    # 如果第一句话太长，截取前20个字符
    if len(first_sentence) > 20:
        first_sentence = first_sentence[:20] + '...'
    
    # 移除不安全的文件名字符
    safe_name = re.sub(r'[\\/:*?"<>|\s]', '_', first_sentence)
    
    # 组合文件名：第一句话_语言_时间戳.wav
    return f'{safe_name}_{language}_{timestamp}.wav'

# 添加文章存储目录
ARTICLES_DIR = "articles"
if not os.path.exists(ARTICLES_DIR):
    os.makedirs(ARTICLES_DIR)

# 添加语言检测函数
def is_chinese(char):
    return '\u4e00' <= char <= '\u9fff'

def split_by_language(text):
    segments = []
    current_type = None  # 'zh' or 'en'
    current_text = ''
    current_sentence = ''
    
    for char in text:
        current_sentence += char
        
        # 如果是空格或标点，添加到当前文本但不改变语言类型
        if char.isspace() or char in '。！？.!?；;,"':
            if current_text:
                current_text += char
            continue
            
        is_zh = is_chinese(char)
        char_type = 'zh' if is_zh else 'en'
        
        if current_type is None:
            current_type = char_type
            current_text = char
        elif char_type == current_type:
            current_text += char
        else:
            if current_text.strip():
                # 保存当前语言段落及其在原文中的完整上下文
                segments.append({
                    'type': current_type,
                    'text': current_text.strip(),
                    'full_context': current_sentence.strip()
                })
            current_type = char_type
            current_text = char
    
    if current_text.strip():
        segments.append({
            'type': current_type,
            'text': current_text.strip(),
            'full_context': current_sentence.strip()
        })
    
    return segments

# 在 text_to_speech 函数中修改处理逻辑
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        logger.info("开始处理 TTS 请求")
        data = request.json
        text = data.get('text')
        languages = data.get('languages', ['zh'])
        
        logger.info(f"请求参数: languages={languages}, text_length={len(text) if text else 0}")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        article_id = timestamp
        language_versions = {}

        for lang in languages:
            if lang not in LANG_CONFIG:
                logger.warning(f"不支持的语言: {lang}")
                continue

            logger.info(f"开始处理 {lang} 语言版本")
            filename = get_safe_filename(text, timestamp, lang)
            filepath = os.path.join(AUDIO_DIR, filename)

            all_audio = []
            sentences = []
            current_time = 0
            max_retries = 3

            # 处理文本
            text = text.strip().replace('\n\n+', '\n').replace('\n\n', '\n')
            paragraphs = text.split('\n')
            text_sentences = []

            # 分段处理文本
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue

                paragraph = re.sub(r'\s+', ' ', paragraph.strip())
                urls = re.findall(r'https?://\S+', paragraph)
                temp_paragraph = re.sub(r'https?://\S+', 'URL_PLACEHOLDER', paragraph)
                sentence_parts = re.split(r'([。！？.!?；;][\s]*)', temp_paragraph)

                current_sentence = ''
                url_index = 0
                
                # 处理每个句子
                for i in range(len(sentence_parts)):
                    part = sentence_parts[i].strip()
                    if not part:
                        continue

                    if re.search(r'[。！？.!?；;][\s]*$', part):
                        current_sentence += part
                        if current_sentence.strip():
                            # 替换回 URL
                            while 'URL_PLACEHOLDER' in current_sentence and url_index < len(urls):
                                current_sentence = current_sentence.replace('URL_PLACEHOLDER', urls[url_index], 1)
                                url_index += 1
                            
                            # 分离中英文并保留完整上下文
                            segments = split_by_language(current_sentence.strip())
                            for segment in segments:
                                if segment['type'] == lang:  # 只处理当前语言的文本
                                    # 如果是英文版本，清理多余的标点符号
                                    if lang == 'en':
                                        # 清理多余的标点符号，包括破折号、波浪号等
                                        cleaned_text = re.sub(r'[，,。！？.!?；;—~""''\s]*(?=[，,。！？.!?；;—~""''])|[—~""'']', '', segment['text'])
                                        text_sentences.append(cleaned_text)
                                    else:
                                        text_sentences.append(segment['text'])
                                elif lang == 'en' and segment['type'] == 'zh':
                                    # 如果是英文版本且遇到中文段落，保存完整上下文中的英文部分
                                    eng_segments = split_by_language(segment['full_context'])
                                    for eng_seg in eng_segments:
                                        if eng_seg['type'] == 'en':
                                            # 清理多余的标点符号，包括破折号、波浪号等
                                            cleaned_text = re.sub(r'[，,。！？.!?；;—~""''\s]*(?=[，,。！？.!?；;—~""''])|[—~""'']', '', eng_seg['text'])
                                            text_sentences.append(cleaned_text)
                        current_sentence = ''
                    else:
                        current_sentence += part

                if current_sentence.strip():
                    while 'URL_PLACEHOLDER' in current_sentence and url_index < len(urls):
                        current_sentence = current_sentence.replace('URL_PLACEHOLDER', urls[url_index], 1)
                        url_index += 1
                    text_sentences.append(current_sentence.strip())

                text_sentences.append('\n')

            if text_sentences and text_sentences[-1] == '\n':
                text_sentences.pop()

            # 生成音频
            total_sentences = len(text_sentences)
            logger.info(f"开始生成音频，共 {total_sentences} 个句子")
            
            for i, sentence in enumerate(text_sentences):
                if sentence == '\n':
                    sentences.append({
                        'text': '\n',
                        'start_time': current_time,
                        'end_time': current_time,
                        'language': lang
                    })
                    continue

                if re.match(r'^https?://\S+$', sentence.strip()):
                    sentences.append({
                        'text': sentence,
                        'start_time': current_time,
                        'end_time': current_time,
                        'language': lang
                    })
                    continue

                start_time = datetime.now()
                logger.info(f"处理第 {i+1}/{total_sentences} 个句子: {sentence[:30]}...")
                
                retry_count = 0
                pipeline = pipelines[lang]
                while retry_count < max_retries:
                    try:
                        # 如果是英文版本，保存原始的中英混合句子作为完整上下文
                        if lang == 'en':
                            # 分离中英文
                            segments = split_by_language(sentence)
                            eng_text = ''
                            for segment in segments:
                                if segment['type'] == 'en':
                                    cleaned_text = re.sub(r'[，,。！？.!?；;]\s*(?=[，,。！？.!?；;])', '', segment['text'])
                                    eng_text += cleaned_text + ' '
                            eng_text = eng_text.strip()
                            
                            if eng_text:  # 只有当存在英文内容时才生成音频
                                # 清理多余的标点符号，包括破折号、波浪号等
                                eng_text = re.sub(r'[，,。！？.!?；;—~""''\s]*(?=[，,。！？.!?；;—~""''])|[—~""'']|[\[\]]+$', '', eng_text)
                                generator = pipeline(eng_text, voice=LANG_CONFIG[lang]['voice'], speed=1)
                                _, _, audio = next(generator)
                                duration = len(audio) / 24000
                                sentences.append({
                                    'text': sentence,  # 保存完整的中英混合句子
                                    'audio_text': eng_text,  # 保存用于生成音频的纯英文文本
                                    'start_time': current_time,
                                    'end_time': current_time + duration,
                                    'language': lang
                                })
                                current_time += duration
                                all_audio.append(audio)
                            else:  # 如果没有英文内容，仍然保存句子但不生成音频
                                sentences.append({
                                    'text': sentence,
                                    'start_time': current_time,
                                    'end_time': current_time,
                                    'language': lang
                                })
                        else:  # 中文版本保持原有逻辑
                            generator = pipeline(sentence, voice=LANG_CONFIG[lang]['voice'], speed=1)
                            _, _, audio = next(generator)
                            duration = len(audio) / 24000
                            sentences.append({
                                'text': sentence,
                                'start_time': current_time,
                                'end_time': current_time + duration,
                                'language': lang
                            })
                            current_time += duration
                            all_audio.append(audio)
                        
                        process_time = (datetime.now() - start_time).total_seconds()
                        logger.info(f"句子处理完成，音频长度: {duration:.2f}秒，处理耗时: {process_time:.2f}秒")
                        break

                    except (StopIteration, Exception) as e:
                        retry_count += 1
                        if retry_count == max_retries:
                            if isinstance(e, StopIteration):
                                logger.warning(f"句子处理中断: {sentence[:30]}...")
                                break
                            error_msg = f"处理句子'{sentence}'时发生错误: {str(e)}"
                            logger.error(error_msg)
                            raise Exception(error_msg)
                        logger.warning(f"处理失败，第 {retry_count} 次重试...")

            logger.info(f"音频生成完成，总句子数: {total_sentences}，总时长: {current_time:.2f}秒")

            # 保存音频文件
            if all_audio:
                logger.info(f"开始保存音频文件: {filepath}")
                save_start_time = datetime.now()
                combined_audio = np.concatenate(all_audio)
                sf.write(filepath, combined_audio, 24000)
                save_time = (datetime.now() - save_start_time).total_seconds()
                logger.info(f"音频文件保存成功，耗时: {save_time:.2f}秒")

                # 保存语言版本信息
                language_versions[lang] = {
                    'audio_filename': filename,
                    'sentences': sentences
                }

        # 保存文章数据
        if language_versions:
            # 使用第一个可用语言版本的第一句话作为标题
            first_lang = next(iter(language_versions))
            first_sentences = language_versions[first_lang]['sentences']
            first_text = next((s['text'] for s in first_sentences if s['text'] != '\n'), text)
            title = re.sub(r'[。！？.!?；;]$', '', first_text)

            # 使用原始文本的分句结果作为外层sentences，保持段落结构
            original_sentences = []
            for paragraph in paragraphs:
                paragraph_sentences = []
                
                if not paragraph.strip():
                    original_sentences.append({
                        'text': '\n',
                        'start_time': 0,
                        'end_time': 0,
                        'language': 'zh',
                        'is_paragraph_break': True
                    })
                    continue

                paragraph = re.sub(r'\s+', ' ', paragraph.strip())
                urls = re.findall(r'https?://\S+', paragraph)
                temp_paragraph = re.sub(r'https?://\S+', 'URL_PLACEHOLDER', paragraph)
                sentence_parts = re.split(r'([。！？.!?；;][\s]*)', temp_paragraph)

                current_sentence = ''
                url_index = 0
                
                for i in range(len(sentence_parts)):
                    part = sentence_parts[i].strip()
                    if not part:
                        continue

                    if re.search(r'[。！？.!?；;][\s]*$', part):
                        current_sentence += part
                        if current_sentence.strip():
                            # 替换回 URL
                            while 'URL_PLACEHOLDER' in current_sentence and url_index < len(urls):
                                current_sentence = current_sentence.replace('URL_PLACEHOLDER', urls[url_index], 1)
                                url_index += 1
                            
                            paragraph_sentences.append({
                                'text': current_sentence.strip(),
                                'start_time': 0,
                                'end_time': 0,
                                'language': 'zh',
                                'is_paragraph_break': False
                            })
                        current_sentence = ''
                    else:
                        current_sentence += part

                if current_sentence.strip():
                    while 'URL_PLACEHOLDER' in current_sentence and url_index < len(urls):
                        current_sentence = current_sentence.replace('URL_PLACEHOLDER', urls[url_index], 1)
                        url_index += 1
                    paragraph_sentences.append({
                        'text': current_sentence.strip(),
                        'start_time': 0,
                        'end_time': 0,
                        'language': 'zh',
                        'is_paragraph_break': False
                    })
                
                # 将段落中的所有句子添加到原始句子列表中
                original_sentences.extend(paragraph_sentences)

            article_data = {
                'id': article_id,
                'title': title,
                'content': text,
                'audio_filename': language_versions[first_lang]['audio_filename'],
                'created_at': datetime.now().isoformat(),
                'sentences': original_sentences,
                'language_versions': language_versions
            }

            article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
            with open(article_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False)

            return jsonify({
                'success': True,
                'article_id': article_id,
                'language_versions': {
                    lang: {'filename': info['audio_filename']}
                    for lang, info in language_versions.items()
                }
            })

    except Exception as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
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