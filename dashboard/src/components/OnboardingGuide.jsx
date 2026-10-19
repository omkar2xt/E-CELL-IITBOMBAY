// components/OnboardingGuide.jsx — StorePulse AI
// Developer: Omkar Gurav
// First-time & reload onboarding walkthrough with source selection and feature guide

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X, ChevronRight, ChevronLeft, Sparkles, Video, Play,
  Radio, MapPin, ShoppingCart, Flame, Layout, Settings, Check, AlertCircle, ArrowRight
} from 'lucide-react';
import logoEmblem from '../assets/logo-emblem.png';
import { API_BASE } from '../config';

export default function OnboardingGuide({ isOpen, onClose, telemetryData }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [switching, setSwitching] = useState(false);
  const [switchError, setSwitchError] = useState(null);
  const [activeSourceMode, setActiveSourceMode] = useState(telemetryData?.is_demo ? 'demo' : 'video');
  const navigate = useNavigate();

  // Keep active source mode synced with telemetry
  useEffect(() => {
    if (telemetryData?.is_demo !== undefined) {
      setActiveSourceMode(telemetryData.is_demo ? 'demo' : 'video');
    }
  }, [telemetryData?.is_demo]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSourceSwitch = async (mode) => {
    try {
      setSwitching(true);
      setSwitchError(null);
      const res = await fetch(`${API_BASE}/api/pipeline/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: mode === 'demo' ? 'demo' : 'video' }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveSourceMode(data.is_demo ? 'demo' : 'video');
      } else {
        setSwitchError('Failed to switch video source. Check backend server.');
      }
    } catch (err) {
      setSwitchError('Connection error contacting backend API.');
    } finally {
      setSwitching(false);
    }
  };

  const handleFinish = () => {
    onClose();
    navigate('/');
  };

  const goToSettings = () => {
    navigate('/settings');
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 10000,
      background: 'rgba(5, 10, 20, 0.82)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 20,
        width: '100%',
        maxWidth: 580,
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 30px rgba(56, 189, 248, 0.1)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        animation: 'fadeIn 0.25s ease'
      }}>
        {/* Progress Bar */}
        <div style={{ width: '100%', height: 4, background: 'rgba(255, 255, 255, 0.05)' }}>
          <div style={{
            width: `${(currentStep / 4) * 100}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #6366f1, #38bdf8)',
            transition: 'width 0.3s ease'
          }} />
        </div>

        {/* Modal Header */}
        <div style={{
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src={logoEmblem} alt="StorePulse AI" style={{ width: 28, height: 28, objectFit: 'contain' }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: 0.5 }}>
              STOREPULSE AI ONBOARDING
            </span>
            <span style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 12,
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#818cf8',
              fontWeight: 600
            }}>
              Step {currentStep} of 4
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 6
            }}
            title="Close guide">
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '24px', minHeight: 280, display: 'flex', flexDirection: 'column' }}>
          {/* ── STEP 1: WELCOME ── */}
          {currentStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 14 }}>
              <div style={{
                width: 68,
                height: 68,
                borderRadius: 18,
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 10,
                boxShadow: '0 0 30px rgba(56, 189, 248, 0.2)'
              }}>
                <img src={logoEmblem} alt="Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>

              <h2 style={{ fontSize: 22, fontWeight: 700, margin: '6px 0 0', color: 'var(--text-primary)' }}>
                Welcome to StorePulse AI
              </h2>

              <p style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: 'var(--text-secondary)',
                maxWidth: 460,
                margin: 0
              }}>
                Monitor store activity, understand customer movement, and discover bottlenecks through computer vision analytics.
              </p>

              <div style={{
                marginTop: 10,
                padding: '12px 16px',
                borderRadius: 12,
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                width: '100%',
                display: 'flex',
                justifyContent: 'space-around',
                fontSize: 12,
                color: 'var(--text-muted)'
              }}>
                <span>✓ YOLO11 Person Tracking</span>
                <span>✓ Zone Congestion Alarms</span>
                <span>✓ What-If Simulator</span>
              </div>
            </div>
          )}

          {/* ── STEP 2: CHOOSE VIDEO SOURCE ── */}
          {currentStep === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Start with Demo or CCTV Video
              </h2>

              <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                Select an operational mode to begin. You can switch modes at any time.
              </p>

              {/* Mode Selection Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 4 }}>
                {/* Demo Card */}
                <div
                  onClick={() => handleSourceSwitch('demo')}
                  style={{
                    padding: 14,
                    borderRadius: 12,
                    border: `1.5px solid ${activeSourceMode === 'demo' ? '#f59e0b' : 'var(--border-subtle)'}`,
                    background: activeSourceMode === 'demo' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    cursor: switching ? 'wait' : 'pointer',
                    transition: 'all 0.15s ease',
                    position: 'relative'
                  }}>
                  {activeSourceMode === 'demo' && (
                    <span style={{
                      position: 'absolute', top: 10, right: 10,
                      background: '#f59e0b', color: '#000', borderRadius: '50%',
                      width: 18, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      <Check size={12} strokeWidth={3} />
                    </span>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <Play size={18} color="#f59e0b" />
                    <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>Demo Mode</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                    Explore StorePulse AI using its built-in demonstration or simulation.
                  </div>
                </div>

                {/* CCTV Card */}
                <div
                  onClick={() => handleSourceSwitch('video')}
                  style={{
                    padding: 14,
                    borderRadius: 12,
                    border: `1.5px solid ${activeSourceMode === 'video' ? '#38bdf8' : 'var(--border-subtle)'}`,
                    background: activeSourceMode === 'video' ? 'rgba(56, 189, 248, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                    cursor: switching ? 'wait' : 'pointer',
                    transition: 'all 0.15s ease',
                    position: 'relative'
                  }}>
                  {activeSourceMode === 'video' && (
                    <span style={{
                      position: 'absolute', top: 10, right: 10,
                      background: '#38bdf8', color: '#000', borderRadius: '50%',
                      width: 18, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      <Check size={12} strokeWidth={3} />
                    </span>
                  )}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <Video size={18} color="#38bdf8" />
                    <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>CCTV/Video Mode</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                    Analyze a supported video or connected camera source, depending on the application's existing capabilities.
                  </div>
                </div>
              </div>

              {switchError && (
                <div style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  color: '#f87171',
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}>
                  <AlertCircle size={15} /> {switchError}
                </div>
              )}

              {/* Settings Hint */}
              <div style={{
                marginTop: 6,
                padding: '10px 14px',
                borderRadius: 10,
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Settings size={15} color="var(--brand-accent)" />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Need RTSP streams or custom camera inputs?
                  </span>
                </div>
                <button
                  onClick={goToSettings}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--brand-accent)',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}>
                  Settings & Privacy <ArrowRight size={13} />
                </button>
              </div>
            </div>
          )}

          {/* ── STEP 3: IMPORTANT FEATURES ── */}
          {currentStep === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Your Store Insights
              </h2>

              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                Key analytics and simulation modules available on your dashboard:
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(99,102,241,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Radio size={16} color="#818cf8" />
                  </div>
                  <div>
                    <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Live Analytics: </strong>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>View people detection and movement activity.</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(56,189,248,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <MapPin size={16} color="#38bdf8" />
                  </div>
                  <div>
                    <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Zone Analytics: </strong>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Understand activity in different store areas.</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(245,158,11,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <ShoppingCart size={16} color="#f59e0b" />
                  </div>
                  <div>
                    <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Queue & Bottleneck Monitoring: </strong>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Identify queues and potential congestion.</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Flame size={16} color="#ef4444" />
                  </div>
                  <div>
                    <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Heatmaps & Flow Friction: </strong>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Discover busy areas and movement problems.</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 6, background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Layout size={16} color="#10b981" />
                  </div>
                  <div>
                    <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>What-If Simulator: </strong>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Explore possible store-layout improvements.</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 4: FINISH ── */}
          {currentStep === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 16 }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1.5px solid #10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 25px rgba(16, 185, 129, 0.25)'
              }}>
                <Sparkles size={32} color="#10b981" />
              </div>

              <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                You’re Ready to Explore
              </h2>

              <p style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: 'var(--text-secondary)',
                maxWidth: 440,
                margin: 0
              }}>
                Start in Demo Mode to explore the dashboard, or switch to CCTV/Video Mode in Settings & Privacy when your source is ready.
              </p>

              <div style={{
                padding: '12px 18px',
                borderRadius: 12,
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                width: '100%',
                fontSize: 12,
                color: 'var(--text-muted)'
              }}>
                Active Mode: <strong style={{ color: activeSourceMode === 'demo' ? '#f59e0b' : '#38bdf8' }}>
                  {activeSourceMode === 'demo' ? '⚡ DEMO SIMULATION' : '📹 CCTV / VIDEO'}
                </strong>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'rgba(0, 0, 0, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          {/* Left Action: Skip Tour */}
          {currentStep < 4 ? (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: 13,
                cursor: 'pointer',
                padding: '6px 10px',
                fontWeight: 500
              }}>
              Skip Tour
            </button>
          ) : (
            <div />
          )}

          {/* Right Actions: Back and Next / Finish */}
          <div style={{ display: 'flex', gap: 10 }}>
            {currentStep > 1 && (
              <button
                onClick={() => setCurrentStep(prev => prev - 1)}
                className="btn btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 14px', fontSize: 13 }}>
                <ChevronLeft size={16} /> Back
              </button>
            )}

            {currentStep < 4 ? (
              <button
                onClick={() => setCurrentStep(prev => prev + 1)}
                className="btn btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 18px', fontSize: 13 }}>
                Next <ChevronRight size={16} />
              </button>
            ) : (
              <button
                onClick={handleFinish}
                className="btn btn-primary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 22px',
                  fontSize: 13,
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  borderColor: '#10b981'
                }}>
                Start Exploring <Sparkles size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
