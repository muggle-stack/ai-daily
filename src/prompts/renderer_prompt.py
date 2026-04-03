"""HTML 渲染模板（暖调 Claude 卡片风格）。纯 Python 模板，不使用 LLM。"""

CATEGORY_EMOJI_MAP: dict[str, str] = {
    "模型发布": "rocket",
    "开源项目": "code",
    "研究论文": "science",
    "产品动态": "devices",
    "行业观点": "lightbulb",
    "工具技巧": "build",
}

# 分类对应的主题色，循环使用
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
<title>AI Daily · {date}</title>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,300,0,0&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: #fbf9f6;
    color: #4a403a;
    font-family: 'Noto Sans SC', system-ui, -apple-system, sans-serif;
    line-height: 1.8;
    min-height: 100vh;
}}
.material-symbols-rounded {{
    font-family: 'Material Symbols Rounded' !important;
    font-weight: 300 !important;
    font-style: normal;
    display: inline-block;
    line-height: 1;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24 !important;
}}
.container {{
    max-width: 780px;
    margin: 0 auto;
    padding: 48px 24px 40px;
}}
.header {{
    text-align: center;
    margin-bottom: 40px;
}}
.header h1 {{
    font-size: 2.8em;
    font-weight: 700;
    color: #c96442;
    line-height: 1.2;
    text-shadow: 2px 2px 0px rgba(201, 100, 66, 0.1);
    margin-bottom: 8px;
}}
.header .date {{
    color: #8a7f76;
    font-size: 1.05em;
    font-weight: 500;
}}
.header .stats {{
    color: #a89f96;
    font-size: 0.85em;
    margin-top: 4px;
}}
.overview {{
    background: #ffffff;
    border: 1px solid rgb(218, 216, 212);
    border-left: 4px solid #c96442;
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 36px;
    color: #4a403a;
    font-size: 0.95em;
    font-weight: 500;
    box-shadow: 0 4px 16px -4px rgba(74, 64, 58, 0.06);
}}
.category-section {{
    margin-bottom: 12px;
}}
.category-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 32px 0 16px 0;
    font-size: 1.35em;
    font-weight: 700;
    line-height: 1.25;
}}
.category-header .material-symbols-rounded {{
    font-size: 28px;
}}
.card {{
    background: #ffffff;
    border: 1px solid rgb(218, 216, 212);
    border-radius: 24px;
    padding: 0;
    margin-bottom: 16px;
    box-shadow: 0 10px 30px -10px rgba(74, 64, 58, 0.08);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    overflow: hidden;
}}
.card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 14px 36px -10px rgba(74, 64, 58, 0.14);
}}
.card-title-box {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 24px 8px;
}}
.card-title-box .material-symbols-rounded {{
    font-size: 24px;
    flex-shrink: 0;
}}
.card h3 {{
    font-size: 1.05em;
    font-weight: 700;
    line-height: 1.35;
}}
.card-body {{
    padding: 0 24px 20px;
}}
.card .summary {{
    color: #141413;
    font-size: 0.92em;
    font-weight: 500;
    line-height: 1.7;
    margin-bottom: 12px;
}}
.card .meta {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    font-size: 0.8em;
    color: #8a7f76;
}}
.card .meta a {{
    color: #c96442;
    text-decoration: none;
    font-weight: 500;
}}
.card .meta a:hover {{
    text-decoration: underline;
}}
.tag {{
    display: inline-block;
    background: rgb(240, 239, 235);
    color: #4a403a;
    font-size: 0.78em;
    padding: 2px 10px;
    border-radius: 10px;
    border: 0.5px solid #d1cfcc;
    font-weight: 500;
}}
.keywords-section {{
    margin-top: 40px;
    text-align: center;
    background: #ffffff;
    border: 1px solid rgb(218, 216, 212);
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 4px 16px -4px rgba(74, 64, 58, 0.06);
}}
.keywords-section h2 {{
    color: #4a403a;
    font-size: 1.15em;
    font-weight: 700;
    margin-bottom: 14px;
}}
.keywords-section .tags {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
}}
.divider {{
    border: none;
    border-top: 1px solid rgb(218, 216, 212);
    margin: 8px 0 0 0;
}}
.footer {{
    text-align: center;
    color: #a89f96;
    font-size: 0.8em;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid rgb(218, 216, 212);
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>AI Daily</h1>
        <div class="date">{date}</div>
        <div class="stats">共 {article_count} 篇精选，来自 {source_count} 个信息源</div>
    </div>
    <div class="overview">{overview}</div>
    {content}
    <div class="keywords-section">
        <h2>今日关键词</h2>
        <div class="tags">{keywords_html}</div>
    </div>
    <div class="footer">
        由 AI Daily 自动生成 · {generated_at}
    </div>
</div>
</body>
</html>"""

CATEGORY_SECTION_TEMPLATE = """<div class="category-section">
    <div class="category-header" style="color: {color};">
        <span class="material-symbols-rounded" style="color: {color};">{icon}</span>
        {category}
    </div>
    {cards}
</div>
<hr class="divider">"""

ARTICLE_CARD_TEMPLATE = """<div class="card">
    <div class="card-title-box">
        <span class="material-symbols-rounded" style="color: {color};">article</span>
        <h3 style="color: {color};">{title}</h3>
    </div>
    <div class="card-body">
        <div class="summary">{summary}</div>
        <div class="meta">
            <a href="{url}" target="_blank" rel="noopener">原文链接 ↗</a>
            <span>· {source}</span>
            <span>· {tags}</span>
        </div>
    </div>
</div>"""
