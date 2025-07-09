import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DocumentsManager = () => {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (files, documentType = 'document') => {
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', documentType);
      formData.append('description', `${documentType} - ${file.name}`);

      try {
        setUploadProgress(0);
        const response = await axios.post(`${API}/documents/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          },
        });

        setDocuments(prev => [...prev, response.data]);
      } catch (error) {
        console.error('Error uploading file:', error);
        alert('Ошибка при загрузке файла: ' + (error.response?.data?.detail || error.message));
      } finally {
        setUploadProgress(0);
      }
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleFileInput = (e) => {
    const files = Array.from(e.target.files);
    handleFileUpload(files);
  };

  const deleteDocument = async (documentId) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот документ?')) {
      return;
    }

    try {
      await axios.delete(`${API}/documents/${documentId}`);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Ошибка при удалении документа');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (mimeType) => {
    if (mimeType?.startsWith('image/')) return '🖼️';
    if (mimeType?.startsWith('application/pdf')) return '📄';
    if (mimeType?.startsWith('application/msword') || mimeType?.includes('wordprocessingml')) return '📝';
    if (mimeType?.startsWith('application/vnd.ms-excel') || mimeType?.includes('spreadsheetml')) return '📊';
    return '📁';
  };

  if (loading) {
    return (
      <div className="documents-loading">
        <div className="loading-spinner"></div>
        <p>Загрузка документов...</p>
      </div>
    );
  }

  return (
    <div className="documents-manager">
      <div className="documents-header">
        <h2>Мои документы</h2>
        <p>Управление вашими документами и файлами</p>
      </div>

      {/* Upload Area */}
      <div 
        className={`upload-area ${isDragging ? 'dragging' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="upload-content">
          <div className="upload-icon">📁</div>
          <h3>Перетащите файлы сюда</h3>
          <p>или нажмите для выбора файлов</p>
          <input
            type="file"
            multiple
            onChange={handleFileInput}
            className="file-input"
            accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx"
          />
        </div>
        
        {uploadProgress > 0 && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <span>{uploadProgress}%</span>
          </div>
        )}
      </div>

      {/* Documents Grid */}
      <div className="documents-grid">
        {documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📄</div>
            <h3>Документы не найдены</h3>
            <p>Загрузите ваши первые документы</p>
          </div>
        ) : (
          documents.map(doc => (
            <div key={doc.id} className="document-card">
              <div className="document-preview">
                {doc.mime_type?.startsWith('image/') ? (
                  <img 
                    src={`${BACKEND_URL}${doc.url}`} 
                    alt={doc.original_name}
                    className="document-image"
                  />
                ) : (
                  <div className="document-icon">
                    {getFileIcon(doc.mime_type)}
                  </div>
                )}
              </div>
              
              <div className="document-info">
                <h4 className="document-name">{doc.original_name}</h4>
                <div className="document-meta">
                  <span className="document-type">{doc.type}</span>
                  <span className="document-size">{formatFileSize(doc.file_size)}</span>
                </div>
                <div className="document-date">
                  {new Date(doc.created_at).toLocaleDateString()}
                </div>
              </div>
              
              <div className="document-actions">
                <a 
                  href={`${BACKEND_URL}${doc.url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="action-btn view-btn"
                >
                  👁️
                </a>
                <button 
                  onClick={() => deleteDocument(doc.id)}
                  className="action-btn delete-btn"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DocumentsManager;