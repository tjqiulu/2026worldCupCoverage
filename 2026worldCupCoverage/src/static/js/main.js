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

async function loadMatches() {
    const showLoading = () => {
        matchesContainer.innerHTML = '<p class="loading">加载中 Loading...</p>';
        bracketContainer.innerHTML = '<p class="loading">加载中 Loading...</p>';
    };
    showLoading();
    try {
        const resp = await fetch('/api/matches');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        allMatches = await resp.json();
        renderMatches(allMatches);
        renderBracket(allMatches);
        scrollToToday();
    } catch (e) {
        const errHtml = `<p class="error">加载失败: ${escapeHtml(e.message)}</p>`;
        matchesContainer.innerHTML = errHtml;
        bracketContainer.innerHTML = errHtml;
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

function renderMatchCard(m) {
    const time = beijingTimeStr(m.date_utc);
    const home = (m.home && m.home.name) || '?';
    const away = (m.away && m.away.name) || '?';
    const stageLabel = m.group
        ? `Group ${m.group}${m.matchday ? ` · MD ${m.matchday}` : ''}`
        : labelStage(m.stage);
    const venue = (m.venue && m.venue.name) || '';
    return `<div class="match-card" data-id="${escapeHtml(m.match_id)}">
        <div class="match-time">${escapeHtml(time)}</div>
        <div class="match-team home">${escapeHtml(home)}</div>
        <div class="match-vs">vs</div>
        <div class="match-team away">${escapeHtml(away)}</div>
        <div class="match-meta">${escapeHtml(stageLabel)} · ${escapeHtml(venue)}</div>
    </div>`;
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

// === Plan 003: Tabs + Bracket ===

const STAGE_LABELS = {
    r32: '1/8 决赛 · R32',
    r16: '1/16 决赛 · R16',
    qf: '1/4 决赛 · QF',
    sf: '半决赛 · SF',
    final: '决赛 · Final',
    third: '季军战',
};

// Row span for each stage in the bracket grid (R32 row count = 16)
// R32 = 1, R16 = 2, QF = 4, SF = 8, Final = 16
const STAGE_ROW_SPAN = { r32: 1, r16: 2, qf: 4, sf: 8, final: 16 };

function renderBracket(matches) {
    if (!matches.length) {
        bracketContainer.innerHTML = '<p class="empty">暂无淘汰赛数据</p>';
        return;
    }

    const stages = {
        r32: [],
        r16: [],
        qf: [],
        sf: [],
        final: [],
    };
    const third = [];
    for (const m of matches) {
        if (m.stage in stages) stages[m.stage].push(m);
        else if (m.stage === 'third') third.push(m);
    }
    for (const k of Object.keys(stages)) {
        stages[k].sort((a, b) => a.date_utc.localeCompare(b.date_utc));
    }
    third.sort((a, b) => a.date_utc.localeCompare(b.date_utc));

    const stageOrder = ['r32', 'r16', 'qf', 'sf', 'final'];

    let html = '<div class="bracket-wrapper">';

    // Column labels
    html += '<div class="bracket-labels">';
    for (const stage of stageOrder) {
        html += `<div class="label">${escapeHtml(STAGE_LABELS[stage])}</div>`;
    }
    html += '</div>';

    // Bracket grid
    html += '<div class="bracket">';
    for (const stage of stageOrder) {
        const ms = stages[stage];
        const rowSpan = STAGE_ROW_SPAN[stage];
        ms.forEach((m, i) => {
            const rowStart = i * rowSpan + 1;
            html += renderBracketCard(m, stage, rowStart, rowSpan);
        });
    }
    html += '</div>';

    // Third place match (single column)
    if (third.length) {
        html += '<div class="bracket-labels" style="margin-top: 16px;">';
        html += `<div class="label" style="grid-column: 1 / -1;">${escapeHtml(STAGE_LABELS.third)}</div>`;
        html += '</div>';
        html += '<div class="bracket-single-col">';
        third.forEach(m => {
            html += renderBracketCard(m, 'third', 1, 1);
        });
        html += '</div>';
    }

    html += '</div>';
    bracketContainer.innerHTML = html;
}

function renderBracketCard(m, stage, rowStart, rowSpan) {
    const time = beijingTimeStr(m.date_utc);
    const date = beijingDateStr(m.date_utc);
    const home = m.home?.name || '?';
    const away = m.away?.name || '?';
    const venue = m.venue?.name || '';
    // For R32 use full date, for later rounds use shorter "7/04" format
    const dateLabel = stage === 'r32' || stage === 'third' ? date : date.substring(5).replace('-', '/');
    return `<div class="bracket-card ${stage}" style="grid-row: ${rowStart} / span ${rowSpan};"
                data-id="${escapeHtml(m.match_id)}" title="${escapeHtml(home + ' vs ' + away + ' · ' + date + ' ' + time + ' · ' + venue)}">
        <div class="bc-date">${escapeHtml(dateLabel)} ${escapeHtml(time)}</div>
        <div class="bc-teams">
            <div class="bc-team home">${escapeHtml(home)}</div>
            <div class="bc-vs">vs</div>
            <div class="bc-team away">${escapeHtml(away)}</div>
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
