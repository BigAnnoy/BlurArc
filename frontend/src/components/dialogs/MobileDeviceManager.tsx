import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../common/Modal';
import { useI18n } from '../../contexts/I18nContext';
import { api } from '../../services/api';

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
  const [connectionInfo, setConnectionInfo] = useState<{ local_ip: string; port: number } | null>(null);
  const [pairedDevices, setPairedDevices] = useState<PairedDevice[]>([]);
  const [qrUrl, setQrUrl] = useState('');
  const [pendingRequest, setPendingRequest] = useState<{ device_name: string; pairing_code: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [pairingState, setPairingState] = useState<'idle' | 'broadcasting' | 'request_received' | 'show_code'>('idle');
  const [pendingDeviceName, setPendingDeviceName] = useState('');
  const [pairingCode, setPairingCode] = useState('');
  const [codeCountdown, setCodeCountdown] = useState(0);

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

  useEffect(() => {
    if (!isOpen || !running) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.getMobilePendingRequest();
        if (res.hasPending) setPendingRequest({ device_name: res.device_name!, pairing_code: res.pairing_code! });
        else setPendingRequest(null);
      } catch {}
    }, 2000);
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
    setLoading(true);
    try {
      if (running) {
        await api.disableMobileService();
        setRunning(false); setConnectionInfo(null); setQrUrl('');
        setPairedDevices([]); setPendingRequest(null);
      } else {
        const info = await api.enableMobileService();
        setRunning(true);
        setConnectionInfo({ local_ip: info.local_ip, port: info.port });
        setQrUrl(api.getMobileQr());
      }
    } catch {}
    setLoading(false);
  };

  const handleAccept = async () => {
    if (!pendingRequest) return;
    await api.confirmMobilePairing(pendingRequest.pairing_code, 'accept');
    setPendingRequest(null);
    loadStatus();
  };

  const handleReject = async () => {
    if (!pendingRequest) return;
    await api.confirmMobilePairing(pendingRequest.pairing_code, 'reject');
    setPendingRequest(null);
  };

  const handleStartPairing = async () => {
    try {
      await api.startPairingMode();
      setPairingState('broadcasting');
    } catch {}
  };

  const handleStopPairing = async () => {
    try { await api.stopPairingMode(); } catch {}
    setPairingState('idle');
    setPendingDeviceName('');
    setPairingCode('');
  };

  const handleConfirmPairing = async () => {
    try {
      const res = await api.confirmPairing();
      setPairingCode(res.pairing_code);
      setPairingState('show_code');
      setCodeCountdown(120);
      // 倒计时
      const timer = setInterval(() => {
        setCodeCountdown(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            setPairingState('idle');
            handleStopPairing();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch {}
  };

  const handleRejectPairing = async () => {
    try { await api.rejectPairing(); } catch {}
    setPairingState('idle');
    setPendingDeviceName('');
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('mobileAccess.title')} size="md">
      <div className="space-y-5">
        <div className="flex items-center justify-between p-4 bg-page rounded-lg border border-border">
          <div>
            <p className="text-sm font-medium">{t('mobileAccess.service')}</p>
            <p className="text-xs text-text-tertiary">{running ? t('mobileAccess.running') : t('mobileAccess.stopped')}</p>
          </div>
          <button onClick={handleToggle} disabled={loading}
            className={`relative w-12 h-6 rounded-full transition-colors ${running ? 'bg-primary' : 'bg-border'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${running ? 'translate-x-6' : ''}`} />
          </button>
        </div>

        {running && connectionInfo && (
          <div className="p-3 bg-page rounded-lg border border-border">
            <p className="text-xs text-text-tertiary mb-1">{t('mobileAccess.connectionInfo')}</p>
            <p className="text-sm font-mono text-text-primary">{connectionInfo.local_ip}:{connectionInfo.port}</p>
          </div>
        )}

        {running && (
          <div>
            <p className="text-sm font-medium mb-2">{t('mobileAccess.newDevice')}</p>
            <div className="flex items-start gap-4 p-4 bg-page rounded-lg border border-border">
              {qrUrl && <img src={qrUrl} alt="QR" className="w-36 h-36 rounded-md border border-border" />}
              <p className="text-xs text-text-tertiary">{t('mobileAccess.scanQrHint')}</p>
            </div>
          </div>
        )}

        {running && pairingState === 'idle' && (
          <div>
            <p className="text-sm font-medium mb-2">{t('pairing.title')}</p>
            <button onClick={handleStartPairing}
              className="w-full px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover">
              {t('pairing.start')}
            </button>
          </div>
        )}

        {pairingState === 'broadcasting' && (
          <div className="p-4 bg-page rounded-lg border border-primary">
            <p className="text-sm font-medium mb-1">{t('pairing.broadcasting')}</p>
            <p className="text-xs text-text-tertiary mb-3">{t('pairing.deviceFound')}</p>
            <button onClick={handleStopPairing}
              className="w-full px-3 py-2 bg-card border border-border rounded-md text-sm">
              {t('pairing.stop')}
            </button>
          </div>
        )}

        {pairingState === 'request_received' && (
          <div className="p-4 bg-page rounded-lg border-2 border-primary">
            <p className="text-sm font-medium mb-1">{t('pairing.requestFrom', { device: pendingDeviceName })}</p>
            <p className="text-lg font-semibold text-primary mb-3">{pendingDeviceName}</p>
            <div className="flex gap-2">
              <button onClick={handleRejectPairing} className="flex-1 px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-red-500">{t('pairing.rejectPairing')}</button>
              <button onClick={handleConfirmPairing} className="flex-1 px-3 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover">{t('pairing.confirmPairing')}</button>
            </div>
          </div>
        )}

        {pairingState === 'show_code' && (
          <div className="p-4 bg-page rounded-lg border-2 border-green-500">
            <p className="text-sm font-medium mb-1">{t('pairing.pairingCode')}</p>
            <p className="text-3xl font-bold text-center text-primary mb-2">{pairingCode}</p>
            <p className="text-xs text-text-tertiary text-center mb-1">{t('pairing.enterCodeOnPhone')}</p>
            <p className="text-xs text-text-tertiary text-center">{t('pairing.codeExpiresIn', { seconds: codeCountdown })}</p>
          </div>
        )}

        {pendingRequest && (
          <div className="p-4 bg-page rounded-lg border-2 border-primary">
            <p className="text-sm font-medium mb-1">{t('mobileAccess.pairRequest')}</p>
            <p className="text-lg font-semibold text-primary mb-3">{pendingRequest.device_name}</p>
            <div className="flex gap-2">
              <button onClick={handleReject} className="flex-1 px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-red-500">{t('common.cancel')}</button>
              <button onClick={handleAccept} className="flex-1 px-3 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover">{t('common.confirm')}</button>
            </div>
          </div>
        )}

        {pairedDevices.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">{t('mobileAccess.pairedDevices')}</p>
              <button onClick={async () => { await api.revokeAllMobileDevices(); loadStatus(); }} className="text-xs text-red-500">{t('mobileAccess.revokeAll')}</button>
            </div>
            <div className="space-y-2">
              {pairedDevices.map(d => (
                <div key={d.token} className="flex items-center justify-between p-3 bg-page rounded-lg border border-border">
                  <div>
                    <p className="text-sm font-medium">{d.device_name}</p>
                    <p className="text-xs text-text-tertiary">{d.paired_at}</p>
                  </div>
                  <button onClick={async () => { await api.revokeMobileDevice(d.token); loadStatus(); }} className="text-xs text-red-500">{t('mobileAccess.revoke')}</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
