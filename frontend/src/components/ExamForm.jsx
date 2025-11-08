import { useState } from 'react'

function ExamForm({ onSubmit }) {
  const [files, setFiles] = useState([])
  const [questionHeader, setQuestionHeader] = useState('')
  const [questionDescription, setQuestionDescription] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [modelName, setModelName] = useState('google/gemini-flash-1.5-8b')
  const [dragOver, setDragOver] = useState(false)

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    const pdfFiles = selectedFiles.filter(file => file.type === 'application/pdf')
    
    if (pdfFiles.length !== selectedFiles.length) {
      alert('Only PDF files are allowed')
    }
    
    setFiles(prev => [...prev, ...pdfFiles])
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    const pdfFiles = droppedFiles.filter(file => file.type === 'application/pdf')
    
    if (pdfFiles.length !== droppedFiles.length) {
      alert('Only PDF files are allowed')
    }
    
    setFiles(prev => [...prev, ...pdfFiles])
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (files.length === 0) {
      alert('Please upload at least one PDF file')
      return
    }
    
    if (!questionHeader || !questionDescription) {
      alert('Please fill in all required fields')
      return
    }

    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    formData.append('question_header', questionHeader)
    formData.append('question_description', questionDescription)
    
    if (apiKey) {
      formData.append('api_key', apiKey)
    }
    
    if (modelName) {
      formData.append('model_name', modelName)
    }

    onSubmit(formData)
  }

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="files">
            Upload PDF Files <span style={{ color: 'red' }}>*</span>
          </label>
          <div
            className={`file-upload-area ${dragOver ? 'drag-over' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => document.getElementById('file-input').click()}
          >
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pdf"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <div>
              <p style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>📁</p>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                <strong>Click to upload</strong> or drag and drop
              </p>
              <p style={{ fontSize: '0.9rem', color: '#666' }}>
                PDF files only
              </p>
            </div>
          </div>
          
          {files.length > 0 && (
            <ul className="file-list">
              {files.map((file, index) => (
                <li key={index} className="file-item">
                  <span>📄 {file.name}</span>
                  <button type="button" onClick={() => removeFile(index)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="questionHeader">
            Exam Title/Header <span style={{ color: 'red' }}>*</span>
          </label>
          <input
            id="questionHeader"
            type="text"
            placeholder="e.g., Midterm Exam - Recommender Systems"
            value={questionHeader}
            onChange={(e) => setQuestionHeader(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="questionDescription">
            Question Requirements <span style={{ color: 'red' }}>*</span>
          </label>
          <textarea
            id="questionDescription"
            placeholder="e.g., Generate 10 multiple choice questions (mixed difficulty levels)"
            value={questionDescription}
            onChange={(e) => setQuestionDescription(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="modelName">AI Model (optional)</label>
          <input
            id="modelName"
            type="text"
            placeholder="google/gemini-flash-1.5-8b"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label htmlFor="apiKey">
            OpenRouter API Key (optional)
          </label>
          <input
            id="apiKey"
            type="password"
            placeholder="Leave blank to use environment variable"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <small style={{ color: '#666', fontSize: '0.875rem' }}>
            If not provided, will use OPENROUTER_API_KEY from backend environment
          </small>
        </div>

        <button type="submit" className="button-primary">
          🚀 Generate Exam
        </button>
      </form>
    </div>
  )
}

export default ExamForm
