# backend 接口
## 5. 接口设计
### 5.1 API 接口
#### 5.1.1 文本转语音
- 请求方法：POST
- 路径：`/api/tts`
- 请求体：
  ```json
  {
    "text": "要转换的文本"
  }

- 响应
  ```json
   {
    "success": true,
    "filename": "converted_audio_timestamp.wav"
    }

#### 5.1.2 获取音频
- 请求方法：GET
- 路径： /api/audio/<filename>
- 响应：音频文件 (WAV 格式)