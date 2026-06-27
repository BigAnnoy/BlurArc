import { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
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
    <Modal isOpen={isOpen} onClose={onClose} title={`加入相册 · ${photoIds.length} 张照片`}>
      <div className="w-[560px] max-w-[90vw]">
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
              placeholder="新相册名称..."
              className="w-full px-3 py-2.5 border border-border rounded-md focus:outline-none focus:border-primary text-sm"
              autoFocus
            />
            <div className="flex gap-3 mt-3 justify-end">
              <button
                onClick={() => { setShowCreateForm(false); setNewAlbumName(''); }}
                className="px-4 py-1.5 text-sm text-text-secondary hover:bg-page rounded"
              >
                取消
              </button>
              <button
                onClick={handleCreateAlbum}
                disabled={!newAlbumName.trim()}
                className="px-4 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50"
              >
                创建
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* 搜索框区域（原型：padding 16px 20px 12px） */}
            <div className="px-5 pt-4 pb-3">
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索相册..."
                  className="w-full pl-9 pr-3 py-2.5 border border-border rounded-md focus:outline-none focus:border-primary text-sm bg-page"
                />
              </div>
            </div>
            <div className="border-t border-border" />

            {/* 相册卡片网格（原型 .album-pick-grid：2 列 gap 10px，padding 12px） */}
            <div className="max-h-[360px] overflow-y-auto p-3">
              {filteredAlbums.length === 0 ? (
                <div className="py-12 text-center text-text-secondary text-sm">
                  {searchQuery ? '没有匹配的相册' : '还没有相册，点击下方创建第一个'}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2.5">
                  {filteredAlbums.map(album => {
                    const isSelected = selectedAlbumIds.has(album.id);
                    return (
                      <button
                        key={album.id}
                        onClick={() => toggleAlbum(album.id)}
                        className={`relative text-left rounded-md p-2 flex flex-col gap-1.5 transition-all border ${
                          isSelected
                            ? 'border-primary bg-primary-light'
                            : 'border-border hover:border-primary'
                        }`}
                      >
                        {/* 默认封面（v0.7 §5.8：cyan 渐变 + 📷 + PHOTOS） */}
                        <div className="cover-default">
                          <span className="emoji">📷</span>
                          <span className="label">PHOTOS</span>
                        </div>
                        {/* 选中勾选 */}
                        {isSelected && (
                          <div className="absolute top-1.5 right-1.5 w-5 h-5 bg-primary rounded-full flex items-center justify-center shadow">
                            <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          </div>
                        )}
                        {/* 名称 + 数量 */}
                        <div>
                          <div className="text-[13px] font-medium truncate text-text-primary">{album.name}</div>
                          <div className="text-[11px] text-text-tertiary">{album.photo_count} 张</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="border-t border-border" />

            {/* 新建相册入口（原型 .album-pick.create-new：横向条目） */}
            <button
              onClick={() => setShowCreateForm(true)}
              className="w-full flex items-center gap-2 px-5 py-3 hover:bg-page transition-colors text-left"
            >
              <div className="w-9 h-9 rounded border-[1.5px] border-dashed border-primary flex items-center justify-center text-primary text-lg flex-shrink-0">
                +
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-primary">新建相册...</div>
                <div className="text-[11px] text-text-tertiary">创建一个新相册</div>
              </div>
            </button>
          </>
        )}

        {/* 底部（原型 .modal-footer：已选 N 个相册 · 含 M 张照片） */}
        <div className="flex justify-between items-center px-5 py-3 border-t border-border">
          <span className="text-[13px] text-text-secondary">
            已选 <span className="text-primary font-medium">{selectedAlbumIds.size}</span> 个相册 · 含 {photoIds.length} 张照片
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-text-secondary hover:bg-page rounded transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleJoin}
              disabled={selectedAlbumIds.size === 0 || loading}
              className="px-5 py-2 text-sm bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50 transition-colors"
            >
              {loading ? '加入中...' : `加入 ${selectedAlbumIds.size || ''} 个相册`}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
