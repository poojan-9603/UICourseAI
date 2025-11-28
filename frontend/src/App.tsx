// frontend/src/App.tsx

import { useState } from "react";
import "./App.css";

type ApiResult = {
  subject: string;
  class_num: string;
  class_title: string;
  instructor: string;
  semester: string | null;
  A_rate: number;
  DFW_rate: number;
  total_students: number;
};

type ApiIntent = {
  polarity: string;
  subject: string | null;
  class_num: string | null;
  keywords: string[];
  recent: boolean;
  level: number | null;
  instructor_like: string | null;
  explain: boolean;
  details: boolean;
};

type ApiResponse = {
  used_llm: boolean;
  intent: ApiIntent;
  results: ApiResult[];
};

function App() {
  const [message, setMessage] = useState("");
  const [results, setResults] = useState<ApiResult[]>([]);
  const [intent, setIntent] = useState<ApiIntent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    

    try {
      const response = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          use_llm: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data: ApiResponse = await response.json();
      setResults(data.results);
      setIntent(data.intent);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-root">
      <div className="app-shell">
        <header className="app-header">
          <div className="logo-circle">UI</div>
          <div>
            <h1>UICourseAI</h1>
            <p className="subtitle">
              Ask for easy / hard courses, ML, data science, and more.
            </p>
          </div>
        </header>

        <main className="app-main">
          <form className="query-form" onSubmit={handleSubmit}>
            <input
              className="query-input"
              placeholder="Ask something like: easy 500-level ML course taught recently"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
            <button
              className="query-button"
              type="submit"
              disabled={loading}
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </form>

          {error && <div className="error-banner">{error}</div>}

          {intent && (
            <div className="intent-chip-row">
              <span className="intent-chip">
                Mode: {intent.polarity === "hard" ? "Hard / strict" : "Easy / chill"}
              </span>
              {intent.recent && <span className="intent-chip">Recent semesters</span>}
              {intent.level && (
                <span className="intent-chip">{intent.level}-level+</span>
              )}
              {intent.keywords?.length > 0 && (
                <span className="intent-chip">
                  Keywords: {intent.keywords.join(", ")}
                </span>
              )}
            </div>
          )}

          <section className="results-section">
            {results.length === 0 && !loading && !error && (
              <p className="placeholder-text">
                Results will show up here once you ask a question.
              </p>
            )}

            {results.length > 0 && (
              <div className="cards-grid">
                {results.map((r, idx) => (
                  <article key={idx} className="course-card">
                    <div className="course-header">
                      <h2>
                        {r.subject} {r.class_num}
                      </h2>
                      <p className="course-title">{r.class_title}</p>
                    </div>
                    <div className="course-meta">
                      <span>{r.instructor}</span>
                      <span>{r.semester || "Semester N/A"}</span>
                    </div>
                    <div className="course-stats">
                      <div>
                        <span className="stat-label">A%</span>
                        <span className="stat-value">
                          {r.A_rate.toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="stat-label">DFW%</span>
                        <span className="stat-value">
                          {r.DFW_rate.toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="stat-label">Students</span>
                        <span className="stat-value">{r.total_students}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
