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

const matchesContainer = document.getElementById('matches-container');
const refreshBtn = document.getElementById('refresh-btn');
const todayBtn = document.getElementById('today-btn');
const cacheInfo = document.getElementById('cache-info');

let allMatches = [];

async function loadMatches() {
    matchesContainer.innerHTML = '<p class="loading">加载中 Loading...</p>';
    try {
        const resp = await fetch('/api/matches');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        allMatches = await resp.json();
        renderMatches(allMatches);
        scrollToToday();
    } catch (e) {
        matchesContainer.innerHTML = `<p class="error">加载失败: ${escapeHtml(e.message)}</p>`;
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
todayBtn.addEventListener('click', scrollToToday);

loadMatches();
