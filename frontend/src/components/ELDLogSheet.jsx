import React, { useRef, useEffect } from 'react';

/**
 * ELD Log Sheet Component
 *
 * Renders a FMCSA-compliant Driver's Daily Log grid.
 * Matches the official format from the FMCSA guide:
 * - 24-hour horizontal grid (midnight to midnight)
 * - 4 duty status rows: Off Duty, Sleeper Berth, Driving, On Duty (Not Driving)
 * - Horizontal lines showing time in each status
 * - Vertical lines showing transitions
 * - Remarks section with location changes
 * - Total hours per status (must = 24)
 */

const STATUS_LABELS = ['Off Duty', 'Sleeper Berth', 'Driving', 'On Duty\n(Not Driving)'];
const STATUS_CODES = ['OFF', 'SB', 'D', 'ON'];
const STATUS_COLORS = {
  OFF: '#6b7280',   // gray
  SB: '#7c3aed',    // purple
  D: '#2563eb',     // blue
  ON: '#dc2626',    // red
};

// Grid dimensions
const GRID_LEFT = 120;    // Left margin for labels
const GRID_TOP = 40;      // Top margin for header
const GRID_RIGHT = 50;    // Right margin for totals
const HOUR_WIDTH = 30;    // Width per hour
const ROW_HEIGHT = 35;    // Height per status row
const GRID_WIDTH = HOUR_WIDTH * 24;
const GRID_HEIGHT = ROW_HEIGHT * 4;
const CANVAS_WIDTH = GRID_LEFT + GRID_WIDTH + GRID_RIGHT;
const CANVAS_HEIGHT = GRID_TOP + GRID_HEIGHT + 20;

function ELDLogSheet({ log }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !log) return;
    drawLog(canvasRef.current, log);
  }, [log]);

  if (!log) return null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Log Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-gray-900">
              Driver's Daily Log - Day {log.day_number}
            </h3>
            <p className="text-sm text-gray-500">{log.date}</p>
          </div>
          <div className="text-right text-sm">
            <p className="text-gray-600">Total Miles: <span className="font-medium">{log.total_miles}</span></p>
          </div>
        </div>
      </div>

      {/* Canvas Grid */}
      <div className="p-4 overflow-x-auto">
        <canvas
          ref={canvasRef}
          width={CANVAS_WIDTH * 2}
          height={CANVAS_HEIGHT * 2}
          style={{ width: CANVAS_WIDTH, height: CANVAS_HEIGHT }}
          className="border border-gray-300"
        />
      </div>

      {/* Totals Row */}
      <div className="px-4 pb-2">
        <div className="grid grid-cols-4 gap-2 text-center text-xs">
          <div className="bg-gray-100 rounded p-2">
            <p className="text-gray-500">Off Duty</p>
            <p className="font-bold text-gray-700">{log.total_off_duty?.toFixed(1) || '0.0'} hrs</p>
          </div>
          <div className="bg-purple-50 rounded p-2">
            <p className="text-gray-500">Sleeper</p>
            <p className="font-bold text-purple-700">{log.total_sleeper?.toFixed(1) || '0.0'} hrs</p>
          </div>
          <div className="bg-blue-50 rounded p-2">
            <p className="text-gray-500">Driving</p>
            <p className="font-bold text-blue-700">{log.total_driving?.toFixed(1) || '0.0'} hrs</p>
          </div>
          <div className="bg-red-50 rounded p-2">
            <p className="text-gray-500">On Duty</p>
            <p className="font-bold text-red-700">{log.total_on_duty?.toFixed(1) || '0.0'} hrs</p>
          </div>
        </div>
      </div>

      {/* Remarks */}
      {log.remarks && log.remarks.length > 0 && (
        <div className="px-4 pb-4">
          <h4 className="text-xs font-semibold text-gray-700 mb-1 uppercase">Remarks</h4>
          <div className="bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
            {log.remarks.map((remark, idx) => (
              <p key={idx} className="text-xs text-gray-600 py-0.5">{remark}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Draw the ELD log grid on canvas.
 * Matches FMCSA format: 24-hour grid, 4 status rows, horizontal duty lines.
 */
function drawLog(canvas, log) {
  const ctx = canvas.getContext('2d');
  const scale = 2; // Retina scaling
  ctx.scale(scale, scale);
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

  // Background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

  // Draw grid structure
  drawGridLines(ctx);
  drawHourLabels(ctx);
  drawStatusLabels(ctx);
  drawTotalColumn(ctx, log);

  // Draw duty status segments
  drawSegments(ctx, log.segments);
}

function drawGridLines(ctx) {
  ctx.strokeStyle = '#d1d5db';
  ctx.lineWidth = 0.5;

  // Horizontal lines (status row separators)
  for (let i = 0; i <= 4; i++) {
    const y = GRID_TOP + i * ROW_HEIGHT;
    ctx.beginPath();
    ctx.moveTo(GRID_LEFT, y);
    ctx.lineTo(GRID_LEFT + GRID_WIDTH, y);
    ctx.stroke();
  }

  // Vertical lines (hour markers)
  for (let h = 0; h <= 24; h++) {
    const x = GRID_LEFT + h * HOUR_WIDTH;
    ctx.beginPath();
    ctx.moveTo(x, GRID_TOP);
    ctx.lineTo(x, GRID_TOP + GRID_HEIGHT);

    // Thicker lines at midnight and noon
    if (h === 0 || h === 12 || h === 24) {
      ctx.strokeStyle = '#6b7280';
      ctx.lineWidth = 1;
    } else {
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 0.5;
    }
    ctx.stroke();
  }

  // Quarter-hour tick marks (15-min intervals)
  ctx.strokeStyle = '#f3f4f6';
  ctx.lineWidth = 0.3;
  for (let h = 0; h < 24; h++) {
    for (let q = 1; q < 4; q++) {
      const x = GRID_LEFT + h * HOUR_WIDTH + q * (HOUR_WIDTH / 4);
      ctx.beginPath();
      ctx.moveTo(x, GRID_TOP);
      ctx.lineTo(x, GRID_TOP + GRID_HEIGHT);
      ctx.stroke();
    }
  }

  // Grid border
  ctx.strokeStyle = '#374151';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(GRID_LEFT, GRID_TOP, GRID_WIDTH, GRID_HEIGHT);
}

function drawHourLabels(ctx) {
  ctx.fillStyle = '#374151';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';

  const labels = [
    'Mid', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    'Noon', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', 'Mid'
  ];

  for (let h = 0; h <= 24; h++) {
    const x = GRID_LEFT + h * HOUR_WIDTH;
    ctx.fillText(labels[h], x, GRID_TOP - 5);
  }
}

function drawStatusLabels(ctx) {
  ctx.fillStyle = '#374151';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'right';

  STATUS_LABELS.forEach((label, idx) => {
    const y = GRID_TOP + idx * ROW_HEIGHT + ROW_HEIGHT / 2;
    const lines = label.split('\n');
    lines.forEach((line, lineIdx) => {
      ctx.fillText(line, GRID_LEFT - 8, y + (lineIdx - (lines.length - 1) / 2) * 12);
    });
  });
}

function drawTotalColumn(ctx, log) {
  ctx.fillStyle = '#374151';
  ctx.font = 'bold 10px sans-serif';
  ctx.textAlign = 'center';

  const totals = [
    log.total_off_duty || 0,
    log.total_sleeper || 0,
    log.total_driving || 0,
    log.total_on_duty || 0,
  ];

  const x = GRID_LEFT + GRID_WIDTH + 25;
  ctx.fillText('Total', x, GRID_TOP - 5);

  totals.forEach((total, idx) => {
    const y = GRID_TOP + idx * ROW_HEIGHT + ROW_HEIGHT / 2 + 4;
    ctx.fillText(total.toFixed(1), x, y);
  });
}

function drawSegments(ctx, segments) {
  if (!segments || segments.length === 0) return;

  let prevRow = null;
  let prevEndX = null;

  segments.forEach((segment) => {
    const rowIdx = STATUS_CODES.indexOf(segment.status);
    if (rowIdx === -1) return;

    const startX = GRID_LEFT + segment.start_hour * HOUR_WIDTH;
    const endX = GRID_LEFT + segment.end_hour * HOUR_WIDTH;
    const y = GRID_TOP + rowIdx * ROW_HEIGHT + ROW_HEIGHT / 2;

    const color = STATUS_COLORS[segment.status] || '#000000';
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;

    // Draw vertical transition line from previous segment
    if (prevRow !== null && prevRow !== rowIdx && prevEndX !== null) {
      const prevY = GRID_TOP + prevRow * ROW_HEIGHT + ROW_HEIGHT / 2;
      ctx.beginPath();
      ctx.moveTo(startX, prevY);
      ctx.lineTo(startX, y);
      ctx.stroke();
    }

    // Draw horizontal line for this segment's duration
    ctx.beginPath();
    ctx.moveTo(startX, y);
    ctx.lineTo(endX, y);
    ctx.stroke();

    prevRow = rowIdx;
    prevEndX = endX;
  });
}

export default ELDLogSheet;
