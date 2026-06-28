import { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { AlbumCoverDefault } from '../common/AlbumCoverDefault';
import { useI18n } from '../../contexts/I18nContext';
import { api } from '../../services/api';

interface JoinAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  photoIds: string[];
  onJoined: () => void;
}

interface Album {
  id: number;
  name: string;
  photo_count: number;
  cover_photo_id: number | null;
  cover_photo_path: string | null;
}

export function JoinAlbumModal({ isOpen, onClose, photoIds, onJoined }: JoinAlbumModalProps) {
  const { t } = useI18n();
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newAlbumName, setNewAlbumName] = useState('');

  useEffect(() => {
    if (isOpen) {
      api.getAlbums().then(res => {
        const albums: Album[] = res.albums.map(a => ({
          id: a.id,
          name: a.name,
          photo_count: a.photo_count,
          cover_photo_id: a.cover_photo_id,
          cover_photo_path: (a as any).cover_photo_path ?? null,
        }));
        setAlbums(albums);
      }).catch(console.error);
      setSelectedAlbumIds(new Set());
      setSearchQuery('');
      setShowCreateForm(false);
      setNewAlbumName('');
    }
  }, [isOpen]);

  const filteredAlbums = albums.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleAlbum = (albumId: number) => {
    setSelectedAlbumIds(prev => {
      const next = new Set(prev);
      if (next.has(albumId)) {
        next.delete(albumId);
      } else {
        next.add(albumId);
      }
      return next;
    });
  };

  const handleCreateAlbum = async () => {
    if (!newAlbumName.trim()) return;
    try {
      const res = await api.createAlbum(newAlbumName.trim());
      const newAlbum: Album = { id: res.id, name: res.name, photo_count: 0, cover_photo_id: null, cover_photo_path: null };
      setAlbums([newAlbum, ...albums]);
      setSelectedAlbumIds(new Set([res.id]));
      setShowCreateForm(false);
      setNewAlbumName('');
    } catch (error) {
      console.error('创建相册失败:', error);
    }
  };

  const handleJoin = async () => {
    if (selectedAlbumIds.size === 0) return;
    setLoading(true);
    try {
      const ids = photoIds.map(id => Number(id));
      for (const albumId of selectedAlbumIds) {
        await api.batchAddPhotosToAlbum(albumId, ids);
      }
      onJoined();
      onClose();
    } catch (error) {
      console.error('加入相册失败:', error);
    }
    setLoading(false);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('joinAlbum.title')}
      size="lg"
      footer={
        <>
          <span className="text-sm text-text-secondary mr-auto">
            {t('joinAlbum.selectedSummary', { count: selectedAlbumIds.size, photoCount: photoIds.length })}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary hover:bg-page rounded transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleJoin}
            disabled={selectedAlbumIds.size === 0 || loading}
            className="px-5 py-2 text-sm bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {loading ? t('joinAlbum.joining') : t('joinAlbum.joinCount', { count: selectedAlbumIds.size })}
          </button>
        </>
      }
    >
      {showCreateForm ? (
        <div className="p-5">
          <input
            type="text"
            value={newAlbumName}
            onChange={(e) => setNewAlbumName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateAlbum();
              if (e.key === 'Escape') setShowCreateForm(false);
            }}
            placeholder={t('joinAlbum.newAlbumPlaceholder')}
            className="w-full px-3 py-2.5 border border-border rounded-md focus:outline-none focus:border-primary text-sm"
            autoFocus
          />
          <div className="flex gap-3 mt-3 justify-end">
            <button
              onClick={() => { setShowCreateForm(false); setNewAlbumName(''); }}
              className="px-4 py-1.5 text-sm text-text-secondary hover:bg-page rounded"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleCreateAlbum}
              disabled={!newAlbumName.trim()}
              className="px-4 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50"
            >
              {t('common.create')}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* 搜索框区域 */}
          <div className="px-5 pt-4 pb-3 flex-shrink-0">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('joinAlbum.searchPlaceholder')}
                className="w-full pl-9 pr-3 py-2.5 border border-border rounded-md focus:outline-none focus:border-primary text-sm bg-page"
              />
            </div>
          </div>

          {/* 相册卡片网格 - 最多 6 个格子(5 个相册 + 1 个新建),2 列 × 3 行 */}
          <div className="flex-1 overflow-y-auto p-3 min-h-0">
            {filteredAlbums.length === 0 && !searchQuery ? (
              <div className="py-12 text-center text-text-secondary text-sm">
                {t('joinAlbum.noAlbums')}
              </div>
            ) : filteredAlbums.length === 0 ? (
              <div className="py-12 text-center text-text-secondary text-sm">
                {t('joinAlbum.noMatch')}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2.5">
                {filteredAlbums.map(album => {
                  const isSelected = selectedAlbumIds.has(album.id);
                  return (
                    <button
                      key={album.id}
                      onClick={() => toggleAlbum(album.id)}
                      className={`relative text-left rounded-md flex items-center gap-2.5 p-2.5 transition-all border ${
                        isSelected
                          ? 'border-primary bg-primary-light'
                          : 'border-border hover:border-primary'
                      }`}
                    >
                      {/* 封面 48x48 */}
                      <div className="w-12 h-12 rounded flex-shrink-0 overflow-hidden">
                        <AlbumCoverDefault size="thumb" />
                      </div>
                      {/* 选中勾选 - 18x18 圆形 */}
                      {isSelected && (
                        <div className="absolute top-1.5 right-1.5 w-[18px] h-[18px] bg-primary rounded-full flex items-center justify-center shadow">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      )}
                      {/* 名称 + 数量 */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate text-text-primary">{album.name}</div>
                        <div className="text-xs text-text-tertiary">{t('main.photoCount', { count: album.photo_count })}</div>
                      </div>
                    </button>
                  );
                })}
                {/* 新建相册入口 - 网格内最后一格 */}
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="relative text-left rounded-md flex items-center gap-2.5 p-2.5 transition-all border border-dashed border-primary hover:bg-page"
                >
                  <div className="w-12 h-12 rounded flex-shrink-0 border-[1.5px] border-dashed border-primary flex items-center justify-center text-primary text-2xl">
                    +
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-primary">{t('joinAlbum.createNewAlbum')}</div>
                    <div className="text-xs text-text-tertiary">{t('joinAlbum.createNewAlbumDesc')}</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
