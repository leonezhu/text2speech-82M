import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [text, setText] = useState('')
  const [audioUrl, setAudioUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [articles, setArticles] = useState([])
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  useEffect(() => {
    fetchArticles()
  }, [])

  const fetchArticles = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/articles')
      const data = await response.json()
      setArticles(data)
    } catch (err) {
      setError('获取文章列表失败: ' + err.message)
    }
  }

  const handleArticleSelect = async (articleId) => {
    try {
      const response = await fetch(`http://localhost:5000/api/articles/${articleId}`)
      const article = await response.json()
      setSelectedArticle(article)
      setAudioUrl(`http://localhost:5000/api/audio/${article.audio_filename}`)
    } catch (err) {
      setError('获取文章失败: ' + err.message)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch('http://localhost:5000/api/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      })

      const data = await response.json()
      
      if (response.ok) {
        setAudioUrl(`http://localhost:5000/api/audio/${data.filename}`)
        await fetchArticles()
      } else {
        setError(data.error || '转换失败')
      }
    } catch (err) {
      setError('请求失败: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <button 
        className="sidebar-toggle"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        aria-label={isSidebarOpen ? '隐藏列表' : '显示列表'}
      >
        <i className={`fas ${isSidebarOpen ? 'fa-times' : 'fa-bars'}`}></i>
      </button>

      <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        {/* <h2>文章列表</h2> */}
        <div className="article-list">
          {articles.map(article => (
            <div
              key={article.id}
              className={`article-item ${selectedArticle?.id === article.id ? 'selected' : ''}`}
              onClick={() => handleArticleSelect(article.id)}
            >
              {article.title}
            </div>
          ))}
        </div>
      </div>
      
      <div className="main-content">
        
        {selectedArticle ? (
          <div className="article-view">
            <button 
              className="back-button"
              onClick={() => setSelectedArticle(null)}
            >
              <i className="fas fa-arrow-left"></i> 返回
            </button>
            <div className="audio-player">
              <audio controls src={audioUrl}>
                您的浏览器不支持音频播放
              </audio>
            </div>
            <div className="article-content">
              <h1>{selectedArticle.title}</h1>
              <p>{selectedArticle.content}</p>
            </div>
          </div>
        ) : (
          <div className="text-input-view">
            <div className="page-title">
              <h1>文字转语音</h1>
            </div>
            <form onSubmit={handleSubmit}>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="请输入要转换的文字..."
                rows={5}
              />
              <button type="submit" disabled={loading || !text} className="convert-btn">
                {loading ? '转换中...' : '转换'}
              </button>
            </form>
            {audioUrl && (
              <div className="audio-player">
                <audio controls src={audioUrl}>
                  您的浏览器不支持音频播放
                </audio>
              </div>
            )}
            {error && <div className="error">{error}</div>}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
