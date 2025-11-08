import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

function Results({ questions, onReset }) {
  const handleDownload = () => {
    const blob = new Blob([questions], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'generated_exam.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(questions)
      alert('Copied to clipboard!')
    } catch (err) {
      alert('Failed to copy: ' + err.message)
    }
  }

  return (
    <div className="card">
      <div className="results-section">
        <div className="results-header">
          <h2>✅ Exam Generated Successfully!</h2>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={handleCopy} className="button-secondary">
              📋 Copy
            </button>
            <button onClick={handleDownload} className="button-secondary">
              💾 Download
            </button>
            <button onClick={onReset} className="button-secondary">
              🔄 New Exam
            </button>
          </div>
        </div>

        <div className="results-content">
          <ReactMarkdown
            remarkPlugins={[remarkMath]}
            rehypePlugins={[rehypeKatex]}
          >
            {questions}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

export default Results
