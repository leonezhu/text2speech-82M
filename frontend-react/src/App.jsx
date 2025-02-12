import { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  // 将 loading 改为可修改的状态
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // 修改 articles 状态为可修改的
  const [articles, setArticles] = useState([]);
  const [showSentences, setShowSentences] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [displayLanguage, setDisplayLanguage] = useState("both");
  const [audioLanguage, setAudioLanguage] = useState(""); // 新增音频语言状态

  // 添加 audioRef
  const audioRef = useRef(null);

  // 添加可用语言列表状态
  const [availableLanguages, setAvailableLanguages] = useState([]);

  // 修改文章选择处理函数
  const handleArticleSelect = async (articleId) => {
    try {
      const response = await fetch(
        `http://localhost:5000/api/articles/${articleId}`
      );
      const article = await response.json();
      setSelectedArticle(article);

      // 获取可用的语言版本
      const languages = Object.keys(article.language_versions);
      setAvailableLanguages(languages);

      // 设置音频语言和URL
      const defaultAudioLang = languages[0];
      setAudioLanguage(defaultAudioLang);
      setAudioUrl(
        `http://localhost:5000/api/audio/${article.language_versions[defaultAudioLang].audio_filename}`
      );
      // 选择文章后自动隐藏侧边栏
      setIsSidebarOpen(false);
    } catch (err) {
      setError("获取文章失败: " + err.message);
    }
  };

  // 修改语言切换处理函数
  const handleDisplayLanguageChange = (lang) => {
    setDisplayLanguage(lang);
    if (!selectedArticle || !audioLanguage) return;

    const sentences = selectedArticle.language_versions[audioLanguage]?.sentences || [];
    let temp = [];
    if (lang === "both") {
      temp = sentences;
    } else {
      temp = sentences.filter(
        (sentence) => sentence.language === lang || sentence.text === "\n"
      );
    }
    setShowSentences(temp);
  };

  // 新增音频语言切换处理函数
  const handleAudioLanguageChange = (lang) => {
    setAudioLanguage(lang);
    if (selectedArticle && selectedArticle.language_versions[lang]) {
      setAudioUrl(
        `http://localhost:5000/api/audio/${selectedArticle.language_versions[lang].audio_filename}`
      );
      // 切换音频语言后更新显示的句子
      handleDisplayLanguageChange(displayLanguage);
    }
  };

  // 添加 handleSubmit 函数
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:5000/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          languages: "en",
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // 获取默认语言版本（优先使用中文）
        const defaultLang = data.language_versions["zh"] ? "zh" : "en";
        setAudioLanguage(defaultLang);
        setAudioUrl(
          `http://localhost:5000/api/audio/${data.language_versions[defaultLang].audio_filename}`
        );

        // 设置可用语言列表
        const languages = Object.keys(data.language_versions);
        setAvailableLanguages(languages);

        // 刷新文章列表
        await fetchArticles();
      } else {
        setError(data.error || "转换失败");
      }
    } catch (err) {
      setError("请求失败: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 添加 fetchArticles 函数
  const fetchArticles = async () => {
    try {
      const response = await fetch("http://localhost:5000/api/articles");
      const data = await response.json();
      setArticles(data);
    } catch (err) {
      setError("获取文章列表失败: " + err.message);
    }
  };

  // 添加初始加载文章列表
  useEffect(() => {
    fetchArticles();
  }, []);

  return (
    <div className="app-container">
      <button
        className="sidebar-toggle"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        aria-label={isSidebarOpen ? "隐藏列表" : "显示列表"}
      >
        <i className={`fas ${isSidebarOpen ? "fa-times" : "fa-bars"}`}></i>
      </button>

      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="article-list">
          {articles.map((article) => (
            <div
              key={article.id}
              className={`article-item ${
                selectedArticle?.id === article.id ? "selected" : ""
              }`}
              onClick={() => handleArticleSelect(article.id)}
            >
              {article.title}
            </div>
          ))}
        </div>
      </div>

      <div className="main-content">
        {selectedArticle && (
          <div className="language-controls">
            <select
              value={displayLanguage}
              onChange={(e) => handleDisplayLanguageChange(e.target.value)}
              className="language-selector"
            >
              <option value="both">中英对照</option>
              <option value="zh">仅中文</option>
              <option value="en">仅英文</option>
            </select>
            <div className="audio-language-buttons">
              {availableLanguages.map((lang) => (
                <button
                  key={lang}
                  className={`audio-language-btn ${audioLanguage === lang ? 'active' : ''}`}
                  onClick={() => handleAudioLanguageChange(lang)}
                >
                  {lang === "zh" ? "中" : "EN"}
                  <i className="fas fa-volume-up"></i>
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedArticle ? (
          <div className="article-view">
            <button
              className="back-button"
              onClick={() => setSelectedArticle(null)}
            >
              <i className="fas fa-arrow-left"></i> 返回
            </button>
            <div className="audio-player">
              <audio
                ref={audioRef}
                controls
                src={audioUrl}
                onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
              >
                您的浏览器不支持音频播放
              </audio>
            </div>
            <div className="article-content">
              <h1>{selectedArticle.title}</h1>
              <div className="sentences-container">
                {showSentences.map((sentence, index) =>
                  sentence.text === "\n" ? (
                    <br key={index} />
                  ) : (
                    <span
                      key={index}
                      className={`sentence ${
                        currentTime >= sentence.start_time &&
                        currentTime <= sentence.end_time
                          ? "active"
                          : ""
                      }`}
                      onClick={() => {
                        if (audioRef.current) {
                          audioRef.current.currentTime = sentence.start_time;
                          audioRef.current.play();
                        }
                      }}
                    >
                      {sentence.text}{" "}
                    </span>
                  )
                )}
              </div>
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
              <button
                type="submit"
                disabled={loading || !text}
                className="convert-btn"
              >
                {loading ? "转换中..." : "转换"}
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
  );
}

export default App;
