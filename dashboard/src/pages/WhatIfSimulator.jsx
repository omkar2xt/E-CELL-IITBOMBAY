// pages/WhatIfSimulator.jsx — StorePulse AI
// Interactive What-If Floor Plan Layout Editor
// Developer: Omkar Gurav
// Uses SVG + React state for drag-and-drop without external DnD libraries
import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Save, Trash2, RotateCcw, Copy, Info, Plus, Layout,
  Grid, Move, Maximize2
} from 'lucide-react';

const API = 'http://localhost:8000';

const ELEMENT_TYPES = [
  { type: 'shelf',    label: 'Shelf',     color: '#6366f1', bg: 'rgba(99,102,241,0.15)',  icon: '🗄' },
  { type: 'checkout', label: 'Checkout',  color: '#10b981', bg: 'rgba(16,185,129,0.15)',  icon: '🛒' },
  { type: 'display',  label: 'Display',   color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)',  icon: '📦' },
  { type: 'entrance', label: 'Entrance',  color: '#f59e0b', bg: 'rgba(245,158,11,0.15)',  icon: '🚪' },
  { type: 'exit',     label: 'Exit',      color: '#06b6d4', bg: 'rgba(6,182,212,0.15)',   icon: '🚪' },
  { type: 'obstacle', label: 'Obstacle',  color: '#ef4444', bg: 'rgba(239,68,68,0.15)',   icon: '🚧' },
];

const GRID_SIZE = 40;   // px — snap grid
const CANVAS_W = 800;
const CANVAS_H = 500;

function snapToGrid(v) { return Math.round(v / GRID_SIZE) * GRID_SIZE; }

function makeId() { return `el_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`; }

const DEFAULT_ELEMENTS = [
  { id: 's1', element_type: 'shelf',    x: 200, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf A' },
  { id: 's2', element_type: 'shelf',    x: 320, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf B' },
  { id: 's3', element_type: 'shelf',    x: 440, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf C' },
  { id: 's4', element_type: 'shelf',    x: 560, y: 40,  width: 80, height: 160, rotation: 0, label: 'Shelf D' },
  { id: 's5', element_type: 'shelf',    x: 200, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf E' },
  { id: 's6', element_type: 'shelf',    x: 320, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf F' },
  { id: 's7', element_type: 'shelf',    x: 440, y: 280, width: 80, height: 160, rotation: 0, label: 'Shelf G' },
  { id: 'c1', element_type: 'checkout', x: 40,  y: 40,  width: 120, height: 160, rotation: 0, label: 'Checkout' },
  { id: 'e1', element_type: 'entrance', x: 0,   y: 380, width: 80,  height: 80, rotation: 0,  label: 'Entrance' },
  { id: 'd1', element_type: 'display',  x: 300, y: 120, width: 60,  height: 100, rotation: 0, label: 'Promo' },
];

export default function WhatIfSimulator() {
  const [elements, setElements] = useState(DEFAULT_ELEMENTS);
  const [selectedId, setSelectedId] = useState(null);
  const [activeType, setActiveType] = useState('shelf');
  const [mode, setMode] = useState('select'); // 'select' | 'add'
  const [layoutName, setLayoutName] = useState('Proposed Layout 1');
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [layouts, setLayouts] = useState([]);
  const [showLayouts, setShowLayouts] = useState(false);

  const svgRef = useRef(null);
  const dragging = useRef(null);   // { id, startX, startY, elX, elY }
  const resizing = useRef(null);   // { id, startX, startY, w0, h0 }

  // Load layouts from backend on mount
  useEffect(() => {
    fetchLayouts();
  }, []);

  const fetchLayouts = async () => {
    try {
      const res = await fetch(`${API}/api/layouts/`);
      const json = await res.json();
      setLayouts(json.layouts || []);
    } catch { }
  };

  // ── Canvas event handlers ──────────────────────────────────────────

  const getSVGCoords = (e) => {
    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const handleCanvasClick = (e) => {
    if (mode !== 'add') return;
    const { x, y } = getSVGCoords(e);
    const typeInfo = ELEMENT_TYPES.find(t => t.type === activeType);
    const newEl = {
      id: makeId(),
      element_type: activeType,
      x: snapToGrid(x - 40),
      y: snapToGrid(y - 40),
      width: activeType === 'entrance' || activeType === 'exit' ? 80 : activeType === 'checkout' ? 120 : 80,
      height: activeType === 'entrance' || activeType === 'exit' ? 80 : 160,
      rotation: 0,
      label: typeInfo?.label || activeType,
    };
    setElements(prev => [...prev, newEl]);
    setSelectedId(newEl.id);
    setMode('select');
  };

  const handleElMouseDown = (e, id) => {
    e.stopPropagation();
    if (mode !== 'select') return;
    setSelectedId(id);
    const { x, y } = getSVGCoords(e);
    const el = elements.find(el => el.id === id);
    dragging.current = { id, startX: x, startY: y, elX: el.x, elY: el.y };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleResizeMouseDown = (e, id) => {
    e.stopPropagation();
    const { x, y } = getSVGCoords(e);
    const el = elements.find(el => el.id === id);
    resizing.current = { id, startX: x, startY: y, w0: el.width, h0: el.height };
    window.addEventListener('mousemove', handleResizeMove);
    window.addEventListener('mouseup', handleResizeUp);
  };

  const handleMouseMove = useCallback((e) => {
    if (!dragging.current) return;
    const { x, y } = getSVGCoords(e);
    const dx = x - dragging.current.startX;
    const dy = y - dragging.current.startY;
    const nx = snapToGrid(dragging.current.elX + dx);
    const ny = snapToGrid(dragging.current.elY + dy);
    setElements(prev => prev.map(el =>
      el.id === dragging.current.id ? { ...el, x: Math.max(0, nx), y: Math.max(0, ny) } : el
    ));
  }, []);

  const handleMouseUp = useCallback(() => {
    dragging.current = null;
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove]);

  const handleResizeMove = useCallback((e) => {
    if (!resizing.current) return;
    const { x, y } = getSVGCoords(e);
    const dx = x - resizing.current.startX;
    const dy = y - resizing.current.startY;
    const nw = snapToGrid(Math.max(GRID_SIZE, resizing.current.w0 + dx));
    const nh = snapToGrid(Math.max(GRID_SIZE, resizing.current.h0 + dy));
    setElements(prev => prev.map(el =>
      el.id === resizing.current.id ? { ...el, width: nw, height: nh } : el
    ));
  }, []);

  const handleResizeUp = useCallback(() => {
    resizing.current = null;
    window.removeEventListener('mousemove', handleResizeMove);
    window.removeEventListener('mouseup', handleResizeUp);
  }, [handleResizeMove]);

  // ── Actions ────────────────────────────────────────────────────────

  const deleteSelected = () => {
    if (!selectedId) return;
    setElements(prev => prev.filter(e => e.id !== selectedId));
    setSelectedId(null);
  };

  const duplicateSelected = () => {
    const el = elements.find(e => e.id === selectedId);
    if (!el) return;
    const newEl = { ...el, id: makeId(), x: el.x + GRID_SIZE, y: el.y + GRID_SIZE };
    setElements(prev => [...prev, newEl]);
    setSelectedId(newEl.id);
  };

  const resetToDefault = () => {
    if (!window.confirm('Reset to default layout? All changes will be lost.')) return;
    setElements(DEFAULT_ELEMENTS);
    setSelectedId(null);
  };

  const saveLayout = async (isBaseline = false) => {
    setSaving(true);
    try {
      const body = {
        name: isBaseline ? 'Baseline Layout' : layoutName,
        description: isBaseline ? 'Baseline layout saved from editor' : `Proposed layout: ${layoutName}`,
        elements: elements.map(e => ({
          ...e,
          x: e.x > 1 ? Number((e.x / CANVAS_W).toFixed(4)) : e.x,
          y: e.y > 1 ? Number((e.y / CANVAS_H).toFixed(4)) : e.y,
          width: e.width > 1 ? Number((e.width / CANVAS_W).toFixed(4)) : e.width,
          height: e.height > 1 ? Number((e.height / CANVAS_H).toFixed(4)) : e.height,
        })),
        zones: [],
        is_baseline: isBaseline,
        id: isBaseline ? 'baseline' : undefined,
      };
      const res = await fetch(`${API}/api/layouts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setSavedMsg(isBaseline ? '✓ Saved as baseline' : '✓ Layout saved');
        fetchLayouts();
        setTimeout(() => setSavedMsg(''), 3000);
      }
    } catch (e) {
      setSavedMsg('⚠ Save failed (backend offline)');
      setTimeout(() => setSavedMsg(''), 3000);
    } finally {
      setSaving(false);
    }
  };

  const loadLayout = async (id) => {
    try {
      const res = await fetch(`${API}/api/layouts/${id}`);
      const json = await res.json();
      const layout = json.layout;
      if (layout?.elements) {
        // Scale from ratio to pixels
        const els = layout.elements.map(e => ({
          ...e,
          x: e.x <= 1.0 ? Math.round(e.x * CANVAS_W) : e.x,
          y: e.y <= 1.0 ? Math.round(e.y * CANVAS_H) : e.y,
          width: e.width <= 1.0 ? Math.round(e.width * CANVAS_W) : e.width,
          height: e.height <= 1.0 ? Math.round(e.height * CANVAS_H) : e.height,
        }));
        setElements(els);
        setLayoutName(layout.name);
        setShowLayouts(false);
        setSavedMsg(`✓ Loaded: ${layout.name}`);
        setTimeout(() => setSavedMsg(''), 3000);
      }
    } catch { }
  };

  const selectedEl = elements.find(e => e.id === selectedId);

  return (
    <div className="fade-in">
      <div className="disclaimer-box" style={{ marginBottom: 16 }}>
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>Heuristic simulation only.</strong> Moving virtual shelves estimates geometric metrics
          (walking distance, space utilization) — it does NOT predict real customer behavior.
          All outputs are labeled as estimates. Field validation required before operational decisions.
        </span>
      </div>

      <div className="simulator-layout" style={{ gridTemplateColumns: '260px 1fr' }}>
        {/* Left panel */}
        <div className="simulator-panel">
          {/* Mode */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8 }}>
              Mode
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className={`sim-btn${mode === 'select' ? ' active' : ''}`} onClick={() => setMode('select')}>
                <Move size={13} /> Select
              </button>
              <button className={`sim-btn${mode === 'add' ? ' active' : ''}`} onClick={() => setMode('add')}>
                <Plus size={13} /> Add
              </button>
            </div>
          </div>

          {/* Element types */}
          {mode === 'add' && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8 }}>
                Element Type
              </div>
              <div className="element-type-grid">
                {ELEMENT_TYPES.map(t => (
                  <button
                    key={t.type}
                    className={`element-type-btn${activeType === t.type ? ' active' : ''}`}
                    onClick={() => setActiveType(t.type)}
                  >
                    <span style={{ fontSize: 18 }}>{t.icon}</span>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Selected element */}
          {selectedEl && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 8 }}>
                Selected: {selectedEl.label}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
                {['x','y','width','height'].map(field => (
                  <div key={field}>
                    <div style={{ color: 'var(--text-muted)', marginBottom: 3 }}>{field}</div>
                    <input
                      type="number"
                      className="input-field"
                      style={{ width: '100%' }}
                      value={selectedEl[field]}
                      onChange={e => {
                        const val = parseInt(e.target.value) || 0;
                        setElements(prev => prev.map(el =>
                          el.id === selectedId ? { ...el, [field]: snapToGrid(val) } : el
                        ));
                      }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 3 }}>Label</div>
                <input
                  type="text"
                  className="input-field"
                  style={{ width: '100%' }}
                  value={selectedEl.label}
                  onChange={e => {
                    setElements(prev => prev.map(el =>
                      el.id === selectedId ? { ...el, label: e.target.value } : el
                    ));
                  }}
                />
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                <button className="sim-btn" style={{ flex: 1 }} onClick={duplicateSelected}>
                  <Copy size={12} /> Clone
                </button>
                <button className="sim-btn danger" style={{ flex: 1 }} onClick={deleteSelected}>
                  <Trash2 size={12} /> Delete
                </button>
              </div>
            </div>
          )}

          {/* Layout name */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Layout Name</div>
            <input
              type="text"
              className="input-field"
              style={{ width: '100%' }}
              value={layoutName}
              onChange={e => setLayoutName(e.target.value)}
            />
          </div>

          {/* Save actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button className="sim-btn primary" onClick={() => saveLayout(false)} disabled={saving}>
              <Save size={13} /> {saving ? 'Saving...' : 'Save Proposed Layout'}
            </button>
            <button className="sim-btn success" onClick={() => saveLayout(true)} disabled={saving}>
              <Save size={13} /> Save as Baseline
            </button>
            <button className="sim-btn" onClick={() => setShowLayouts(s => !s)}>
              <Layout size={13} /> {showLayouts ? 'Hide' : 'Browse'} Layouts
            </button>
            <button className="sim-btn" onClick={resetToDefault}>
              <RotateCcw size={13} /> Reset to Default
            </button>
          </div>

          {savedMsg && (
            <div style={{ marginTop: 10, fontSize: 12, color: savedMsg.startsWith('✓') ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
              {savedMsg}
            </div>
          )}

          {/* Layouts browser */}
          {showLayouts && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8 }}>SAVED LAYOUTS</div>
              {layouts.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No saved layouts</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {layouts.map(l => (
                    <button key={l.id} className="sim-btn" style={{ textAlign: 'left', justifyContent: 'flex-start' }}
                      onClick={() => loadLayout(l.id)}>
                      <Layout size={12} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 150 }}>{l.name}</span>
                      {l.is_baseline && <span style={{ fontSize: 10, marginLeft: 'auto', color: '#10b981' }}>BASE</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          <div style={{ marginTop: 16, padding: 10, background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Current Layout Stats</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              Elements: <strong>{elements.length}</strong><br />
              Shelves: <strong>{elements.filter(e => e.element_type === 'shelf').length}</strong><br />
              Checkouts: <strong>{elements.filter(e => e.element_type === 'checkout').length}</strong><br />
              Area used: <strong>{Math.round(elements.reduce((s, e) => s + e.width * e.height, 0) / (CANVAS_W * CANVAS_H) * 100)}%</strong>
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="simulator-canvas-wrapper">
          <div className="simulator-toolbar">
            <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 4 }}>
              Mode: <strong style={{ color: mode === 'add' ? '#6366f1' : 'var(--text-secondary)' }}>{mode === 'add' ? `Add ${activeType}` : 'Select & Move'}</strong>
            </span>
            {mode === 'add' && (
              <span style={{ fontSize: 11, color: 'var(--brand-accent)' }}>
                Click on canvas to place element
              </span>
            )}
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
              Grid: {GRID_SIZE}px · Snapping ON
            </span>
          </div>

          <div style={{ flex: 1, overflow: 'auto' }}>
            <svg
              ref={svgRef}
              viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
              style={{
                width: '100%',
                minHeight: 400,
                display: 'block',
                cursor: mode === 'add' ? 'crosshair' : 'default',
                background: `
                  linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
                backgroundSize: `${GRID_SIZE}px ${GRID_SIZE}px`,
                backgroundColor: '#070c1a',
              }}
              onClick={handleCanvasClick}
            >
              {/* Store border */}
              <rect x="1" y="1" width={CANVAS_W-2} height={CANVAS_H-2}
                fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="2" rx="4"
                strokeDasharray="8 4" />

              {/* Elements */}
              {elements.map(el => {
                const typeInfo = ELEMENT_TYPES.find(t => t.type === el.element_type) || ELEMENT_TYPES[0];
                const isSelected = el.id === selectedId;
                return (
                  <g key={el.id}
                    transform={`translate(${el.x},${el.y}) rotate(${el.rotation || 0},${el.width/2},${el.height/2})`}
                    onMouseDown={e => handleElMouseDown(e, el.id)}
                    style={{ cursor: 'move', userSelect: 'none' }}
                  >
                    <rect
                      width={el.width} height={el.height}
                      rx="4"
                      fill={typeInfo.bg}
                      stroke={isSelected ? '#06b6d4' : typeInfo.color}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      filter={isSelected ? 'drop-shadow(0 0 8px rgba(6,182,212,0.5))' : undefined}
                    />
                    <text
                      x={el.width / 2} y={el.height / 2 - 6}
                      textAnchor="middle"
                      fill="white"
                      fontSize="16"
                      style={{ pointerEvents: 'none' }}
                    >
                      {typeInfo.icon}
                    </text>
                    <text
                      x={el.width / 2} y={el.height / 2 + 12}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.8)"
                      fontSize={Math.max(8, Math.min(12, el.width / 7))}
                      style={{ pointerEvents: 'none' }}
                    >
                      {el.label}
                    </text>
                    {/* Resize handle */}
                    {isSelected && (
                      <rect
                        x={el.width - 8} y={el.height - 8}
                        width={10} height={10}
                        rx="2"
                        fill="#06b6d4"
                        style={{ cursor: 'se-resize' }}
                        onMouseDown={e => { e.stopPropagation(); handleResizeMouseDown(e, el.id); }}
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Legend */}
          <div style={{ padding: '8px 16px', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {ELEMENT_TYPES.map(t => (
              <div key={t.type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: t.color, opacity: 0.7 }} />
                {t.label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
