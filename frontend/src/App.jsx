import { useState } from 'react'
import ExamForm from './components/ExamForm'
import Results from './components/Results'
import './index.css'
import 'katex/dist/katex.min.css'

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleGenerateExam = async (formData) => {
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await fetch('http://localhost:8000/api/generate-exam', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to generate exam')
      }

      if (data.success) {
        setResults(data.questions)
      } else {
        setError(data.error || 'Unknown error occurred')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResults(null)
    setError(null)
  }

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>📝 AI Exam Generator</h1>
          <p>Upload your PDFs and generate custom exams with AI</p>
        </header>

        {!results && !loading && (
          <ExamForm onSubmit={handleGenerateExam} />
        )}

        {loading && (
          <div className="card">
            <div className="loading-spinner">
              <div className="spinner"></div>
              <p className="loading-text">
                Generating your exam... This may take a minute.
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="card">
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
            <button 
              onClick={handleReset} 
              className="button-primary"
              style={{ marginTop: '1rem' }}
            >
              Try Again
            </button>
          </div>
        )}

        {results && !loading && (
          <Results questions={results} onReset={handleReset} />
        )}
      </div>
    </div>
  )
}

export default App
