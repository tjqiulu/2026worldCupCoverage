// 2026 World Cup Coverage - main frontend logic (Plan 002 minimal)

// === Timezone: Beijing (UTC+8) — user preference ===
const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;
const WEEKDAYS_ZH = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function toBeijing(utcIso) {
    // Returns a Date whose UTC components represent Beijing time.
    // Example: new Date('2026-06-11T19:00:00Z').getTime() + 8h
    //          -> Date whose getUTC*() reads 2026-06-12 03:00:00 (Beijing)
    return new Date(new Date(utcIso).getTime() + BEIJING_OFFSET_MS);
}

function beijingDateStr(utcIso) {
    const d = toBeijing(utcIso);
    const y = d.getUTCFullYear();
    const m = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function beijingTimeStr(utcIso) {
    const d = toBeijing(utcIso);
    const h = String(d.getUTCHours()).padStart(2, '0');
    const min = String(d.getUTCMinutes()).padStart(2, '0');
    return `${h}:${min}`;
}

function beijingWeekdayIdx(beijingDateString) {
    // Given a YYYY-MM-DD in Beijing time, return 0-6 weekday index.
    // Trick: noon Beijing of that date == 04:00 UTC of that date, which is
    // safely within the same Beijing date and gives the correct weekday.
    const [y, m, day] = beijingDateString.split('-').map(Number);
    const d = new Date(Date.UTC(y, m - 1, day, 4));
    return d.getUTCDay();
}

function todayBeijing() {
    return beijingDateStr(new Date().toISOString());
}

const matchesContainer = document.getElementById('matches-view');
const bracketContainer = document.getElementById('bracket-view');
const refreshBtn = document.getElementById('refresh-btn');
const todayBtn = document.getElementById('today-btn');
const cacheInfo = document.getElementById('cache-info');

let allMatches = [];
let allTeams = {};  // Plan 015: {team_id: {name, name_zh, code_iso, ...}}

async function loadMatches() {
    const showLoading = () => {
        matchesContainer.innerHTML = '<p class="loading">加载中 Loading...</p>';
        bracketContainer.innerHTML = '<p class="loading">加载中 Loading...</p>';
    };
    showLoading();
    // Retry up to 3 times with backoff (handles Flask reloader race, etc.)
    const MAX_RETRIES = 3;
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        try {
            const resp = await fetch('/api/matches');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            allMatches = await resp.json();
            // Plan 015: load teams BEFORE first render so modal can show
            // team names + flags in standings. Failure is non-fatal.
            await loadTeams();
            // Plan 016: widget mode takes over rendering
            if (_isWidgetMode()) {
                initWidgetMode();
            } else {
                renderMatches(allMatches);
                renderBracket(allMatches);
            }
            attachMatchCardClickHandlers();
            scrollToToday();
            return;  // success
        } catch (e) {
            if (attempt < MAX_RETRIES) {
                const delay = attempt * 1000;  // 1s, 2s, 3s
                console.warn(`Fetch attempt ${attempt} failed, retrying in ${delay}ms...`);
                await new Promise(r => setTimeout(r, delay));
            } else {
                // Plan 016: 'Failed to fetch' is the most common error when the Flask
                // server has died (e.g., process was killed). Show a retry button so
                // the user doesn't have to hard-refresh the whole PWA.
                const errHtml = `<div class="error-box">
                    <p class="error">加载失败: ${escapeHtml(e.message)}</p>
                    <p class="error-hint">服务可能已退出 · 点击重试 · 或 <code>bin/serve.sh</code> 重启服务</p>
                    <button class="error-retry-btn" onclick="window.location.reload()">🔄 重试 Retry</button>
                </div>`;
                matchesContainer.innerHTML = errHtml;
                bracketContainer.innerHTML = errHtml;
            }
        }
    }
}

async function loadTeams() {
    try {
        const resp = await fetch('/api/teams');
        if (resp.ok) {
            // Backend already normalizes: {id: {name, name_zh, code_iso, code_fifa, flag_url}}
            allTeams = await resp.json();
        }
    } catch (e) {
        console.warn('Failed to load teams:', e);
    }
}

function renderMatches(matches) {
    if (!matches.length) {
        matchesContainer.innerHTML = '<p class="empty">暂无比赛数据</p>';
        return;
    }

    // Group by Beijing date
    const byDate = {};
    for (const m of matches) {
        const d = beijingDateStr(m.date_utc);
        if (!byDate[d]) byDate[d] = [];
        byDate[d].push(m);
    }

    // Today in Beijing
    const today = todayBeijing();

    let html = '';
    for (const [date, ms] of Object.entries(byDate)) {
        const isToday = date === today;
        const dayLabel = formatDate(date);
        html += `<section class="day-group" data-date="${date}">`;
        html += `<h2 class="day-header ${isToday ? 'today' : ''}">`;
        html += `${dayLabel}${isToday ? '<span class="today-tag">今天</span>' : ''}`;
        html += `</h2>`;
        for (const m of ms) {
            html += renderMatchCard(m);
        }
        html += `</section>`;
    }
    matchesContainer.innerHTML = html;
}

// === Plan 016: Widget view (compact, desktop-background mode) ===

const WIDGET_REFRESH_MS = 60_000;
let _widgetTimerId = null;

function initWidgetMode() {
    if (!_isWidgetMode()) return;
    document.body.classList.add('widget-mode');
    // Load teams first (for standings display in modal, if user clicks)
    loadTeams().then(() => {
        renderWidget(allMatches);
        attachMatchCardClickHandlers();
        // Auto-refresh every 60s (silent in background)
        _widgetTimerId = setInterval(() => {
            fetch('/api/matches')
                .then(r => r.ok ? r.json() : null)
                .then(fresh => {
                    if (fresh) {
                        allMatches = fresh;
                        renderWidget(allMatches);
                        attachMatchCardClickHandlers();
                    }
                })
                .catch(e => console.warn('Widget auto-refresh failed:', e));
        }, WIDGET_REFRESH_MS);
    });
}

function _isWidgetMode() {
    return new URLSearchParams(window.location.search).get('view') === 'widget';
}

function renderWidget(matches) {
    const widgetEl = document.getElementById('widget-view');
    if (!widgetEl) return;
    const today = todayBeijing();
    // Find today's matches; if none, show next matchday
    let shown = matches.filter(m => beijingDateStr(m.date_utc) === today);
    if (!shown.length) {
        // Sort by date_utc, take next 5 upcoming
        shown = [...matches]
            .sort((a, b) => a.date_utc.localeCompare(b.date_utc))
            .filter(m => m.date_utc > new Date().toISOString())
            .slice(0, 5);
    } else {
        // Also include live / recent (last 6 hours)
        const sixHoursAgo = new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString();
        const recent = matches
            .filter(m => m.date_utc < today && m.date_utc >= sixHoursAgo
                && beijingDateStr(m.date_utc) === today)
            .slice(-3);
        // De-dup
        const ids = new Set(shown.map(m => m.match_id));
        for (const r of recent) if (!ids.has(r.match_id)) shown.unshift(r);
    }
    if (!shown.length) {
        widgetEl.innerHTML = '<p class="widget-empty">暂无比赛</p>';
        return;
    }
    let html = '';
    for (const m of shown) {
        html += renderWidgetCard(m);
    }
    widgetEl.innerHTML = html;
}

function renderWidgetCard(m) {
    const time = beijingTimeStr(m.date_utc);
    const status = getEffectiveStatus(m);
    const homeFlag = m.home && m.home.code_iso
        ? `<span class="fi fi-${escapeHtml(m.home.code_iso)}"></span>` : '';
    const awayFlag = m.away && m.away.code_iso
        ? `<span class="fi fi-${escapeHtml(m.away.code_iso)}"></span>` : '';
    const stageLabel = m.group
        ? `G${escapeHtml(m.group)}${m.matchday ? '·M' + escapeHtml(String(m.matchday)) : ''}`
        : labelStage(m.stage).replace(/1\/|1\/8|1\/16|1\/4/g, '').trim();
    let middle = '<span class="widget-vs">vs</span>';
    if ((status === 'final' || status === 'live') && m.details && m.details.score) {
        const s = m.details.score;
        const liveClass = status === 'live' ? ' live' : '';
        middle = `<span class="widget-score${liveClass}">${s.home} - ${s.away}</span>`;
    } else if (status === 'final') {
        middle = '<span class="widget-pending">待更新</span>';
    }
    return `<div class="widget-card" data-id="${escapeHtml(m.match_id)}" data-status="${status}">
        <div class="widget-row">
            <div class="widget-team home">
                <span class="widget-team-name">${escapeHtml(m.home.name_zh || m.home.name)}</span>
                ${homeFlag}
            </div>
            ${middle}
            <div class="widget-team away">
                ${awayFlag}
                <span class="widget-team-name">${escapeHtml(m.away.name_zh || m.away.name)}</span>
            </div>
        </div>
        <div class="widget-meta">
            <span class="widget-time">${escapeHtml(time)}</span>
            <span class="widget-stage">${stageLabel}</span>
            <span class="widget-status status-${status}">${widgetStatusLabel(status)}</span>
        </div>
    </div>`;
}

function widgetStatusLabel(status) {
    return ({
        final: '完场', live: 'LIVE', scheduled: '未开赛',
    })[status] || status;
}

function renderMatchCard(m) {
    const time = beijingTimeStr(m.date_utc);
    const stageLabel = m.group
        ? `Group ${m.group}${m.matchday ? ` · MD ${m.matchday}` : ''}`
        : labelStage(m.stage);
    const venue = (m.venue && m.venue.name) || '';
    const status = getEffectiveStatus(m);
    const statusBadge = renderStatusBadge(status);
    const scoreOrVs = (status === 'final' || status === 'live') && m.details && m.details.score
        ? renderScoreDisplay(m.details.score, status)
        : '<div class="match-vs">vs</div>';
    return `<div class="match-card" data-id="${escapeHtml(m.match_id)}" data-status="${status}">
        <div class="match-time">${escapeHtml(time)}</div>
        ${statusBadge}
        <div class="match-team home">${renderTeamName(m.home, 'home')}</div>
        ${scoreOrVs}
        <div class="match-team away">${renderTeamName(m.away, 'away')}</div>
        <div class="match-meta">${escapeHtml(stageLabel)} · ${escapeHtml(venue)}</div>
    </div>`;
}

// === Plan 011: Auto-detect match status from date_utc ===
// Constants for auto-detection window (in milliseconds)
const LIVE_WINDOW_MS = 2 * 60 * 60 * 1000;  // 2 hours before/after kickoff = "live"

function getEffectiveStatus(match, now) {
    // 1. details.status wins if set (manual override)
    if (match.details && match.details.status) {
        return match.details.status;
    }
    // 2. Auto-detect from date_utc
    const matchTime = new Date(match.date_utc).getTime();
    const nowMs = (now !== undefined) ? now : Date.now();
    if (matchTime + LIVE_WINDOW_MS < nowMs) {
        return 'final';  // match ended (>2h ago)
    }
    if (matchTime - LIVE_WINDOW_MS < nowMs && nowMs < matchTime + LIVE_WINDOW_MS) {
        return 'live';  // match in progress (or about to start)
    }
    return 'scheduled';  // future
}

function renderStatusBadge(status) {
    const map = {
        final: '<span class="status-badge status-final">已结束</span>',
        live: '<span class="status-badge status-live"><span class="live-dot"></span>LIVE</span>',
        scheduled: '<span class="status-badge status-scheduled">未开始</span>',
    };
    return map[status] || '';
}

function renderScoreDisplay(score, status) {
    if (!score) return '<div class="match-vs">vs</div>';
    const cls = status === 'live' ? 'match-score live' : 'match-score';
    return `<div class="${cls}">
        <span class="score-num">${score.home}</span>
        <span class="score-sep">-</span>
        <span class="score-num">${score.away}</span>
    </div>`;
}

function renderTeamName(side, align) {
    if (!side || !side.name) return '<span class="placeholder-name">?</span>';
    if (side.code_iso) {
        // Real country with flag
        return `<span class="team-name">
            ${align === 'away' ? renderEnName(side) : ''}
            <span class="fi fi-${escapeHtml(side.code_iso)}"></span>
            <span class="zh">${escapeHtml(side.name_zh || side.name)}</span>
            ${align === 'home' ? renderEnName(side) : ''}
        </span>`;
    }
    // Placeholder (W86, 1E, L101, etc.)
    return `<span class="placeholder-name">${escapeHtml(side.name)}</span>`;
}

function renderEnName(side) {
    if (!side.name || !side.name_zh) return '';
    if (side.name === side.name_zh) return '';  // same in both langs
    return `<span class="en">${escapeHtml(side.name)}</span>`;
}

function labelStage(stage) {
    const map = {
        'group': '小组赛',
        'r32': '1/8 决赛',
        'r16': '1/16 决赛',
        'qf': '1/4 决赛',
        'sf': '半决赛',
        'third': '季军战',
        'final': '决赛',
        'unknown': '',
    };
    return map[stage] || stage;
}

function formatDate(dateStr) {
    // dateStr is YYYY-MM-DD in Beijing time
    const [y, m, day] = dateStr.split('-').map(Number);
    return `${y}年${m}月${day}日 ${WEEKDAYS_ZH[beijingWeekdayIdx(dateStr)]}`;
}

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function scrollToToday() {
    const todayHeader = document.querySelector('.day-header.today');
    if (todayHeader) {
        todayHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// === Plan 003 (updated by Plan 005): Tabs + Mirror Bracket ===

const STAGE_LABELS = {
    r32: '1/8 决赛 · R32',
    r16: '1/16 决赛 · R16',
    qf: '1/4 决赛 · QF',
    sf: '半决赛 · SF',
    final: '决赛 · Final',
    third: '季军战',
};

function renderBracket(matches) {
    if (!matches.length) {
        bracketContainer.innerHTML = '<p class="empty">暂无淘汰赛数据</p>';
        return;
    }

    // Collect and sort by stage
    const stages = { r32: [], r16: [], qf: [], sf: [], final: [] };
    const third = [];
    for (const m of matches) {
        if (m.stage in stages) stages[m.stage].push(m);
        else if (m.stage === 'third') third.push(m);
    }
    for (const k of Object.keys(stages)) {
        stages[k].sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    }
    third.sort((a, b) => a.date_utc.localeCompare(b.date_utc));

    // Split halves using BRACKET ORDER (not chronological) so R16 cards
    // visually center between their actual R32 parents. FIFA pairings
    // aren't adjacent (e.g., R16-1 = R32-1 + R32-3), so chronological
    // order produces a zigzag layout.
    // See: src/data/bracket_pairings.py compute_bracket_order
    const r32Bracket = computeBracketOrder(stages.r32, stages.r16);
    const r32Top = r32Bracket.slice(0, 8);
    const r32Bot = r32Bracket.slice(8, 16);
    const r16Top = stages.r16.slice(0, 4);
    const r16Bot = stages.r16.slice(4, 8);
    const qfTop = stages.qf.slice(0, 2);
    const qfBot = stages.qf.slice(2, 4);
    const sfTop = stages.sf[0] || null;
    const sfBot = stages.sf[1] || null;
    const finalMatch = stages.final[0] || null;

    let html = '<div class="bracket-wrapper">';

    // Column labels: 9 columns (mirror)
    const labelTexts = ['R32', 'R16', 'QF', 'SF', 'Final', 'SF', 'QF', 'R16', 'R32'];
    html += '<div class="bracket-labels-mirror">';
    for (const l of labelTexts) {
        html += `<div class="label">${escapeHtml(l)}</div>`;
    }
    html += '</div>';

    // 9-column mirror grid (16 rows total)
    // Wrap in a positioned container so SVG lines can be absolute-positioned
    html += '<div class="bracket-mirror-wrapper">';
    html += '<svg class="bracket-lines" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"></svg>';
    html += '<div class="bracket-mirror">';

    // === Plan 008: 8-row layout, both halves in same vertical extent ===
    // Top half: cols 1-4, rows 1-8
    // Bottom half: cols 6-9, rows 1-8 (mirrored horizontally)
    // Final: col 5, row 1, span 8
    r32Top.forEach((m, i) => {
        html += renderMirrorCard(m, 'r32', 1, i + 1, 1);
    });
    r16Top.forEach((m, i) => {
        html += renderMirrorCard(m, 'r16', 2, i * 2 + 1, 2);
    });
    qfTop.forEach((m, i) => {
        html += renderMirrorCard(m, 'qf', 3, i * 4 + 1, 4);
    });
    if (sfTop) {
        html += renderMirrorCard(sfTop, 'sf', 4, 1, 8);
    }
    // Center: Final (rows 1-8)
    if (finalMatch) {
        html += renderMirrorCard(finalMatch, 'final', 5, 1, 8);
    }
    // Bottom half: rows 1-8, cols 6-9 (mirrored)
    if (sfBot) {
        html += renderMirrorCard(sfBot, 'sf', 6, 1, 8);
    }
    qfBot.forEach((m, i) => {
        html += renderMirrorCard(m, 'qf', 7, i * 4 + 1, 4);
    });
    r16Bot.forEach((m, i) => {
        html += renderMirrorCard(m, 'r16', 8, i * 2 + 1, 2);
    });
    r32Bot.forEach((m, i) => {
        html += renderMirrorCard(m, 'r32', 9, i + 1, 1);
    });

    html += '</div>';  // close .bracket-mirror
    html += '</div>';  // close .bracket-mirror-wrapper

    // Third place match (single column below mirror)
    if (third.length) {
        html += '<div class="bracket-labels-mirror" style="margin-top: 24px; grid-template-columns: minmax(200px, 400px);">';
        html += `<div class="label">${escapeHtml(STAGE_LABELS.third)}</div>`;
        html += '</div>';
        html += '<div class="bracket-single-col">';
        third.forEach(m => {
            html += renderMirrorCard(m, 'third', 1, 1, 1);
        });
        html += '</div>';
    }

    html += '</div>';
    bracketContainer.innerHTML = html;

    // Draw connecting lines on top of the grid (behind cards)
    drawBracketLines(bracketContainer, matches);

    // Attach click handlers for opening detail modal
    attachMatchCardClickHandlers();
}

// === Plan 007: Bracket connecting lines (SVG overlay) ===

const SVG_NS = 'http://www.w3.org/2000/svg';

function drawBracketLines(container, matches) {
    const wrapper = container.querySelector('.bracket-mirror-wrapper');
    if (!wrapper) return;
    const svg = wrapper.querySelector('.bracket-lines');
    if (!svg) return;

    // Clear existing
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Get wrapper bounds (offset for relative positioning of SVG)
    const wBox = wrapper.getBoundingClientRect();
    svg.setAttribute('viewBox', `0 0 ${wBox.width} ${wBox.height}`);

    // Build card map by match id
    const cardById = new Map();
    for (const card of wrapper.querySelectorAll('.bracket-card')) {
        const id = card.dataset.id;
        if (id) cardById.set(id, card);
    }

    // Stage data
    const r32ByDate = matches.filter(m => m.stage === 'r32').sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    const r16ByDate = matches.filter(m => m.stage === 'r16').sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    const qfByDate = matches.filter(m => m.stage === 'qf').sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    const sfByDate = matches.filter(m => m.stage === 'sf').sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    const finalMatch = matches.find(m => m.stage === 'final');

    // Map R32 by bracket position (1-16)
    const r32ByPos = new Map();
    r32ByDate.forEach((m, i) => r32ByPos.set(i + 1, m));

    // R32 -> R16 (8 groups, 2 R32 each)
    for (const r16m of r16ByDate) {
        const wH = parseInt((r16m.home?.name || '').replace('W', ''));
        const wA = parseInt((r16m.away?.name || '').replace('W', ''));
        const r32Parents = [wH, wA]
            .filter(w => w)
            .map(w => r32ByPos.get(w - 72))
            .filter(m => m)
            .map(m => cardById.get(m.match_id));
        connect(svg, r32Parents, cardById.get(r16m.match_id), wBox);
    }

    // R16 -> QF (4 groups, 2 R16 each)
    for (let i = 0; i < qfByDate.length; i++) {
        const r16Parents = [r16ByDate[i * 2], r16ByDate[i * 2 + 1]]
            .filter(m => m)
            .map(m => cardById.get(m.match_id));
        connect(svg, r16Parents, cardById.get(qfByDate[i].match_id), wBox);
    }

    // QF -> SF (2 groups, 2 QF each)
    for (let i = 0; i < sfByDate.length; i++) {
        const qfParents = [qfByDate[i * 2], qfByDate[i * 2 + 1]]
            .filter(m => m)
            .map(m => cardById.get(m.match_id));
        connect(svg, qfParents, cardById.get(sfByDate[i].match_id), wBox);
    }

    // SF -> Final (1 group, 2 SF)
    if (finalMatch) {
        const sfParents = sfByDate.map(m => cardById.get(m.match_id));
        connect(svg, sfParents, cardById.get(finalMatch.match_id), wBox);
    }
}

function connect(svg, parentCards, childCard, wBox) {
    if (!childCard) return;
    const parents = (Array.isArray(parentCards) ? parentCards : [parentCards]).filter(p => p);
    if (parents.length === 0) return;

    const cBox = childCard.getBoundingClientRect();
    const cy = cBox.top + cBox.height / 2 - wBox.top;
    const cLeft = cBox.left - wBox.left;
    const cRight = cBox.right - wBox.left;
    const cCenterX = cLeft + cBox.width / 2;

    // Get all parent (left, right, y) endpoints
    const parentsData = parents.map(p => {
        const b = p.getBoundingClientRect();
        return {
            left: b.left - wBox.left,
            right: b.right - wBox.left,
            y: b.top + b.height / 2 - wBox.top,
        };
    });
    parentsData.sort((a, b) => a.y - b.y);

    // Direction: if parent center is LEFT of child center, go RIGHT (use parent.right)
    //            if parent center is RIGHT of child center, go LEFT (use parent.left)
    const pCenterX = (parentsData[0].left + parentsData[0].right) / 2;
    const goingRight = pCenterX < cCenterX;
    const px = goingRight ? parentsData[0].right : parentsData[0].left;
    const cEdge = goingRight ? cLeft : cRight;

    if (parents.length === 1) {
        // Simple L: parent edge -> vertical to child y -> horizontal to child edge
        const path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', `M ${px} ${parentsData[0].y} V ${cy} H ${cEdge}`);
        path.setAttribute('class', 'bracket-line');
        svg.appendChild(path);
        return;
    }

    // 2+ parents: T-shape (vertical line spanning all parents + horizontal to child)
    const x = px;  // all parents share the same edge x
    const vert = document.createElementNS(SVG_NS, 'path');
    vert.setAttribute('d', `M ${x} ${parentsData[0].y} L ${x} ${parentsData[parentsData.length - 1].y}`);
    vert.setAttribute('class', 'bracket-line');
    svg.appendChild(vert);

    const horz = document.createElementNS(SVG_NS, 'path');
    horz.setAttribute('d', `M ${x} ${cy} L ${cEdge} ${cy}`);
    horz.setAttribute('class', 'bracket-line');
    svg.appendChild(horz);

    const dot = document.createElementNS(SVG_NS, 'circle');
    dot.setAttribute('cx', x);
    dot.setAttribute('cy', cy);
    dot.setAttribute('r', '2');
    dot.setAttribute('class', 'bracket-dot');
    svg.appendChild(dot);
}

function computeBracketOrder(r32, r16) {
    // Build R32 position → match lookup
    const r32ByPos = new Map();
    r32.forEach((m, i) => r32ByPos.set(i + 1, m));
    // For each R16 match, take its 2 R32 parents (in home/away order)
    const order = [];
    const seen = new Set();
    for (const r16m of r16) {
        const wH = parseInt((r16m.home.name || '').replace('W', ''));
        const wA = parseInt((r16m.away.name || '').replace('W', ''));
        for (const w of [wH, wA]) {
            if (w) {
                const pos = w - 72;
                const m = r32ByPos.get(pos);
                if (m && !seen.has(m.match_id)) {
                    order.push(m);
                    seen.add(m.match_id);
                }
            }
        }
    }
    return order;
}

function renderMirrorCard(m, stage, col, row, span) {
    const time = beijingTimeStr(m.date_utc);
    const date = beijingDateStr(m.date_utc);
    const venue = m.venue?.name || '';
    const homeTitle = m.home?.name || '?';
    const awayTitle = m.away?.name || '?';
    // For R32 use full date, for later rounds use shorter "7/04" format
    const dateLabel = stage === 'r32' || stage === 'third' ? date : date.substring(5).replace('-', '/');
    const colClass = `col-${col}`;
    return `<div class="bracket-card ${stage} ${colClass}"
                style="grid-column: ${col}; grid-row: ${row} / span ${span};"
                data-id="${escapeHtml(m.match_id)}"
                title="${escapeHtml(homeTitle + ' vs ' + awayTitle + ' · ' + date + ' ' + time + ' · ' + venue)}">
        <div class="bc-date">${escapeHtml(dateLabel)} ${escapeHtml(time)}</div>
        <div class="bc-teams">
            <div class="bc-team home">${renderTeamName(m.home, 'home')}</div>
            <div class="bc-vs">vs</div>
            <div class="bc-team away">${renderTeamName(m.away, 'away')}</div>
        </div>
    </div>`;
}

function showTab(name) {
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === name);
    });
    document.querySelectorAll('.view').forEach(v => {
        v.classList.toggle('active', v.id === `${name}-view`);
    });
}

document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
});

// === Plan 009: Match detail modal ===

const STAGE_LABELS_ZH = {
    group: '小组赛',
    r32: '1/8 决赛 R32',
    r16: '1/16 决赛 R16',
    qf: '1/4 决赛 QF',
    sf: '半决赛',
    third: '季军战',
    final: '决赛',
    unknown: '未知阶段',
};

const WEEKDAYS_FULL_ZH = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

function describePlaceholder(name) {
    if (!name) return '';
    if (name.startsWith('W')) {
        const n = name.slice(1);
        return `${n} 场胜者`;
    }
    if (name.startsWith('L')) {
        const n = name.slice(1);
        return `${n} 场败者`;
    }
    // 1X / 2X / 3X
    const m = name.match(/^([123])([A-Z])$/);
    if (m) {
        const place = { '1': '第一', '2': '第二', '3': '第三' }[m[1]];
        return `${m[2]} 组${place}`;
    }
    return name;
}

function renderModalTeam(team) {
    if (!team) return '';
    if (team.code_iso) {
        return `<span class="fi fi-${escapeHtml(team.code_iso)}"></span>
                <div class="team-name-zh">${escapeHtml(team.name_zh || team.name)}</div>
                <div class="team-name-en">${escapeHtml(team.name)}</div>`;
    }
    return `<div class="placeholder-flag" title="${escapeHtml(describePlaceholder(team.name))}">?</div>
            <div class="team-name-zh placeholder-name">${escapeHtml(team.name)}</div>
            <div class="team-name-en">${escapeHtml(describePlaceholder(team.name))}</div>`;
}

function getStageFullLabel(match) {
    if (match.stage === 'group' && match.group) {
        return `${STAGE_LABELS_ZH.group} · Group ${match.group}${match.matchday ? ` · 第 ${match.matchday} 轮` : ''}`;
    }
    if (match.stage === 'third') {
        return STAGE_LABELS_ZH.third;
    }
    return STAGE_LABELS_ZH[match.stage] || match.stage;
}

function formatModalDate(utcIso) {
    const d = new Date(utcIso);
    const bj = new Date(d.getTime() + BEIJING_OFFSET_MS);
    const month = bj.getUTCMonth() + 1;
    const day = bj.getUTCDate();
    const weekday = WEEKDAYS_FULL_ZH[bj.getUTCDay()];
    const hour = String(bj.getUTCHours()).padStart(2, '0');
    const min = String(bj.getUTCMinutes()).padStart(2, '0');
    return `${month} 月 ${day} 日 ${weekday} ${hour}:${min}（北京时间）`;
}

function showMatchModal(matchId) {
    const match = allMatches.find(m => m.match_id === matchId);
    if (!match) return;
    document.getElementById('modal-stage').textContent = getStageFullLabel(match);
    document.getElementById('modal-date').textContent = formatModalDate(match.date_utc);
    document.getElementById('modal-home').innerHTML = renderModalTeam(match.home);
    document.getElementById('modal-away').innerHTML = renderModalTeam(match.away);

    // Plan 010: score + goalscorers section
    const scoreSection = document.getElementById('modal-score-section');
    const details = match.details;
    const status = getEffectiveStatus(match);
    if ((status === 'final' || status === 'live') && details && details.score) {
        scoreSection.innerHTML = renderModalScore(details, status);
        scoreSection.hidden = false;
    } else if (status === 'final' && (!details || !details.score)) {
        // Auto-detected as final but no details.json entry: show "score pending"
        scoreSection.innerHTML = renderModalFinalNoDetails();
        scoreSection.hidden = false;
    } else {
        scoreSection.innerHTML = '';
        scoreSection.hidden = true;
    }

    // Plan 010: goalscorers list (only for final)
    const goalsSection = document.getElementById('modal-goals-section');
    if (status === 'final' && details && details.goalscorers && details.goalscorers.length) {
        goalsSection.innerHTML = renderModalGoals(details, match);
        goalsSection.hidden = false;
    } else {
        goalsSection.innerHTML = '';
        goalsSection.hidden = true;
    }

    const venueEl = document.getElementById('modal-venue');
    if (match.venue && match.venue.name) {
        venueEl.innerHTML = `<span class="venue-name">📍 ${escapeHtml(match.venue.name)}</span>`;
    } else {
        venueEl.innerHTML = '';
    }

    // Plan 015: stadium section (full name + city + capacity)
    const stadiumEl = document.getElementById('modal-stadium-section');
    const stadium = match.venue && match.venue.stadium;
    if (stadium && stadium.name) {
        stadiumEl.innerHTML = renderModalStadium(stadium);
        stadiumEl.hidden = false;
    } else {
        stadiumEl.innerHTML = '';
        stadiumEl.hidden = true;
    }

    // Plan 015: group standings (all group stage matches — including finished,
    // so the user can see how the table evolved after this match)
    const standingsEl = document.getElementById('modal-standings-section');
    if (match.stage === 'group' && match.group
        && Array.isArray(match.standings) && match.standings.length) {
        standingsEl.innerHTML = renderModalStandings(match);
        standingsEl.hidden = false;
    } else {
        standingsEl.innerHTML = '';
        standingsEl.hidden = true;
    }

    // Plan 015: countdown (only for not-yet-started)
    const countdownEl = document.getElementById('modal-countdown-section');
    if (status === 'scheduled' && match.date_utc) {
        countdownEl.innerHTML = renderModalCountdown(match);
        countdownEl.hidden = false;
        startCountdownTimer(match);
    } else {
        countdownEl.innerHTML = '';
        countdownEl.hidden = true;
        stopCountdownTimer();
    }

    document.getElementById('match-modal').hidden = false;
}

function renderModalScore(details, status) {
    const { score, half_time_score } = details;
    const statusLabel = status === 'live'
        ? '<span class="score-status live">LIVE</span>'
        : '<span class="score-status final">完场</span>';
    let hts = '';
    if (half_time_score) {
        hts = `<div class="score-half">半场 ${half_time_score.home} - ${half_time_score.away}</div>`;
    }
    return `<div class="modal-score-label">比分 Score ${statusLabel}</div>
        <div class="modal-score-big">
            <span class="score-num">${score.home}</span>
            <span class="score-sep">-</span>
            <span class="score-num">${score.away}</span>
        </div>
        ${hts}`;
}

function renderModalGoals(details, match) {
    const rows = details.goalscorers.map(g => {
        const flag = g.team === 'home' && match.home.code_iso
            ? `<span class="fi fi-${escapeHtml(match.home.code_iso)}"></span>`
            : g.team === 'away' && match.away.code_iso
                ? `<span class="fi fi-${escapeHtml(match.away.code_iso)}"></span>`
                : '';
        const typeBadge = g.type === 'penalty' ? ' <span class="goal-badge goal-pen">P</span>'
            : g.type === 'own_goal' ? ' <span class="goal-badge goal-og">OG</span>' : '';
        // Plan 016 fix: render stoppage time as "45'+5'" instead of just "45'"
        const minuteStr = g.stoppage
            ? `${g.minute}'+${g.stoppage}'`
            : `${g.minute}'`;
        return `<li class="goal-row">
            <span class="goal-flag">${flag}</span>
            <span class="goal-player">${escapeHtml(g.player)}${typeBadge}</span>
            <span class="goal-minute">${minuteStr}</span>
        </li>`;
    }).join('');
    return `<div class="modal-goals-label">进球 Goals</div>
        <ul class="modal-goals-list">${rows}</ul>`;
}

function renderModalFinalNoDetails() {
    return `<div class="modal-score-label">比分 Score</div>
        <div class="modal-score-pending">
            比赛已结束 · 比分待更新
        </div>
        <div class="modal-score-hint">Match ended · Score pending update</div>
        <div class="modal-score-manual-hint">
            💡 worldcup26.ir 还未录入该场比分 · 点刷新可重拉 · 仍没有可手动加
            <br><small>worldcup26.ir has not posted this match's score yet. Try Refresh. If still missing, you can <a href="https://github.com/tjqiulu/2026worldCupCoverage/blob/main/data/details.json" target="_blank" rel="noopener">add it manually to details.json</a>.</small>
        </div>`;
}

// === Plan 015: Stadium, Standings, Countdown ===

function renderModalStadium(stadium) {
    const capacity = (typeof stadium.capacity === 'number' && stadium.capacity > 0)
        ? stadium.capacity.toLocaleString('en-US')
        : null;
    return `<div class="modal-section-label">🏟️ 球场 Stadium</div>
        <div class="modal-stadium-card">
            <div class="stadium-name">${escapeHtml(stadium.name)}</div>
            <div class="stadium-loc">📍 ${escapeHtml(stadium.city || '')}${stadium.country ? ', ' + escapeHtml(stadium.country) : ''}</div>
            ${capacity ? `<div class="stadium-capacity">容量 Capacity: <strong>${capacity}</strong></div>` : ''}
        </div>`;
}

function _teamFlag(teamId) {
    // Look up team in the global team map (loaded with matches). Falls back to nothing.
    const t = (typeof allTeams !== 'undefined' && allTeams && allTeams[teamId]) || null;
    if (t && t.code_iso) {
        return `<span class="fi fi-${escapeHtml(t.code_iso)}"></span>`;
    }
    return '';
}

function _teamName(teamId) {
    const t = (typeof allTeams !== 'undefined' && allTeams && allTeams[teamId]) || null;
    if (t) {
        return escapeHtml(t.name_zh || t.name || teamId);
    }
    return `Team ${teamId}`;
}

function _gdStr(v) {
    // Plan 019: format goal difference with explicit + / - sign
    const n = _numOrZero(v);
    if (n > 0) return `+${n}`;
    return String(n);
}

function renderModalStandings(match) {
    const rows = match.standings.map((t, i) => {
        const rank = i + 1;
        const flag = _teamFlag(t.team_id);
        const name = _teamName(t.team_id);
        return `<tr class="standings-row">
            <td class="standings-rank">${rank}</td>
            <td class="standings-team"><span class="standings-flag">${flag}</span><span class="standings-name">${name}</span></td>
            <td class="standings-num">${_numOrZero(t.mp)}</td>
            <td class="standings-num">${_numOrZero(t.w)}</td>
            <td class="standings-num">${_numOrZero(t.d)}</td>
            <td class="standings-num">${_numOrZero(t.l)}</td>
            <td class="standings-num">${_numOrZero(t.gf)}</td>
            <td class="standings-num">${_numOrZero(t.ga)}</td>
            <td class="standings-num standings-gd">${_gdStr(t.gd)}</td>
            <td class="standings-num standings-pts"><strong>${_numOrZero(t.pts)}</strong></td>
        </tr>`;
    }).join('');
    return `<div class="modal-section-label">🏆 ${escapeHtml(match.group)} 组积分榜 Group ${escapeHtml(match.group)} Standings</div>
        <div class="modal-standings-wrap">
            <table class="modal-standings-table">
                <thead>
                    <tr>
                        <th class="standings-rank">#</th>
                        <th class="standings-team">球队 Team</th>
                        <th class="standings-num">赛 MP</th>
                        <th class="standings-num">胜 W</th>
                        <th class="standings-num">平 D</th>
                        <th class="standings-num">负 L</th>
                        <th class="standings-num">进 GF</th>
                        <th class="standings-num">失 GA</th>
                        <th class="standings-num">净 GD</th>
                        <th class="standings-num">分 Pts</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
}

function _numOrZero(v) {
    if (v === null || v === undefined || v === '') return 0;
    const n = parseInt(v, 10);
    return isNaN(n) ? 0 : n;
}

function renderModalCountdown(match) {
    const kickoffBjt = formatModalDate(match.date_utc);
    return `<div class="modal-section-label">⏱️ 距离开赛 Kickoff in</div>
        <div class="modal-countdown-card">
            <div class="countdown-time" id="modal-countdown-time" data-target="${escapeHtml(match.date_utc)}">--:--:--</div>
            <div class="countdown-kickoff">开赛时间: ${escapeHtml(kickoffBjt)}</div>
        </div>`;
}

let _countdownTimerId = null;
let _countdownTarget = null;

function startCountdownTimer(match) {
    stopCountdownTimer();
    _countdownTarget = match.date_utc;
    const tick = () => {
        const el = document.getElementById('modal-countdown-time');
        if (!el || el.dataset.target !== _countdownTarget) {
            stopCountdownTimer();
            return;
        }
        el.textContent = formatCountdown(_countdownTarget);
    };
    tick();
    _countdownTimerId = setInterval(tick, 1000);
}

function stopCountdownTimer() {
    if (_countdownTimerId !== null) {
        clearInterval(_countdownTimerId);
        _countdownTimerId = null;
    }
    _countdownTarget = null;
}

function formatCountdown(utcIso) {
    const target = new Date(utcIso).getTime();
    if (isNaN(target)) return '--:--:--';
    const now = Date.now();
    let diffMs = target - now;
    if (diffMs <= 0) return '已开赛 · 即将更新';
    const totalSec = Math.floor(diffMs / 1000);
    const days = Math.floor(totalSec / 86400);
    const rem = totalSec - days * 86400;
    const hours = Math.floor(rem / 3600);
    const mins = Math.floor((rem % 3600) / 60);
    const secs = rem % 60;
    const pad = n => String(n).padStart(2, '0');
    if (days > 0) {
        return `${days} 天 ${pad(hours)}:${pad(mins)}:${pad(secs)}`;
    }
    return `${pad(hours)}:${pad(mins)}:${pad(secs)}`;
}

function closeMatchModal() {
    document.getElementById('match-modal').hidden = true;
}

function attachMatchCardClickHandlers() {
    document.querySelectorAll('.match-card, .bracket-card, .widget-card').forEach(card => {
        if (card.dataset.id && !card.dataset.clickBound) {
            card.addEventListener('click', () => showMatchModal(card.dataset.id));
            card.dataset.clickBound = '1';
        }
    });
}

// Hook up modal close handlers
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('match-modal');
    if (modal) {
        modal.querySelector('.match-modal-close').addEventListener('click', closeMatchModal);
        modal.querySelector('.match-modal-backdrop').addEventListener('click', closeMatchModal);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.hidden) {
                closeMatchModal();
            }
        });
    }
});

async function refreshData() {
    refreshBtn.disabled = true;
    const original = refreshBtn.textContent;
    refreshBtn.textContent = '⏳ 刷新中...';
    try {
        const resp = await fetch('/api/refresh', { method: 'POST' });
        const data = await resp.json();
        if (data.status === 'ok') {
            cacheInfo.textContent = `${data.count} 场 (刚刚)`;
            await loadMatches();
        } else {
            alert('刷新失败: ' + (data.message || '未知错误'));
        }
    } catch (e) {
        alert('刷新失败: ' + e.message);
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = original;
    }
}

refreshBtn.addEventListener('click', refreshData);
todayBtn.addEventListener('click', () => {
    showTab('matches');
    setTimeout(scrollToToday, 50);
});

loadMatches();


// === Plan 014: PWA install prompt ===

let deferredInstallPrompt = null;

function setupPwaInstall() {
    const btn = document.getElementById('install-pwa-btn');
    if (!btn) return;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredInstallPrompt = e;
        btn.hidden = false;
        btn.textContent = '📲 安装';
    });
    btn.addEventListener('click', async () => {
        if (!deferredInstallPrompt) return;
        deferredInstallPrompt.prompt();
        const choice = await deferredInstallPrompt.userChoice;
        if (choice.outcome === 'accepted') {
            btn.textContent = '✓ 已安装';
            btn.disabled = true;
        } else {
            btn.textContent = '📲 安装';
        }
        deferredInstallPrompt = null;
    });
    window.addEventListener('appinstalled', () => {
        btn.hidden = true;
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupPwaInstall);
} else {
    setupPwaInstall();
}
