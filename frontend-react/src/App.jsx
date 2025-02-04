import { useState } from 'react'
import './App.css'

function App() {
  const [text, setText] = useState('')
  const [audioUrl, setAudioUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
    <div className="container">
      <h1>文字转语音</h1>
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
      
      {error && <div className="error">{error}</div>}
      
      {audioUrl && (
        <div className="audio-player">
          <audio controls src={audioUrl}>
            您的浏览器不支持音频播放
          </audio>
        </div>
      )}
    </div>
  )
}

export default App
