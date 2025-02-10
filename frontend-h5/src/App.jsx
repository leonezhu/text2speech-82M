import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [articles, setArticles] = useState([])
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)

  const audioRef = useRef(null)

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
        const sortedArticles = articles.sort((a, b) => b.id.localeCompare(a.id))
        setArticles(sortedArticles)
        // 自动选择第一篇文章
        if (sortedArticles.length > 0) {
          setSelectedArticle(sortedArticles[0])
        }
      }
    } catch (err) {
      setError('获取文章列表失败: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleArticleSelect = (article) => {
    setSelectedArticle(article)
    setIsSidebarOpen(false)
  }

  return (
    <div className="app-container">
      <button
        className="sidebar-toggle"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
      >
        ☰
      </button>

      <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <h2> &nbsp; </h2>
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
                onClick={() => handleArticleSelect(article)}
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
            <div className="audio-player">
              <audio 
                ref={audioRef}
                controls
                src={selectedArticle.audioUrl}
                onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
              >
                您的浏览器不支持音频播放
              </audio>
            </div>
            <div className="article-content">
              <h2>{selectedArticle.title}</h2>
              {selectedArticle.sentences?.map((sentence, index) => (
                sentence.text === '\n' ? (
                  <br key={index} />
                ) : (
                  <span
                    key={index}
                    className={`sentence ${currentTime >= sentence.start_time && currentTime <= sentence.end_time ? 'active' : ''}`}
                    onClick={() => {
                      if (audioRef.current) {
                        audioRef.current.currentTime = sentence.start_time;
                        audioRef.current.play();
                      }
                    }}
                    ref={el => {
                      if (el && currentTime >= sentence.start_time && currentTime <= sentence.end_time) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }
                    }}
                  >
                    {sentence.text}{' '}
                  </span>
                )
              ))}
            </div>
          </div>
        ) : loading ? (
          <div className="loading">加载中...</div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : null}
      </div>
    </div>
  )
}

export default App
