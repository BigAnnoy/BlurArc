import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Modal } from '../common/Modal';
import { useI18n } from '../../contexts/I18nContext';
import { api } from '../../services/api';

// ——— 小型确认弹窗组件 ———
interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  desc: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  danger?: boolean;
}
function ConfirmDialog({ isOpen, title, desc, confirmLabel = '确认', onConfirm, onCancel, loading, danger }: ConfirmDialogProps) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} />
      <div className="relative bg-card border border-border rounded-xl shadow-2xl w-80 p-5 space-y-3">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-text-tertiary leading-relaxed">{desc}</p>
        <div className="flex gap-2 pt-1">
          <button
            onClick={(e) => { e.stopPropagation(); onCancel(); }}
            disabled={loading}
            className="flex-1 px-3 py-2 rounded-lg text-xs border border-border hover:bg-page transition-colors active:scale-95"
          >
            取消
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onConfirm(); }}
            disabled={loading}
            className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-all active:scale-95 ${
              danger
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-primary hover:bg-primary-hover text-white'
            } ${loading ? 'opacity-60 cursor-not-allowed' : ''}`}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-1.5">
                <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                处理中
              </span>
            ) : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

interface PairedDevice {
  device_name: string;
  paired_at: string;
  token: string;
}

interface MobileDeviceManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileDeviceManager({ isOpen, onClose }: MobileDeviceManagerProps) {
  const { t } = useI18n();
  const [running, setRunning] = useState(false);
  const [toggleLoading, setToggleLoading] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState<{ local_ip: string; port: number } | null>(null);
  const [pairedDevices, setPairedDevices] = useState<PairedDevice[]>([]);
  // 撤销确认弹窗状态
  const [revokeTarget, setRevokeTarget] = useState<PairedDevice | null>(null);  // 单设备撤销
  const [revokeAllConfirm, setRevokeAllConfirm] = useState(false);              // 全部撤销
  const [revokeLoading, setRevokeLoading] = useState(false);

  // 配对状态
  const [pairingState, setPairingState] = useState<'idle' | 'broadcasting' | 'request_received' | 'show_code' | 'success'>('idle');
  const [pendingDeviceName, setPendingDeviceName] = useState('');
  const [pairingCode, setPairingCode] = useState('');
  const [codeCountdown, setCodeCountdown] = useState(0);
  const pairedCountRef = useRef(0); // 进入 show_code 时的设备数，用于检测新设备配对成功
  const codeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null); // 配对码倒计时 timer ref

  const loadStatus = useCallback(async () => {
    try {
      const status = await api.getMobileStatus();
      setRunning(status.running);
      if (status.running && status.local_ip) setConnectionInfo({ local_ip: status.local_ip, port: status.port! });
      if (status.running) {
        const dev = await api.getMobileDevices();
        setPairedDevices(dev.devices);
      }
    } catch {}
  }, []);

  useEffect(() => { if (isOpen) loadStatus(); }, [isOpen, loadStatus]);

  // 检测配对完成（手机端正确提交配对码后设备数增加）
  useEffect(() => {
    if (!isOpen || pairingState !== 'show_code') return;
    const baseCount = pairedCountRef.current;
    const interval = setInterval(async () => {
      try {
        const dev = await api.getMobileDevices().catch(() => ({ devices: [] }));
        setPairedDevices(dev.devices);
        if (dev.devices.length > baseCount) {
          clearInterval(interval);
          setPairingState('success');
          setCodeCountdown(0);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [isOpen, pairingState]);

  // 定期刷新已配对设备列表
  useEffect(() => {
    if (!isOpen || !running) return;
    const interval = setInterval(async () => {
      try {
        const dev = await api.getMobileDevices().catch(() => ({ devices: [] }));
        setPairedDevices(dev.devices);
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [isOpen, running]);

  // 配对模式轮询
  useEffect(() => {
    if (!isOpen || pairingState !== 'broadcasting') return;
    const interval = setInterval(async () => {
      try {
        const res = await api.getPairingPending();
        if (res.status === 'pending') {
          setPendingDeviceName(res.device_name || 'Unknown');
          setPairingState('request_received');
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [isOpen, pairingState]);

  const handleToggle = async () => {
    setToggleLoading(true);
    try {
      if (running) {
        await api.disableMobileService();
        setRunning(false); setConnectionInfo(null);
        setPairedDevices([]);
        setPairingState('idle');
      } else {
        const info = await api.enableMobileService();
        setRunning(true);
        setConnectionInfo({ local_ip: info.local_ip, port: info.port });
      }
    } catch (error) {
      console.error('Toggle mobile service failed:', error);
    }
    setToggleLoading(false);
  };

  const handleStartPairing = async () => {
    try {
      await api.startPairingMode();
      setPairingState('broadcasting');
    } catch (error) {
      console.error('Start pairing failed:', error);
    }
  };

  const handleStopPairing = async () => {
    if (codeTimerRef.current) {
      clearInterval(codeTimerRef.current);
      codeTimerRef.current = null;
    }
    // 调用 cancel API 清除后端 _pending 状态，防止 409
    try { await api.cancelPairing(); } catch {}
    try { await api.stopPairingMode(); } catch {}
    setPairingState('idle');
    setPendingDeviceName('');
    setPairingCode('');
    setCodeCountdown(0);
  };

  const handleConfirmPairing = async () => {
    try {
      const res = await api.confirmPairing();
      setPairingCode(res.pairing_code);
      pairedCountRef.current = pairedDevices.length;
      setPairingState('show_code');
      setCodeCountdown(120);
      // 存 timer ref，以便取消配对时能清除
      codeTimerRef.current = setInterval(() => {
        setCodeCountdown(prev => {
          if (prev <= 1) {
            if (codeTimerRef.current) {
              clearInterval(codeTimerRef.current);
              codeTimerRef.current = null;
            }
            setPairingState('idle');
            handleStopPairing();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (error) {
      console.error('Confirm pairing failed:', error);
    }
  };

  const handleRejectPairing = async () => {
    try { await api.rejectPairing(); } catch {}
    setPairingState('idle');
    setPendingDeviceName('');
  };

  // 确认撤销单个设备
  const handleRevokeConfirm = async () => {
    if (!revokeTarget) return;
    setRevokeLoading(true);
    try {
      const res = await api.revokeMobileDevice(revokeTarget.token);
      if (res.status === 'revoked') {
        setRevokeTarget(null);
        await loadStatus();
      } else {
        console.error('Revoke device failed:', res);
      }
    } catch (error) {
      console.error('Revoke device failed:', error);
    }
    setRevokeLoading(false);
  };

  // 确认撤销全部设备
  const handleRevokeAllConfirm = async () => {
    setRevokeLoading(true);
    try {
      await api.revokeAllMobileDevices();
      await loadStatus();
    } catch (error) {
      console.error('Revoke all devices failed:', error);
    }
    setRevokeLoading(false);
    setRevokeAllConfirm(false);
  };

  const handleClose = async () => {
    if (pairingState !== 'idle') {
      await handleStopPairing();
    }
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('mobileAccess.title')} size="md">
      <div className="space-y-5">
        {/* 移动接入服务总开关 */}
        <div className="flex items-center justify-between p-4 bg-page rounded-lg border border-border">
          <div>
            <p className="text-sm font-medium">{t('mobileAccess.service')}</p>
            <p className="text-xs text-text-tertiary">
              {running ? t('mobileAccess.running') : t('mobileAccess.stopped')}
              {running && pairedDevices.length > 0 && ` · ${pairedDevices.length} 台设备已配对`}
            </p>
          </div>
          <button
            onClick={handleToggle}
            disabled={toggleLoading}
            className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${running ? 'bg-primary' : 'bg-border'} ${toggleLoading ? 'opacity-50' : ''}`}
          >
            {toggleLoading ? (
              <span className="absolute inset-0 flex items-center justify-center">
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              </span>
            ) : (
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform duration-200 ${running ? 'translate-x-6' : ''}`} />
            )}
          </button>
        </div>
        <p className="text-xs text-text-tertiary -mt-3 leading-relaxed">
          {t('mobileAccess.serviceDesc')}
        </p>

        {/* 配对模式按钮 */}
        {running && pairingState === 'idle' && (
          <div>
            <p className="text-sm font-medium mb-2">{t('pairing.title')}</p>
            <p className="text-xs text-text-tertiary mb-2 leading-relaxed">{t('pairing.description')}</p>
            <button
              onClick={handleStartPairing}
              className="w-full px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover active:scale-[0.98] transition-all"
            >
              {t('pairing.start')}
            </button>
          </div>
        )}

        {pairingState === 'broadcasting' && (
          <div className="p-4 bg-page rounded-lg border border-primary space-y-3">
            <p className="text-sm font-medium">{t('pairing.broadcasting')}</p>
            {connectionInfo && (
              <p className="text-xs font-mono text-text-secondary bg-card px-2 py-1 rounded border border-border">
                {connectionInfo.local_ip}:{connectionInfo.port}
              </p>
            )}
            <p className="text-xs text-text-tertiary">{t('pairing.deviceFound')}</p>
            <button
              onClick={handleStopPairing}
              className="w-full px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-text-secondary active:scale-[0.98] transition-all"
            >
              {t('pairing.stop')}
            </button>
          </div>
        )}

        {pairingState === 'request_received' && (
          <div className="p-4 bg-page rounded-lg border-2 border-primary">
            <p className="text-sm font-medium mb-1">{t('pairing.requestFrom', { device: pendingDeviceName })}</p>
            <p className="text-lg font-semibold text-primary mb-3">{pendingDeviceName}</p>
            <div className="flex gap-2">
              <button
                onClick={handleRejectPairing}
                className="flex-1 px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-red-500 hover:text-red-500 active:scale-[0.98] transition-all"
              >
                {t('pairing.rejectPairing')}
              </button>
              <button
                onClick={handleConfirmPairing}
                className="flex-1 px-3 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover active:scale-[0.98] transition-all"
              >
                {t('pairing.confirmPairing')}
              </button>
            </div>
          </div>
        )}

        {pairingState === 'show_code' && (
          <div className="p-4 bg-page rounded-lg border-2 border-green-500 space-y-2">
            <p className="text-sm font-medium mb-1">{t('pairing.pairingCode')}</p>
            <p className="text-3xl font-bold text-center text-primary mb-2 tracking-widest">{pairingCode}</p>
            <p className="text-xs text-text-tertiary text-center mb-1">{t('pairing.enterCodeOnPhone')}</p>
            <p className="text-xs text-text-tertiary text-center">{t('pairing.codeExpiresIn', { seconds: codeCountdown })}</p>
            <button
              onClick={handleStopPairing}
              className="w-full mt-2 px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-red-400 hover:text-red-400 active:scale-[0.98] transition-all"
            >
              取消配对
            </button>
          </div>
        )}

        {pairingState === 'success' && (
          <div className="p-4 bg-page rounded-lg border-2 border-green-500 dark:bg-green-900/20">
            <p className="text-lg text-center mb-1">✅ {t('pairing.success')}</p>
            <p className="text-xs text-text-tertiary text-center">{t('pairing.successDesc')}</p>
          </div>
        )}

        {/* 已配对设备列表 */}
        <div>
          <p className="text-sm font-medium mb-2">{t('mobileAccess.pairedDevices')}</p>
          {pairedDevices.length > 0 ? (
            <div className="space-y-2">
              {pairedDevices.map(d => (
                <div key={d.token} className="flex items-center justify-between p-3 bg-page rounded-lg border border-border group">
                  <div>
                    <p className="text-sm font-medium">{d.device_name}</p>
                    <p className="text-xs text-text-tertiary">{d.paired_at}</p>
                  </div>
                  <button
                    onClick={() => setRevokeTarget(d)}
                    className="text-xs text-text-secondary hover:text-red-500 hover:bg-red-500/10 active:scale-95 transition-all px-2.5 py-1 rounded border border-transparent hover:border-red-500/30 cursor-pointer"
                  >
                    {t('mobileAccess.revoke')}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-tertiary py-2">{t('mobileAccess.noDevices')}</p>
          )}
          {pairedDevices.length > 0 && (
            <button
              onClick={() => setRevokeAllConfirm(true)}
              className="text-xs text-text-secondary hover:text-red-500 hover:bg-red-500/10 active:scale-95 transition-all mt-2 px-2.5 py-1 rounded border border-transparent hover:border-red-500/30"
            >
              {t('mobileAccess.revokeAll')}
            </button>
          )}
        </div>
      </div>

      {/* 撤销单设备确认弹窗 - 用 Portal 渲染到 body，避开 Modal 层叠上下文 */}
      {typeof document !== 'undefined' && revokeTarget ? createPortal(
        <ConfirmDialog
          isOpen={!!revokeTarget}
          title={t('mobileAccess.revokeConfirmTitle')}
          desc={`"${revokeTarget.device_name}" ${t('mobileAccess.revokeConfirmDesc')}`}
          confirmLabel="撤销"
          onConfirm={handleRevokeConfirm}
          onCancel={() => setRevokeTarget(null)}
          loading={revokeLoading}
          danger
        />,
        document.body
      ) : null}

      {/* 撤销全部确认弹窗 - 用 Portal 渲染到 body */}
      {typeof document !== 'undefined' && revokeAllConfirm ? createPortal(
        <ConfirmDialog
          isOpen={revokeAllConfirm}
          title={t('mobileAccess.revokeAllConfirmTitle')}
          desc={t('mobileAccess.revokeAllConfirmDesc')}
          confirmLabel="全部撤销"
          onConfirm={handleRevokeAllConfirm}
          onCancel={() => setRevokeAllConfirm(false)}
          loading={revokeLoading}
          danger
        />,
        document.body
      ) : null}
    </Modal>
  );
}
