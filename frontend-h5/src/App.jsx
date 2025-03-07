import { useState, useEffect, useRef } from "react";
import "./App.css";

function App() {
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [displayLanguage, setDisplayLanguage] = useState("both");
  const [audioLanguage, setAudioLanguage] = useState("");
  const [showSentences, setShowSentences] = useState([]);
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [githubRepo, setGithubRepo] = useState("");

  const audioRef = useRef(null);
  const GITHUB_BRANCH = "master";

  useEffect(() => {
    // 从 localStorage 获取配置
    const savedRepo = localStorage.getItem("githubRepo");
    if (savedRepo) {
      setGithubRepo(savedRepo);
    } else {
      setShowConfigModal(true);
    }
  }, []);

  useEffect(() => {
    if (githubRepo) {
      fetchArticles();
    }
  }, [githubRepo]);

  const handleConfigSubmit = (repo) => {
    setGithubRepo(repo);
    localStorage.setItem("githubRepo", repo);
    setShowConfigModal(false);
    fetchArticles();
  };

  const fetchArticles = async () => {
    if (!githubRepo) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `https://api.github.com/repos/${githubRepo}/contents/articles?ref=${GITHUB_BRANCH}`
      );
      const data = await response.json();

      if (Array.isArray(data)) {
        const articlePromises = data.map(async (file) => {
          const articleResponse = await fetch(file.download_url);
          const articleData = await articleResponse.json();
          return {
            id: file.name.replace(".json", ""),
            ...articleData,
          };
        });

        const articles = await Promise.all(articlePromises);
        const sortedArticles = articles.sort((a, b) =>
          b.id.localeCompare(a.id)
        );
        setArticles(sortedArticles);
        if (sortedArticles.length > 0) {
          handleArticleSelect(sortedArticles[0]);
        }
      }
    } catch (err) {
      setError("获取文章列表失败: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleArticleSelect = (article) => {
    setSelectedArticle(article);
    setIsSidebarOpen(false);

    const languages = Object.keys(article.language_versions || {});
    setAvailableLanguages(languages);

    const defaultLang = languages.includes("en") ? "en" : languages[0];
    setAudioLanguage(defaultLang);

    if (
      article &&
      article.language_versions &&
      article.language_versions[defaultLang]
    ) {
      const sentences = article.language_versions[defaultLang].sentences || [];
      const audioUrl = `https://raw.githubusercontent.com/${githubRepo}/${GITHUB_BRANCH}/audio_files/${article.language_versions[defaultLang].audio_filename}`;
      setSelectedArticle((prev) => ({ ...prev, audioUrl }));
      handleDisplayLanguageChange("both", sentences);
    } else {
      setError("文章内容加载失败");
    }
  };

  useEffect(() => {
    if (selectedArticle?.audioUrl && audioRef.current) {
      audioRef.current.src = selectedArticle.audioUrl;
      audioRef.current.load();
    }
  }, [selectedArticle]);


  // 添加键盘事件处理函数
  useEffect(() => {
    const handleKeyPress = (e) => {
      // 如果正在输入文本（比如在配置模态框中），则不处理空格键
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }
      
      // 当按下空格键且有选中的文章时
      if (e.code === 'Space' && selectedArticle && audioRef.current) {
        e.preventDefault(); // 阻止页面滚动
        if (audioRef.current.paused) {
          audioRef.current.play();
        } else {
          audioRef.current.pause();
        }
      }
    };

    // 添加事件监听
    window.addEventListener('keydown', handleKeyPress);

    // 清理函数
    return () => {
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, [selectedArticle]); // 依赖项包含 selectedArticle


  const handleDisplayLanguageChange = (lang, sentences = null) => {
    setDisplayLanguage(lang);
    const targetSentences =
      sentences ||
      (selectedArticle &&
        selectedArticle.language_versions &&
        selectedArticle.language_versions[audioLanguage]?.sentences) ||
      [];
    if (!targetSentences) return;

    let temp = [];
    if (lang === "both") {
      temp = targetSentences;
    } else {
      temp = targetSentences.filter(
        (sentence) => sentence.language === lang || sentence.text === "\n"
      );
    }
    setShowSentences(temp);
  };

  return (
    <div className="app-container">
      <div className="top-toolbar">
        <div className="toolbar-right">
          <select
            value={displayLanguage}
            onChange={(e) => handleDisplayLanguageChange(e.target.value)}
            className="language-selector"
          >
            <option value="both">中英对照</option>
            <option value="zh">仅中文</option>
            <option value="en">仅英文</option>
          </select>

          {/* <div className="audio-language-buttons">
            {availableLanguages.map((lang) => (
              <button
                key={lang}
                className="toolbar-button"
                onClick={() => {
                  setAudioLanguage(lang);
                  if (selectedArticle) {
                    const newAudioUrl = `https://raw.githubusercontent.com/${githubRepo}/${GITHUB_BRANCH}/backend/audio_files/${selectedArticle.audio_filename.replace(
                      /_(en|zh)_/,
                      `_${lang}_`
                    )}`;
                    audioRef.current.src = newAudioUrl;
                    audioRef.current.load();
                    audioRef.current.play();
                  }
                }}
                title={lang === "zh" ? "中文音频" : "英文音频"}
              >
                {lang === "zh" ? "🔊中" : "🔊EN"}
              </button>
            ))}
          </div> */}
       
          <button
            className="toolbar-button"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            title="文章列表"
          >
            ☰
          </button>
        </div>
      </div>

      {showConfigModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>配置 GitHub 仓库</h3>
            <input
              type="text"
              defaultValue={githubRepo}
              placeholder="请输入 GitHub 仓库地址 (格式: 用户名/仓库名)"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleConfigSubmit(e.target.value);
                }
              }}
            />
            <div className="modal-buttons">
              <button
                onClick={() =>
                  handleConfigSubmit(
                    document.querySelector(".modal-content input").value
                  )
                }
              >
                确定
              </button>
              {githubRepo && (
                <button onClick={() => setShowConfigModal(false)}>取消</button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="toolbar-left">
          <button
            className="toolbar-button"
            onClick={() => setShowConfigModal(true)}
            title="配置仓库"
          >
            ⚙️
          </button>
        </div>
        
        {loading ? (
          <div className="loading">加载中...</div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : (
          <div className="article-list">
            {articles.map((article) => (
              <div
                key={article.id}
                className={`article-item ${
                  selectedArticle?.id === article.id ? "selected" : ""
                }`}
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
            <div className="article-content">
              <h2>{selectedArticle.title}</h2>

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
                    ref={(el) => {
                      if (
                        el &&
                        currentTime >= sentence.start_time &&
                        currentTime <= sentence.end_time
                      ) {
                        el.scrollIntoView({
                          behavior: "smooth",
                          block: "center",
                        });
                      }
                    }}
                  >
                    {sentence.text}{" "}
                  </span>
                )
              )}
            </div>
          </div>
        ) : loading ? (
          <div className="loading">加载中...</div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : null}
      </div>
      {selectedArticle ? (
        <div className="audio-player-bottom">
          <audio
            ref={audioRef}
            controls
            src={selectedArticle.audioUrl}
            onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
          >
            您的浏览器不支持音频播放
          </audio>
        </div>
      ) : null}
    </div>
  );
}

export default App;
