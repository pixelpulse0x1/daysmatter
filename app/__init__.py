"""DaysMatter — Flask application factory with Blueprints."""
import os
import json
import shutil
import random
from flask import Flask

DATA_DIR = "/data"
DB_PATH = os.path.join(DATA_DIR, "database", "main.db")
UPLOADS_PHOTOS_DIR = os.path.join(DATA_DIR, "uploads", "photos")
UPLOADS_COUNTDOWN_DIR = os.path.join(DATA_DIR, "uploads", "countdown_days")
UPLOADS_WISHLIST_DIR = os.path.join(DATA_DIR, "uploads", "wishlist")
UPLOADS_MEMOS_DIR = os.path.join(DATA_DIR, "uploads", "memos")
BACKGROUNDS_DIR = os.path.join(DATA_DIR, "backgrounds")
JSON_DIR = os.path.join(DATA_DIR, "json")

DEFAULT_BG_SRC = os.path.join(os.path.dirname(__file__), "static", "default_bg")
DEFAULT_JSON_SRC = os.path.join(os.path.dirname(__file__), "default_json")

# Ensure all data directories and default files exist
def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def _copy_defaults(src_dir, dst_dir):
    if not os.path.isdir(src_dir):
        return
    _ensure_dir(dst_dir)
    for f in os.listdir(src_dir):
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

def _init_json_file(filepath, default_content):
    """Create a JSON file with default content if it doesn't exist."""
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_content, f, ensure_ascii=False, indent=2)

def init_data_dirs():
    """Ensure all /data subdirectories exist and are seeded with defaults."""
    _ensure_dir(os.path.join(DATA_DIR, "database"))
    _ensure_dir(UPLOADS_PHOTOS_DIR)
    _ensure_dir(UPLOADS_COUNTDOWN_DIR)
    _ensure_dir(UPLOADS_WISHLIST_DIR)
    _ensure_dir(UPLOADS_MEMOS_DIR)
    _ensure_dir(BACKGROUNDS_DIR)
    _ensure_dir(JSON_DIR)
    _ensure_dir(os.path.join(DATA_DIR, "log"))

    # Seed default backgrounds if backgrounds/ is empty
    if os.path.isdir(BACKGROUNDS_DIR) and not os.listdir(BACKGROUNDS_DIR):
        if os.path.isdir(DEFAULT_BG_SRC):
            _copy_defaults(DEFAULT_BG_SRC, BACKGROUNDS_DIR)

    # Seed default JSON configs
    # Determine default header_bg: first image in backgrounds/
    default_header_bg = ""
    if os.path.isdir(BACKGROUNDS_DIR):
        for f in sorted(os.listdir(BACKGROUNDS_DIR)):
            if os.path.splitext(f)[1].lower() in (".jpg",".jpeg",".png",".webp",".gif",".bmp"):
                default_header_bg = f
                break

    _init_json_file(os.path.join(JSON_DIR, "settings.json"), {
        "language": "zh",
        "wallpaper": "",
        "wallpaper_random": True,
        "wallpaper_interval": 1,
        "expired_color": "rgb(150,150,150)",
        "soon_color": "rgb(255,199,206)",
        "mid_color": "rgb(255,217,102)",
        "quote_interval": 10,
        "header_bg": default_header_bg,
        "header_bg_type": "image",
        "header_bg_color": "#ffffff",
        "bg_type": "image",
        "bg_color": "#f8f6f2",
        "bg_opacity": 0.6,
        "debug_logging": False,
    })

    _init_json_file(os.path.join(JSON_DIR, "quotes.json"), {
        "quotes": [
            "古人学问无遗力，少壮工夫老始成。纸上得来终觉浅，绝知此事要躬行。",
            "知止而后有定，定而后能静，静而后能安，安而后能虑，虑而后能得。",
            "物有本末，事有终始。知所先后，则近道矣。",
            "念念不忘，必有回响",
            "苟有恒，何必三更眠、五更起；最无益，莫过一日曝、十日寒",
            "凡心所向，素履所往，生如逆旅，一苇以航。",
            "岁月是一场有去无回的旅行，好的坏的都是风景。",
            "星光不问赶路人，时光不负有心人。",
        ]
    })

    _init_json_file(os.path.join(JSON_DIR, "lang_zh.json"), {
        "DaysMatter": "倒数日",
        "Countdown Days": "倒数日",
        "Wishlist": "愿望单",
        "Memo": "备忘录",
        "Settings": "设置",
        "Logout": "登出星空",
        "Home": "首页",
        "All": "全部",
        "Archive": "归档",
        "Default": "默认",
        "Add Event": "添加事项",
        "Edit Event": "编辑事项",
        "Event Name": "事项名称",
        "Enter event name": "输入事件名称",
        "Target Date": "目标日",
        "Category": "所属倒数本",
        "Pin": "置顶",
        "Show on Home": "首页展示",
        "Repeat": "重复",
        "No Repeat": "不重复",
        "Every": "每",
        "Day(s)": "日",
        "Week(s)": "周",
        "Month(s)": "月",
        "Year(s)": "年",
        "Include start day (+1 day)": "包含起始日（+1天）",
        "Highlight": "高亮醒目",
        "Event Color": "事件颜色",
        "Icon": "图标",
        "Note": "备注",
        "Additional notes...": "补充事项...",
        "Image": "附图",
        "Add Image": "上传附图",
        "Archive event": "归档",
        "Restore": "回档",
        "Delete": "删除",
        "Save": "保存",
        "Today": "今天",
        "Header Display": "页头显示",
        "Show current time": "显示当前时间（精确到秒）",
        "Show days left in year": "显示今年剩余天数",
        "Wallpaper": "壁纸",
        "Wallpaper Management": "壁纸管理",
        "Upload Wallpaper": "上传壁纸",
        "Clear Wallpaper": "清除壁纸",
        "Random Mode": "随机模式",
        "Switch interval (hours)": "切换间隔（小时）",
        "BGOpacity": "内容区透明度",
        "Select from gallery": "从图库选择",
        "Apply": "应用",
        "Quotes": "励志语",
        "Separate quotes with blank lines...": "每条励志语之间用空行分隔...",
        "Switch interval (seconds)": "切换间隔（秒）",
        "Color Hints": "颜色提示",
        "Expired background": "已过期底色",
        "Within 30 days background": "未来30天内底色",
        "Within 31-90 days background": "未来31-90天底色",
        "Language": "语言",
        "Category Management": "倒数本管理",
        "Manage Categories": "管理倒数本",
        "New category name": "新倒数本名称",
        "Add": "添加",
        "Data Backup": "数据备份",
        "Export Backup": "导出备份",
        "Debug Logging": "调试日志",
        "Enable debug logging": "开启调试日志",
        "Debug logging warning": "开启调试日志会记录系统运行详细信息并占用额外空间，仅建议在排查故障时开启。是否继续？",
        "Image Management": "附件管理",
        "Manage Attachments": "管理附件",
        "Refresh": "刷新",
        "No images": "暂无附图",
        "Preview": "预览",
        "{n} days until New Year": "新年还有 {n} 天",
        "Sunday": "周日",
        "Monday": "周一",
        "Tuesday": "周二",
        "Wednesday": "周三",
        "Thursday": "周四",
        "Friday": "周五",
        "Saturday": "周六",
        "Sun": "周日",
        "Mon": "周一",
        "Tue": "周二",
        "Wed": "周三",
        "Thu": "周四",
        "Fri": "周五",
        "Sat": "周六",
        "Confirm delete event?": "确定删除这个事项吗？",
        "Confirm again? This cannot be undone.": "再次确认删除？此操作不可恢复。",
        "Confirm archive?": "确定该事项已经完成？完成后将移入归档。",
        "Confirm restore?": "确定将该事项移出归档？",
        "Confirm delete category?": "确定删除此倒数本？其中的事项将移至默认倒数本。",
        "Confirm delete image?": "删除此附图？将从所有事项中移除。",
        "Please enter event name": "请输入事项名称",
        "Please select a target date": "请选择目标日",
        "No events yet.": "暂无事项，点击右上角添加",
        "Saved successfully": "保存成功",
        "Settings saved.": "设置已保存。",
        "Header Background": "页头背景",
        "Background Type": "背景类型",
        "Image": "图片",
        "Color": "颜色",
        "Select Background Color": "选择背景颜色",
        "Repeat interval (0=off)": "重复间隔（0=关闭）",
        "Saving...": "保存中...",
        "Saved!": "已保存!",
        # Wishlist
        "Add Wish": "添加愿望",
        "Edit Wish": "编辑愿望",
        "Wish Title": "愿望标题",
        "Enter wish title": "输入愿望标题",
        "Description": "描述",
        "Wish description...": "愿望描述...",
        "Life Ripple": "人生影响力",
        "Heart's Fire": "内心渴望值",
        "Difficulty": "实现难度",
        "Status": "状态",
        "All": "全部",
        "Draft": "草稿",
        "Active": "进行中",
        "Achieved": "已达成",
        "Steps": "步骤拆解",
        "Add Step": "添加步骤",
        "Step content": "步骤内容",
        "Vision Board": "附图",
        "Upload Image": "上传图片",
        "Max 20 images": "最多上传30张",
        "Upload Attachments": "上传附图",
        "Linked Countdown": "关联倒数日",
        "None": "无",
        "days left": "离目标还剩 {n} 天",
        "days overdue": "已超期 {n} 天",
        "Priority Score": "优先级分值",
        "North Star": "人生核心目标",
        "Sleeping Giant": "重要但需破冰",
        "Sweet Treat": "高多巴胺奖励",
        "Leisure Cloud": "随缘心愿",
        "No wishes yet.": "暂无愿望，点击右上角添加",
        "Confirm delete wish?": "确定删除这个愿望吗？",
        "Please enter wish title": "请输入愿望标题",
        "Celebrate!": "庆祝达成!",
        "Quadrant Stats": "象限分布",
        "Achieved on": "达成于",
        "Total Achieved": "累计达成",
        "Quick Add (Ctrl+K)": "快速添加 (Ctrl+K)",
        "Quick add wish...": "快速输入愿望...",
        "Journey": "心路历程",
        "Edit Journey": "编辑心路历程",
        "Save Journey": "保存心路历程",
        "Cancel": "取消",
        "No journey yet.": "暂无记录，点击管理心路历程添加",
        "Manage Journey": "管理心路历程",
        "Journey History": "心路历程记录",
        "New Entry": "新增记录",
        "Edit Entry": "编辑记录",
        "Delete Entry": "删除记录",
        "Entry Date": "记录日期",
        "Entry Content": "记录内容",
        "Save Entry": "保存记录",
        "Cancel Edit": "取消编辑",
        "Confirm delete entry?": "确定删除这条记录吗？",
        "All Wishes": "全部愿望",
        "High Impact · High Desire": "高影响 · 高渴望",
        "High Impact · Low Desire": "高影响 · 低渴望",
        "Low Impact · High Desire": "低影响 · 高渴望",
        "Low Impact · Low Desire": "低影响 · 低渴望",
        # Memo
        "Memo": "备忘录",
        "Compose": "添加",
        "Subject": "主题",
        "Enter subject": "输入主题",
        "Summary": "摘要",
        "Starred": "星标",
        "All Memos": "全部备忘录",
        "No memos yet.": "暂无备忘录，点击撰写开始",
        "Memo content...": "备忘录内容...",
        "Confirm delete memo?": "确定删除这条备忘录吗？",
        "Cancel edit?": "放弃编辑？未保存的更改将丢失。",
        "Attachments": "附件",
        "No attachments": "暂无附件",
        "Upload Attachment": "上传附件",
        "has attachments": "包含附件",
        "Read": "阅读",
        "Edit": "编辑",
        # Auth / Logout
        "Leave Wish Space": "离开愿望空间",
        "Logout confirm text": "确定要离开吗？下次开启星门需要再次验证身份。",
        "Confirm Logout": "确认退出",
    })

    _init_json_file(os.path.join(JSON_DIR, "lang_en.json"), {})


# Helpers to read/write JSON configs
def read_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_settings():
    return read_json(os.path.join(JSON_DIR, "settings.json"))

def save_settings(data):
    current = get_settings()
    current.update(data)
    write_json(os.path.join(JSON_DIR, "settings.json"), current)

def get_all_quotes():
    """Return quotes list from quotes.json. Populates defaults if empty."""
    path = os.path.join(JSON_DIR, "quotes.json")
    default_quotes = [
        "古人学问无遗力，少壮工夫老始成。纸上得来终觉浅，绝知此事要躬行。",
        "知止而后有定，定而后能静，静而后能安，安而后能虑，虑而后能得。",
        "物有本末，事有终始。知所先后，则近道矣。",
        "我大体上欢喜冷静、沉着、稳重、刚毅，以出世精神做入世事业，尊崇理性和意志，却也不菲薄情感和想象。我的思想就抱着这个中心旋转，我不另找玄学或形而上学的基础",
        "念念不忘，必有回响",
        "苟有恒，何必三更眠、五更起；最无益，莫过一日曝、十日寒",
        "苟能发奋自立，则家塾可读书，即旷野之地，热闹之场，亦可读书，负薪牧豕，皆可读书。苟不能发奋自立，则家塾不宜读书，即清净之乡，神仙之境，皆不能读书。何必择地？何必择时？但自问立志之真不真耳。",
        "一日不读书，尘生其中；两日不读书，言语乏味；三日不读书，面目可憎。",
        "凡心所向，素履所往，生如逆旅，一苇以航。",
        "每一处风景都有它的故事，每一个人都是这故事的讲述者。",
        "岁月是一场有去无回的旅行，好的坏的都是风景。",
        "星光不问赶路人，时光不负有心人。",
    ]
    if os.path.exists(path):
        data = read_json(path)
        quotes = data.get("quotes", [])
        if quotes:
            return quotes
    # File doesn't exist or quotes are empty — write defaults
    write_json(path, {"quotes": default_quotes})
    return default_quotes

def get_lang(lang_code):
    """Load language mapping. Returns {} for 'en' (keys are English)."""
    if lang_code == "en":
        return {}
    filepath = os.path.join(JSON_DIR, f"lang_{lang_code}.json")
    if os.path.exists(filepath):
        return read_json(filepath)
    return {}

def get_wallpaper_list():
    """Scan backgrounds/ for image files, return list of filenames."""
    files = []
    valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
    if os.path.isdir(BACKGROUNDS_DIR):
        for f in sorted(os.listdir(BACKGROUNDS_DIR)):
            if os.path.splitext(f)[1].lower() in valid_exts:
                files.append(f)
    return files

def get_random_wallpaper():
    """Pick a random wallpaper from backgrounds/."""
    wallpapers = get_wallpaper_list()
    return random.choice(wallpapers) if wallpapers else None


def create_app():
    """Flask application factory."""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Initialize data directories
    init_data_dirs()

    # Initialize auth system (Flask-Login + route protection)
    from app.routes.auth import auth_bp, init_auth
    init_auth(app)
    app.register_blueprint(auth_bp)

    # Register blueprints
    from app.routes.daysmatter import daysmatter_bp
    from app.routes.settings import settings_bp
    from app.routes.wishlist import wishlist_bp
    from app.routes.memo import memo_bp

    app.register_blueprint(daysmatter_bp)
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(wishlist_bp, url_prefix="/wishlist")
    app.register_blueprint(memo_bp, url_prefix="/memo")

    return app
