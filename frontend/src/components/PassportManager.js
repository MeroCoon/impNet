import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PassportManager = () => {
  const { user } = useAuth();
  const [passport, setPassport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    middle_name: '',
    birth_date: '',
    birth_place: '',
    gender: 'М',
    issue_place: 'МВД России'
  });
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    fetchPassport();
    fetchDocuments();
  }, []);

  const fetchPassport = async () => {
    try {
      const response = await axios.get(`${API}/passport`);
      setPassport(response.data);
      setFormData({
        first_name: response.data.first_name,
        last_name: response.data.last_name,
        middle_name: response.data.middle_name || '',
        birth_date: response.data.birth_date,
        birth_place: response.data.birth_place,
        gender: response.data.gender,
        issue_place: response.data.issue_place
      });
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error('Error fetching passport:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API}/documents`);
      setDocuments(response.data.filter(doc => doc.mime_type?.startsWith('image/')));
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      let response;
      if (passport) {
        response = await axios.put(`${API}/passport`, formData);
      } else {
        response = await axios.post(`${API}/passport`, formData);
      }
      
      setPassport(response.data);
      setEditing(false);
    } catch (error) {
      console.error('Error saving passport:', error);
      alert('Ошибка при сохранении паспорта: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const setPassportPhoto = async (documentId) => {
    try {
      const formData = new FormData();
      formData.append('document_id', documentId);
      
      await axios.post(`${API}/passport/photo`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Refresh passport data
      await fetchPassport();
    } catch (error) {
      console.error('Error setting passport photo:', error);
      alert('Ошибка при установке фото паспорта');
    }
  };

  const handlePhotoUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'passport_photo');
    formData.append('description', 'Фото для паспорта');

    try {
      const response = await axios.post(`${API}/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Automatically set as passport photo
      await setPassportPhoto(response.data.id);
      
      // Refresh documents
      await fetchDocuments();
    } catch (error) {
      console.error('Error uploading photo:', error);
      alert('Ошибка при загрузке фото');
    }
  };

  if (loading) {
    return (
      <div className="passport-loading">
        <div className="loading-spinner"></div>
        <p>Загрузка паспорта...</p>
      </div>
    );
  }

  return (
    <div className="passport-manager">
      <div className="passport-header">
        <h2>Виртуальный паспорт</h2>
        <p>Управление вашим цифровым паспортом</p>
      </div>

      {!passport && !editing ? (
        <div className="no-passport">
          <div className="no-passport-icon">🆔</div>
          <h3>Паспорт не создан</h3>
          <p>Создайте ваш виртуальный паспорт для использования в системе</p>
          <button 
            onClick={() => setEditing(true)}
            className="create-passport-btn"
          >
            Создать паспорт
          </button>
        </div>
      ) : (
        <div className="passport-content">
          {/* Passport Display */}
          {passport && !editing && (
            <div className="passport-card">
              <div className="passport-header-section">
                <div className="passport-title">
                  <h3>ПАСПОРТ ГРАЖДАНИНА</h3>
                  <p>impNet ID</p>
                </div>
                <div className="passport-photo">
                  {passport.photo_url ? (
                    <img 
                      src={`${BACKEND_URL}${passport.photo_url}`} 
                      alt="Фото паспорта"
                      className="passport-photo-img"
                    />
                  ) : (
                    <div className="passport-photo-placeholder">
                      <span>📷</span>
                      <p>Нет фото</p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="passport-info">
                <div className="passport-field">
                  <label>Фамилия</label>
                  <span>{passport.last_name}</span>
                </div>
                <div className="passport-field">
                  <label>Имя</label>
                  <span>{passport.first_name}</span>
                </div>
                {passport.middle_name && (
                  <div className="passport-field">
                    <label>Отчество</label>
                    <span>{passport.middle_name}</span>
                  </div>
                )}
                <div className="passport-field">
                  <label>Пол</label>
                  <span>{passport.gender}</span>
                </div>
                <div className="passport-field">
                  <label>Дата рождения</label>
                  <span>{new Date(passport.birth_date).toLocaleDateString()}</span>
                </div>
                <div className="passport-field">
                  <label>Место рождения</label>
                  <span>{passport.birth_place}</span>
                </div>
              </div>
              
              <div className="passport-details">
                <div className="passport-field">
                  <label>Серия и номер</label>
                  <span className="passport-number">{passport.series} {passport.number}</span>
                </div>
                <div className="passport-field">
                  <label>Дата выдачи</label>
                  <span>{new Date(passport.issue_date).toLocaleDateString()}</span>
                </div>
                <div className="passport-field">
                  <label>Выдан</label>
                  <span>{passport.issue_place}</span>
                </div>
              </div>
              
              <div className="passport-actions">
                <button 
                  onClick={() => setEditing(true)}
                  className="edit-passport-btn"
                >
                  Редактировать
                </button>
              </div>
            </div>
          )}

          {/* Photo Management */}
          {passport && (
            <div className="photo-management">
              <h3>Управление фото</h3>
              <div className="photo-upload">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      handlePhotoUpload(file);
                    }
                  }}
                  className="photo-input"
                />
                <div className="photo-upload-label">
                  <span>📷</span>
                  <p>Загрузить новое фото</p>
                </div>
              </div>
              
              {documents.length > 0 && (
                <div className="photo-gallery">
                  <h4>Выберите фото из загруженных:</h4>
                  <div className="photo-grid">
                    {documents.map(doc => (
                      <div key={doc.id} className="photo-option">
                        <img 
                          src={`${BACKEND_URL}${doc.url}`} 
                          alt={doc.original_name}
                          className="photo-thumbnail"
                        />
                        <button 
                          onClick={() => setPassportPhoto(doc.id)}
                          className="select-photo-btn"
                        >
                          Выбрать
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Passport Form */}
          {editing && (
            <div className="passport-form">
              <h3>{passport ? 'Редактировать паспорт' : 'Создать паспорт'}</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Фамилия *</label>
                    <input
                      type="text"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Имя *</label>
                    <input
                      type="text"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Отчество</label>
                    <input
                      type="text"
                      name="middle_name"
                      value={formData.middle_name}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="form-group">
                    <label>Пол *</label>
                    <select
                      name="gender"
                      value={formData.gender}
                      onChange={handleInputChange}
                      required
                    >
                      <option value="М">Мужской</option>
                      <option value="Ж">Женский</option>
                    </select>
                  </div>
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label>Дата рождения *</label>
                    <input
                      type="date"
                      name="birth_date"
                      value={formData.birth_date}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Место рождения *</label>
                    <input
                      type="text"
                      name="birth_place"
                      value={formData.birth_place}
                      onChange={handleInputChange}
                      required
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Кем выдан *</label>
                  <input
                    type="text"
                    name="issue_place"
                    value={formData.issue_place}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                
                <div className="form-actions">
                  <button type="submit" className="save-btn">
                    {passport ? 'Сохранить изменения' : 'Создать паспорт'}
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setEditing(false)}
                    className="cancel-btn"
                  >
                    Отмена
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PassportManager;