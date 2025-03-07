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

# 标题长度限制
TITLE_LENGTH_LIMIT = 30

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

# 在 text_to_speech 函数中修改处理逻辑
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        logger.info("开始处理 TTS 请求")
        data = request.json
        text = data.get('text')
        language = data.get('language', 'en')  
        
        logger.info(f"请求参数: language={language}, text_length={len(text) if text else 0}")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        if language not in LANG_CONFIG:
            return jsonify({'error': f'Unsupported language: {language}'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        article_id = timestamp

        # 预处理文本，保留换行符作为段落分隔
        text = text.strip()
        text = re.sub(r'\n{3,}', '\n\n', text)  # 将多个换行符（3个及以上）替换为两个
        text = re.sub(r'\n\n\n*', '\n\n', text)  # 确保最多只有两个连续的换行
        paragraphs = text.split('\n')
        
        # 初始化音频处理相关变量
        all_audio = []
        sentences = []
        current_time = 0
        max_retries = 3
        pipeline = pipelines[language]

        # 处理每个段落
        for paragraph in paragraphs:
            # 处理空行，保留段落分隔
            if not paragraph.strip():
                sentences.append({
                    'text': '\n',
                    'start_time': current_time,
                    'end_time': current_time,
                    'language': language
                })
                continue

            # 提取中文段落（被[]包围的文本）
            chinese_segments = re.findall(r'\[(.*?)\]', paragraph)
            # 将原文中的中文段落替换为占位符，以便后续处理
            temp_paragraph = re.sub(r'\[(.*?)\]', 'CN_PLACEHOLDER', paragraph)
            
            # 分割英文段落
            eng_parts = [part.strip() for part in temp_paragraph.split('CN_PLACEHOLDER')]
            
            # 重建段落，保持原有顺序，并对中文段落进行分句
            processed_parts = []
            for i in range(max(len(eng_parts), len(chinese_segments))):
                if i < len(eng_parts) and eng_parts[i]:
                    processed_parts.append(('en', eng_parts[i].strip()))
                if i < len(chinese_segments):
                    chinese_text = chinese_segments[i]
                    if chinese_text.strip():
                        chinese_sentences = re.split(r'([。！？；])', chinese_text)
                        current_sentence = ''
                        for j in range(0, len(chinese_sentences), 2):
                            current_sentence = chinese_sentences[j]
                            if j + 1 < len(chinese_sentences):
                                current_sentence += chinese_sentences[j + 1]
                            if current_sentence.strip():
                                processed_parts.append(('zh', current_sentence.strip()))

            # 处理每个语言段落
            for part_lang, part_text in processed_parts:
                if not part_text.strip():
                    continue

                # 只处理目标语言的文本
                if part_lang != language:
                    sentences.append({
                        'text': part_text,
                        'start_time': current_time,
                        'end_time': current_time,
                        'language': part_lang
                    })
                    continue

                # 分句处理（对于目标语言的文本）
                if part_lang == language:
                    current_sentence = part_text.strip()
                    if current_sentence:
                        # 生成音频
                        retry_count = 0
                        while retry_count < max_retries:
                            try:
                                start_time = datetime.now()
                                generator = pipeline(current_sentence, voice=LANG_CONFIG[language]['voice'], speed=1)
                                _, _, audio = next(generator)
                                duration = len(audio) / 24000

                                sentences.append({
                                    'text': current_sentence,
                                    'start_time': current_time,
                                    'end_time': current_time + duration,
                                    'language': language
                                })

                                current_time += duration
                                all_audio.append(audio)

                                process_time = (datetime.now() - start_time).total_seconds()
                                logger.info(f"句子处理完成，音频长度: {duration:.2f}秒，处理耗时: {process_time:.2f}秒")
                                break

                            except Exception as e:
                                retry_count += 1
                                if retry_count == max_retries:
                                    error_msg = f"处理句子'{current_sentence}'时发生错误: {str(e)}"
                                    logger.error(error_msg)
                                    raise Exception(error_msg)
                                logger.warning(f"处理失败，第 {retry_count} 次重试...")

            # 在每个段落结束后添加换行符
            sentences.append({
                'text': '\n',
                'start_time': current_time,
                'end_time': current_time,
                'language': language
            })

        # 保存音频文件
        if all_audio:
            filename = get_safe_filename(text, timestamp, language)
            filepath = os.path.join(AUDIO_DIR, filename)
            
            logger.info(f"开始保存音频文件: {filepath}")
            save_start_time = datetime.now()
            combined_audio = np.concatenate(all_audio)
            sf.write(filepath, combined_audio, 24000)
            save_time = (datetime.now() - save_start_time).total_seconds()
            logger.info(f"音频文件保存成功，耗时: {save_time:.2f}秒")

            # 准备文章数据
            first_text = next((s['text'] for s in sentences if s['text'] != '\n'), text)
            # 移除句子末尾的标点符号
            title = re.sub(r'[。！？.!?；;]$', '', first_text)
            # 限制标题长度，如果超过20个字符则截断并添加省略号
            if len(title) > TITLE_LENGTH_LIMIT:
                # 尝试在最后一个完整词或标点处截断
                cutoff = title[:TITLE_LENGTH_LIMIT].rfind(' ')
                if cutoff == -1:  # 如果找不到空格，就在标点符号处截断
                    cutoff = max(
                        title[:TITLE_LENGTH_LIMIT].rfind(c) for c in ',.，。!！?？;；'
                    )
                if cutoff == -1:  # 如果找不到标点符号，就直接在第20个字符处截断
                    cutoff = TITLE_LENGTH_LIMIT
                title = title[:cutoff].strip() + '...'

            # 准备语言版本数据
            language_version = {
                'audio_filename': filename,
                'sentences': sentences
            }

            # 检查是否已存在文章
            article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
            if os.path.exists(article_path):
                # 更新已存在的文章
                with open(article_path, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                article_data['language_versions'][language] = language_version
            else:
                # 创建新文章
                article_data = {
                    'id': article_id,
                    'title': title,
                    'content': text,
                    'created_at': datetime.now().isoformat(),
                    'language_versions': {language: language_version}
                }

            # 保存文章数据
            article_path = os.path.join(ARTICLES_DIR, f'{article_id}.json')
            with open(article_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False)

            return jsonify({
                'success': True,
                'article_id': article_id,
                'audio_filename': filename
            })

        return jsonify({'error': 'No audio generated'}), 400

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