"""HTML 渲染模板（暖调卡片风格）。纯 Python 模板，不使用 LLM。"""

CATEGORY_EMOJI_MAP: dict[str, str] = {
    "模型发布": "rocket",
    "开源项目": "code",
    "研究论文": "science",
    "产品动态": "devices",
    "行业观点": "lightbulb",
    "工具技巧": "build",
}

CATEGORY_COLOR_MAP: dict[str, str] = {
    "模型发布": "#c96442",
    "开源项目": "#335c67",
    "研究论文": "#9e2a2b",
    "产品动态": "#e09f3e",
    "行业观点": "#c96442",
    "工具技巧": "#335c67",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 日报 · {date}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,300,0,0&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<script>
tailwind.config = {{
    theme: {{
        extend: {{
            colors: {{
                warm: {{ 50: '#fbf9f6', 100: '#f5f0ea', 200: '#e8dfd5', 400: '#b5a08a', 500: '#8a7f76', 600: '#6b6158', 700: '#4a403a', 800: '#342d28', 900: '#1f1a17' }},
                accent: {{ DEFAULT: '#c96442', light: '#e8825f', dark: '#a84e32' }},
            }},
            fontFamily: {{ sans: ['Noto Sans SC', 'system-ui', 'sans-serif'] }},
        }}
    }}
}}
</script>
<style>
body {{ font-family: 'Noto Sans SC', system-ui, sans-serif; }}
.material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; font-weight: 300 !important; font-style: normal; display: inline-block; line-height: 1; font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24 !important; }}
.card-hover {{ transition: all 0.25s ease; }}
.card-hover:hover {{ transform: translateY(-3px); box-shadow: 0 12px 24px -8px rgba(74,64,58,0.14); }}
</style>
</head>
<body class="bg-warm-50 text-warm-700 antialiased">

<!-- Navigation -->
<nav class="fixed top-0 w-full bg-warm-50/85 backdrop-blur-md z-50 border-b border-warm-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
        <a href="../index.html" class="text-lg font-bold text-accent hover:text-accent-dark transition">← AI 日报</a>
        <span class="text-warm-500 text-sm">{date}</span>
    </div>
</nav>

<main class="pt-20 pb-16">
    <!-- Header -->
    <section class="bg-gradient-to-br from-accent to-accent-dark text-white py-12 mb-10">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold mb-2">AI 日报 · {date}</h1>
            <p class="text-orange-100">共 {article_count} 篇精选，来自 {source_count} 个信息源</p>
        </div>
    </section>

    <!-- Overview -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-10">
        <div class="bg-white border border-warm-200 rounded-xl p-6 shadow-sm" style="border-left: 4px solid #c96442;">
            <p class="text-warm-700 leading-relaxed">{overview}</p>
        </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {content}
    </div>

    <!-- Keywords -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-12">
        <div class="bg-white border border-warm-200 rounded-xl p-6 shadow-sm text-center">
            <h2 class="text-lg font-bold text-warm-800 mb-4">今日关键词</h2>
            <div class="flex flex-wrap justify-center gap-2">{keywords_html}</div>
        </div>
    </div>
</main>

<footer class="text-center text-warm-400 text-sm py-8 border-t border-warm-200">
    由 AI 日报 自动生成 · {generated_at}
</footer>
</body>
</html>"""

CATEGORY_SECTION_TEMPLATE = """<section class="mb-10">
    <div class="flex items-center gap-3 mb-5">
        <span class="material-symbols-rounded text-2xl" style="color: {color};">{icon}</span>
        <h2 class="text-xl font-bold" style="color: {color};">{category}</h2>
        <span class="text-xs text-warm-400 bg-warm-100 px-2.5 py-0.5 rounded-full">{count} 篇</span>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        {cards}
    </div>
</section>"""

ARTICLE_CARD_TEMPLATE = """<div class="bg-white border border-warm-200 rounded-xl overflow-hidden shadow-sm card-hover{featured_class}" style="{featured_style}">
    <div class="p-5">
        <div class="flex items-start gap-3 mb-3">
            <span class="material-symbols-rounded mt-0.5 flex-shrink-0" style="color: {color}; font-size: 20px;">{icon}</span>
            <h3 class="text-base font-bold leading-snug flex-1" style="color: {color};">{title}</h3>
            <span class="flex-shrink-0 text-xs font-bold text-white px-2 py-0.5 rounded" style="background: {color};">{score}</span>
        </div>
        <p class="text-sm text-warm-700 leading-relaxed mb-3">{summary}</p>
        <div class="flex flex-wrap items-center gap-1.5 text-xs text-warm-500">
            <a href="{url}" target="_blank" rel="noopener" class="text-accent font-medium hover:underline">原文 ↗</a>
            <span>·</span>
            <span class="font-medium text-warm-600">{source}</span>
            <span>·</span>
            <span>{publish_time}</span>
            <span>·</span>
            {tags}
        </div>
    </div>
</div>"""

INDEX_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 日报 — 每天更新最新行业动态</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,300,0,0&display=swap" rel="stylesheet">
<script>
tailwind.config = {
    theme: {
        extend: {
            colors: {
                warm: { 50: '#fbf9f6', 100: '#f5f0ea', 200: '#e8dfd5', 300: '#d1c4b2', 400: '#b5a08a', 500: '#8a7f76', 600: '#6b6158', 700: '#4a403a', 800: '#342d28', 900: '#1f1a17' },
                accent: { DEFAULT: '#c96442', light: '#e8825f', dark: '#a84e32' },
            },
            fontFamily: { sans: ['Noto Sans SC', 'system-ui', 'sans-serif'] },
        }
    }
}
</script>
<style>
body { font-family: 'Noto Sans SC', system-ui, sans-serif; }
.material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; font-weight: 300 !important; font-style: normal; display: inline-block; line-height: 1; font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24 !important; }
.card-hover { transition: all 0.25s ease; }
.card-hover:hover { transform: translateY(-3px); box-shadow: 0 12px 28px -8px rgba(74,64,58,0.15); }
.fade-in { animation: fadeIn 0.5s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
.report-card { opacity: 0; animation: slideUp 0.4s ease-out forwards; }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>
</head>
<body class="bg-warm-50 text-warm-700">

<!-- Navigation -->
<nav class="fixed top-0 w-full bg-warm-50/85 backdrop-blur-md z-50 border-b border-warm-200">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
        <a href="index.html" class="text-xl font-bold text-accent">AI 日报</a>
        <div class="hidden md:flex items-center space-x-6 text-sm">
            <a href="#latest" class="text-warm-500 hover:text-accent transition">最新一期</a>
            <a href="#archive" class="text-warm-500 hover:text-accent transition">往期回顾</a>
        </div>
    </div>
</nav>

<!-- Hero -->
<section class="bg-gradient-to-br from-accent to-accent-dark text-white pt-28 pb-14">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center fade-in">
        <h1 class="text-4xl md:text-5xl font-bold mb-3">AI 日报</h1>
        <p class="text-lg md:text-xl text-orange-100 max-w-2xl mx-auto mb-6">每天更新最新行业动态</p>
        <a href="#latest" class="inline-block bg-white text-accent px-6 py-2.5 rounded-full font-semibold hover:bg-orange-50 transition text-sm">阅读最新一期</a>
    </div>
</section>

<!-- Latest Issue -->
<section id="latest" class="py-14">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div id="latest-report" class="fade-in"></div>
    </div>
</section>

<!-- Archive -->
<section id="archive" class="py-14 bg-white">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-2xl font-bold text-warm-800 mb-8 text-center">往期回顾</h2>
        <div id="reports-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </div>
</section>

<!-- Footer -->
<footer class="bg-warm-900 text-warm-400 py-8">
    <div class="max-w-6xl mx-auto px-4 text-center text-sm">
        <p class="font-semibold text-warm-200 mb-1">AI 日报</p>
        <p>每日精选 · 智能筛选 · 自动生成</p>
    </div>
</footer>

<script src="reports.js"></script>
<script>
const secColors = { '产品应用': ['bg-orange-50','text-orange-700','border-orange-200','orange'], '开发生态': ['bg-teal-50','text-teal-700','border-teal-200','teal'], '行业动态': ['bg-purple-50','text-purple-700','border-purple-200','purple'], '研究前沿': ['bg-blue-50','text-blue-700','border-blue-200','blue'] };
const secIcons = { '产品应用': 'devices', '开发生态': 'code', '行业动态': 'trending_up', '研究前沿': 'science' };
function fmtDate(d) { return new Date(d).toLocaleDateString('zh-CN', {year:'numeric',month:'long',day:'numeric'}); }

function sectionCard(sec) {
    const c = secColors[sec.name] || ['bg-gray-50','text-gray-700','border-gray-200','gray'];
    const icon = secIcons[sec.name] || sec.icon || 'article';
    const items = sec.items.map(it => `<li class="flex items-start gap-2 py-1"><span class="text-warm-300 mt-0.5">·</span><a href="${it.url}" target="_blank" rel="noopener" class="text-warm-700 hover:text-accent transition text-sm leading-snug line-clamp-1">${it.title}</a></li>`).join('');
    return `<div class="${c[0]} border ${c[2]} rounded-xl p-5 card-hover">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-rounded ${c[1]}" style="font-size:22px">${icon}</span>
            <h4 class="font-bold ${c[1]}">${sec.name}</h4>
            <span class="text-xs ${c[1]} opacity-60 ml-auto">${sec.items.length} 篇</span>
        </div>
        <ul class="space-y-0.5">${items}</ul>
    </div>`;
}

function latestCard(r) {
    const hasSections = r.sections && r.sections.length > 0;
    const sectionsHtml = hasSections
        ? `<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">${r.sections.map(s => sectionCard(s)).join('')}</div>`
        : '';
    const tagsHtml = r.tags.map(t => `<span class="px-2 py-0.5 bg-white/15 text-white/90 text-xs rounded-full">#${t}</span>`).join(' ');
    return `<div class="bg-gradient-to-br from-[#c96442] to-[#a84e32] rounded-2xl shadow-xl overflow-hidden">
        <div class="p-7 pb-5 text-white">
            <div class="flex items-center justify-between mb-4">
                <div><span class="px-3 py-1 bg-white/20 rounded-full text-sm font-medium">最新发布</span><span class="ml-3 text-orange-100 text-sm">${fmtDate(r.date)}</span></div>
                <span class="text-3xl font-bold text-white/90">${r.articleCount}<span class="text-base font-normal text-orange-200 ml-1">篇</span></span>
            </div>
            <h3 class="text-xl font-bold mb-2">${r.title}</h3>
            <p class="text-orange-100 text-sm mb-3">${r.summary}</p>
            <div class="flex flex-wrap gap-1.5">${tagsHtml}</div>
        </div>
        <div class="bg-warm-50 p-6 pt-5">
            <div class="flex items-center justify-between mb-4">
                <h4 class="text-warm-800 font-bold">今日概览</h4>
                <a href="reports/${r.id}.html" class="inline-flex items-center text-accent hover:text-accent-dark font-medium text-sm transition">
                    阅读完整报告 <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
                </a>
            </div>
            ${sectionsHtml || '<p class="text-warm-400 text-sm">暂无板块数据</p>'}
        </div>
    </div>`;
}

function reportCard(r, i) {
    const catsHtml = (r.categories||[]).slice(0,3).map(c => {
        const sc = secColors[c] || ['bg-gray-50','text-gray-600'];
        return `<span class="px-2 py-0.5 ${sc[0]} ${sc[1]} text-xs rounded-full font-medium">${c}</span>`;
    }).join('');
    return `<div class="bg-white rounded-xl shadow-sm p-5 card-hover report-card border border-warm-200" style="animation-delay:${i*80}ms">
        <div class="mb-3 flex justify-between items-center">
            <span class="text-sm text-accent font-medium">${fmtDate(r.date)}</span>
            <span class="text-xs text-warm-400">${r.articleCount} 篇</span>
        </div>
        <h4 class="text-base font-bold text-warm-800 mb-2 line-clamp-2">${r.title}</h4>
        <p class="text-warm-500 text-sm mb-3 line-clamp-2">${r.summary}</p>
        <div class="flex flex-wrap gap-1.5 mb-3">${catsHtml}</div>
        <a href="reports/${r.id}.html" class="inline-flex items-center text-accent hover:text-accent-dark font-medium text-sm transition">
            阅读全文 <svg class="w-3.5 h-3.5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </a>
    </div>`;
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof reportsData === 'undefined' || !reportsData.length) {
        document.getElementById('latest-report').innerHTML = '<p class="text-center text-warm-400 py-8">暂无报告，运行 pipeline 生成第一期</p>';
        return;
    }
    document.getElementById('latest-report').innerHTML = latestCard(reportsData[0]);
    const rest = reportsData.slice(1);
    document.getElementById('reports-grid').innerHTML = rest.length
        ? rest.map((r,i) => reportCard(r,i)).join('')
        : '<div class="col-span-full text-center py-8 text-warm-400">暂无往期报告</div>';
});
</script>
</body>
</html>"""
