import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [articles, setArticles] = useState([])
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const GITHUB_REPO = 'leonezhu/text2speech-82M'
  const GITHUB_BRANCH = 'master'

  useEffect(() => {
    fetchArticles()
  }, [])

  const fetchArticles = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/backend/articles?ref=${GITHUB_BRANCH}`)
      const data = await response.json()
      
      if (Array.isArray(data)) {
        const articlePromises = data.map(async (file) => {
          const articleResponse = await fetch(file.download_url)
          const articleData = await articleResponse.json()
          return {
            id: file.name.replace('.json', ''),
            ...articleData,
            audioUrl: `https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/backend/audio_files/${articleData.audio_filename}`
          }
        })

        const articles = await Promise.all(articlePromises)
        setArticles(articles.sort((a, b) => b.id.localeCompare(a.id)))
      }
    } catch (err) {
      setError('获取文章列表失败: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <div className="sidebar">
        <h2>文章列表</h2>
        {loading ? (
          <div className="loading">加载中...</div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : (
          <div className="article-list">
            {articles.map(article => (
              <div
                key={article.id}
                className={`article-item ${selectedArticle?.id === article.id ? 'selected' : ''}`}
                onClick={() => setSelectedArticle(article)}
              >
                {article.title || article.id}
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="main-content">
        {selectedArticle ? (
          <div className="article-view">
            <button 
              className="back-button"
              onClick={() => setSelectedArticle(null)}
            >
              返回列表
            </button>
            <h1>{selectedArticle.title}</h1>
            <div className="audio-player">
              <audio
                controls
                src={selectedArticle.audioUrl}
              >
                您的浏览器不支持音频播放
              </audio>
            </div>
            <div className="article-content">
              {selectedArticle.sentences?.map((sentence, index) => (
                sentence.text === '\n' ? (
                  <br key={index} />
                ) : (
                  <span key={index} className="sentence">
                    {sentence.text}{' '}
                  </span>
                )
              ))}
            </div>
          </div>
        ) : (
          <div className="welcome-message">
            <h1>文字转语音展示</h1>
            <p>请从左侧选择一篇文章查看详情</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
