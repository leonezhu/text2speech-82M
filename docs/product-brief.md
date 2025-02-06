# 文字转语音项目

## 1. 项目概述
本项目是一个基于 Web 的文字转语音应用，允许用户输入文本并将其转换为语音输出。项目采用前后端分离架构，使用现代化的技术栈实现。


## 4. 核心功能模块
### 4.1 前端模块
#### 4.1.1 文本输入组件
- 功能：接收用户输入的文本
- 位置：<mcfile name="App.jsx" path="/Users/xiong/Documents/GitHub/text2speech82m/frontend-react/src/App.jsx"></mcfile>
- 特性：
  - 响应式文本框
  - 实时输入验证
  - 状态管理

#### 4.1.2 音频播放组件
- 功能：播放转换后的音频
- 特性：
  - 原生音频控件
  - 自动加载
  - 错误处理

### 4.2 后端模块
#### 4.2.1 TTS 转换服务
- 入口：`/api/tts` (POST)
- 功能：
  - 文本预处理
  - TTS 转换
  - 音频文件管理
- 实现：<mcfile name="app.py" path="/Users/xiong/Documents/GitHub/text2speech82m/backend/app.py"></mcfile>

#### 4.2.2 音频文件服务
- 入口：`/api/audio/<filename>` (GET)
- 功能：音频文件的存储和检索