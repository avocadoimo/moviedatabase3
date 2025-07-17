# app.py 修正版（興収推移データ機能追加）

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from functools import wraps 
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import or_, desc, asc
from flask_paginate import get_page_parameter
from datetime import datetime, timedelta
import os
import re
import random
import pandas as pd
import json
import requests
import traceback
import logging
from bs4 import BeautifulSoup
from collections import Counter
import time
from urllib.parse import quote

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# セッション設定
app.secret_key = os.environ.get("SECRET_KEY", "movie_admin_secret_key_1529")
app.permanent_session_lifetime = timedelta(hours=24)

# パスワード設定
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1529")
SITE_ACCESS_PASSWORD = os.environ.get("SITE_ACCESS_PASSWORD", "imo4649")

def parse_date(s):
    try:
        return datetime.strptime(s, "%Y/%m/%d")
    except:
        return datetime.min 

# PostgreSQL接続設定（Render対応版）
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL環境変数が設定されていません")
    # 開発環境用のフォールバック
    database_url = "sqlite:///movie_dev.db"
    print("⚠️ 開発用SQLiteデータベースを使用します")

# RenderのpostgreSQL URLをpsqlalchemy形式に変換
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL最適化設定
if database_url.startswith("postgresql://"):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'client_encoding': 'utf8'
    }

db = SQLAlchemy(app)

# Flask-Migrate初期化
migrate = Migrate(app, db)

# データベースモデル定義
class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(50))
    title = db.Column(db.String(200), nullable=False)
    revenue = db.Column(db.Float)
    year = db.Column(db.Integer)
    release_date = db.Column(db.String(20))
    category = db.Column(db.String(50))
    distributor = db.Column(db.String(200))
    description = db.Column(db.Text)
    director = db.Column(db.String(200))
    author = db.Column(db.String(200))
    actor = db.Column(db.Text)
    scriptwriter = db.Column(db.String(200))
    producer = db.Column(db.String(200))
    copyright = db.Column(db.String(500))
    genre = db.Column(db.String(200))

class BoxOfficeData(db.Model):
    __tablename__ = 'box_office_data'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    title = db.Column(db.String(200))
    week = db.Column(db.String(20))  # 公開週（例：「第1週」）
    weekend_revenue = db.Column(db.String(50))  # 週末興収
    total_revenue = db.Column(db.String(50))  # 累計興収
    weekly_revenue = db.Column(db.String(50))  # 週間興収
    match_score = db.Column(db.Integer)  # マッチスコア
    
    __table_args__ = (
        db.Index('idx_box_office_movie_id', 'movie_id'),
        db.Index('idx_box_office_title', 'title'),
    )

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300))
    author = db.Column(db.String(100))
    category = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class TrendingData(db.Model):
    __tablename__ = 'trending_data'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    post_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_trending_date_title', 'date', 'movie_title'),
        db.Index('idx_trending_date', 'date'),
    )

# デコレータ
def site_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.endpoint == 'site_login':
            return f(*args, **kwargs)
        if not session.get('site_authenticated'):
            return redirect(url_for('site_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# データベース初期化関数
def init_database_safe():
    """安全なデータベース初期化"""
    try:
        with app.app_context():
            # テーブル作成
            db.create_all()
            print("✅ データベーステーブル作成完了")
            
            # 接続確認
            try:
                if database_url.startswith("postgresql://"):
                    result = db.session.execute(db.text('SELECT version()'))
                    version = result.fetchone()[0]
                    print(f"✅ PostgreSQL接続確認: {version[:50]}...")
                else:
                    print("✅ SQLite接続確認完了")
            except Exception as e:
                print(f"⚠️ 接続確認スキップ: {e}")
            
            return True
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        return False

class TrendingDataManager:
    def __init__(self, app_instance):
        self.app = app_instance
        try:
            import MeCab
            self.mecab = MeCab.Tagger('-Owakati')
        except:
            print("⚠️ MeCab未使用（形態素解析なし）")
            self.mecab = None
        
        print("✅ TrendingDataManager初期化完了（映画ID照合対応版）")
    
    def get_trending_by_date(self, target_date=None, limit=10):
        with self.app.app_context():
            try:
                if target_date is None:
                    latest_date = db.session.query(TrendingData.date).order_by(desc(TrendingData.date)).first()
                    if latest_date:
                        target_date = latest_date[0]
                    else:
                        print("📊 トレンドデータが見つかりません")
                        return []
                
                # 指定日のトレンドデータを取得（投稿数順）
                trending_list = TrendingData.query.filter_by(date=target_date)\
                                                 .order_by(desc(TrendingData.post_count))\
                                                 .limit(limit)\
                                                 .all()
                
                if not trending_list:
                    print(f"📊 {target_date} のデータなし")
                    return []
                
                result = []
                for i, trend in enumerate(trending_list, 1):
                    # 映画データを正確に照合（映画ID基準）
                    movie_data = self.find_movie_by_title_enhanced(trend.movie_title)
                    
                    trend_info = {
                        'rank': i,
                        'title': trend.movie_title,
                        'post_count': trend.post_count,
                        'date': trend.date,
                        'movie_data': movie_data,
                        'change': self.calculate_change(trend.movie_title, target_date),
                        'trend_score': min(100, (trend.post_count / max(1, trending_list[0].post_count)) * 100),
                        'word_cloud': self.generate_enhanced_wordcloud(trend.movie_title, movie_data)
                    }
                    result.append(trend_info)
                
                print(f"📈 {target_date}のトレンド取得: {len(result)}件")
                return result
                
            except Exception as e:
                print(f"❌ トレンド取得エラー: {e}")
                return []
    
    def find_movie_by_title_enhanced(self, title):
        """強化された映画データ検索（完全一致優先）"""
        try:
            # 1. 完全一致検索
            movie = Movie.query.filter(Movie.title == title).first()
            if movie:
                return self.format_movie_data(movie)
            
            # 2. 部分一致検索（前方一致）
            movie = Movie.query.filter(Movie.title.like(f"{title}%")).first()
            if movie:
                return self.format_movie_data(movie)
            
            # 3. 部分一致検索（後方一致）
            movie = Movie.query.filter(Movie.title.like(f"%{title}")).first()
            if movie:
                return self.format_movie_data(movie)
            
            # 4. 含む検索
            movie = Movie.query.filter(Movie.title.contains(title)).first()
            if movie:
                return self.format_movie_data(movie)
            
            # 5. 逆方向検索（タイトルが含まれているか）
            movies = Movie.query.limit(500).all()  # パフォーマンス考慮
            for movie in movies:
                if movie.title and (movie.title in title or title in movie.title):
                    return self.format_movie_data(movie)
            
            # 6. キーワード分割検索
            title_words = title.replace('劇場版', '').replace('「', '').replace('」', '').split()
            for word in title_words:
                if len(word) > 2:  # 短すぎる単語は除外
                    movie = Movie.query.filter(Movie.title.contains(word)).first()
                    if movie:
                        print(f"🔍 キーワード '{word}' で照合: {title} → {movie.title}")
                        return self.format_movie_data(movie)
            
            return None
            
        except Exception as e:
            print(f"❌ 映画検索エラー ({title}): {e}")
            return None
    
    def format_movie_data(self, movie):
        """映画データの標準化フォーマット"""
        return {
            'id': movie.id,
            'movie_id': movie.movie_id,
            'title': movie.title,
            'revenue': movie.revenue,
            'year': movie.year,
            'director': movie.director,
            'category': movie.category,
            'genre': movie.genre,
            'distributor': movie.distributor,
            'description': movie.description,
            'poster_path': f"posters/{movie.movie_id}.jpg" if movie.movie_id else None
        }
    
    def generate_enhanced_wordcloud(self, movie_title, movie_data):
        """強化されたワードクラウド生成"""
        
        # 映画固有のキーワード辞書
        movie_keywords = {
            '鬼滅の刃': ['感動', '泣いた', '最高', '劇場版', 'アニメ', '無限列車', '炭治郎', '禰豆子', '煉獄', '映像美', '音楽', 'LiSA'],
            '千と千尋の神隠し': ['ジブリ', '宮崎駿', 'スタジオジブリ', '千尋', 'ハク', '湯婆婆', 'カオナシ', '神秘的', '美しい', '名作', '感動'],
            '君の名は': ['新海誠', '瀧', '三葉', '入れ替わり', '隕石', '糸守', '美しい', '音楽', 'RADWIMPS', '感動', '恋愛'],
            'タイタニック': ['ジャック', 'ローズ', '恋愛', '悲劇', '感動', '名作', 'ディカプリオ', '船', '氷山', '永遠'],
            'アナと雪の女王': ['エルサ', 'アナ', '雪だるま', 'オラフ', 'Let It Go', 'ディズニー', '魔法', '姉妹', '歌', 'ミュージカル'],
            'ミッション': ['トム・クルーズ', 'アクション', 'スタント', 'ハラハラ', '迫力', 'スパイ', 'イーサン・ハント', '危険', '手に汗'],
            'スーパーマン': ['ヒーロー', 'DC', 'アメコミ', '飛行', '正義', 'クラーク', 'スーパーパワー', '守る', '希望'],
            'ルパン三世': ['次元', '五右衛門', '不二子', '銭形', '泥棒', 'カリオストロ', 'アニメ', '冒険', 'かっこいい'],
            'ドラえもん': ['のび太', 'しずか', 'ジャイアン', 'スネ夫', '未来', 'ひみつ道具', 'ファミリー', '感動', '友情'],
            'クレヨンしんちゃん': ['しんのすけ', 'ひろし', 'みさえ', 'ひまわり', '春日部', '面白い', 'ファミリー', '笑った', 'ケツだけ星人'],
            'アンパンマン': ['バイキンマン', 'ドキンちゃん', 'しょくぱんまん', 'カレーパンマン', '正義', '子供', '優しい', '勇気'],
            'ワンピース': ['ルフィ', 'ゾロ', 'ナミ', 'サンジ', '海賊', '仲間', '冒険', '感動', '友情', '夢', 'ONE PIECE'],
            'コナン': ['真実', '推理', 'ミステリー', '事件', '解決', '蘭', '園子', '服部', '黒ずくめ', '頭脳戦'],
            'ジブリ': ['宮崎駿', '美しい', '自然', '環境', '成長', '冒険', 'トトロ', 'ナウシカ', '魔女の宅急便'],
            'ポケモン': ['ピカチュウ', 'サトシ', '冒険', 'バトル', 'ゲットだぜ', '友達', 'ポケットモンスター', '進化'],
            'エヴァンゲリオン': ['シンジ', 'レイ', 'アスカ', '使徒', 'NERV', 'ロボット', '心理', '哲学', '庵野秀明'],
            'ガンダム': ['モビルスーツ', 'ニュータイプ', '戦争', 'アムロ', 'シャア', 'ザク', 'ビーム', 'リアルロボット']
        }
        
        # 映画タイトルに対応するキーワードを検索
        keywords = []
        colors = ['#1a73e8', '#34a853', '#ea4335', '#fbbc04', '#9c27b0', '#ff6f00', '#795548', '#607d8b']
        
        # 完全一致検索
        matched_keywords = None
        for key, words in movie_keywords.items():
            if key in movie_title:
                matched_keywords = words
                break
        
        # 部分一致検索
        if not matched_keywords:
            for key, words in movie_keywords.items():
                if any(word in movie_title for word in key.split()):
                    matched_keywords = words
                    break
        
        # デフォルトキーワード
        if not matched_keywords:
            matched_keywords = ['面白い', '最高', '感動', '泣いた', '笑った', '見た', '良かった', 'おすすめ']
        
        # 映画データから追加キーワード生成
        if movie_data:
            if movie_data.get('genre'):
                genres = movie_data['genre'].split('、')
                matched_keywords.extend(genres[:3])  # ジャンルを最大3つ追加
            
            if movie_data.get('director'):
                matched_keywords.append(movie_data['director'])
            
            if movie_data.get('year') and movie_data['year'] >= 2020:
                matched_keywords.append('最新作')
            elif movie_data.get('year') and movie_data['year'] <= 2000:
                matched_keywords.append('名作')
        
        # キーワードリストを作成（重複除去）
        unique_keywords = list(dict.fromkeys(matched_keywords))[:10]  # 最大10個
        
        for i, word in enumerate(unique_keywords):
            keywords.append({
                'text': word,
                'size': max(12, 26 - (i * 2)),  # 12-26pxの範囲
                'color': colors[i % len(colors)],
                'count': max(1, 20 - i)  # 出現回数（仮想値）
            })
        
        return keywords
    
    def calculate_change(self, title, current_date):
        """投稿数変化率計算（前日比）"""
        try:
            from datetime import datetime, timedelta
            
            current_date_obj = datetime.strptime(current_date, '%Y/%m/%d')
            prev_date_obj = current_date_obj - timedelta(days=1)
            prev_date = prev_date_obj.strftime('%Y/%m/%d')
            
            current_data = TrendingData.query.filter_by(date=current_date, movie_title=title).first()
            prev_data = TrendingData.query.filter_by(date=prev_date, movie_title=title).first()
            
            if current_data and prev_data and prev_data.post_count > 0:
                change_rate = ((current_data.post_count - prev_data.post_count) / prev_data.post_count) * 100
                if change_rate > 0:
                    return f"+{change_rate:.1f}%"
                else:
                    return f"{change_rate:.1f}%"
            elif current_data and not prev_data:
                return "NEW"
            
            return "-%"
            
        except Exception as e:
            print(f"❌ 変化率計算エラー ({title}): {e}")
            return "-%"
    
    def get_available_dates(self):
        """利用可能な日付一覧取得"""
        try:
            with self.app.app_context():
                dates = db.session.query(TrendingData.date).distinct().order_by(desc(TrendingData.date)).all()
                date_list = [date[0] for date in dates]
                return date_list
        except Exception as e:
            print(f"❌ 日付取得エラー: {e}")
            return []

# AIチャットボット
class MovieAnalysisBot:
    def __init__(self):
        self.responses = {
            "投稿数": [
                "SNS投稿数データを見ると、リアルタイムで話題の映画がわかりますね。投稿数が多い作品ほど注目度が高い傾向があります。",
                "Yahoo!リアルタイム検索のデータから、どの映画が今話題になっているかを分析できます。"
            ],
            "興行収入": [
                "興行収入とSNS投稿数には相関関係があることが多いです。話題性が高い映画ほど劇場に足を運ぶ人が多くなります。",
                "投稿数ランキング上位の映画は、興行収入でも好成績を残すことが多いですね。"
            ],
            "トレンド": [
                "リアルタイムのSNS投稿数から見ると、今最も話題になっている映画がわかります。",
                "投稿数の推移を見ることで、映画の人気の変化も追跡できます。"
            ],
            "ランキング": [
                "投稿数ランキングでは、リアルタイムで話題の映画が上位に来ます。興行収入ランキングとは違った視点で人気を見ることができます。",
                "SNS投稿数ランキングは、特に若年層に人気の作品が上位に来やすい傾向があります。"
            ]
        }
    
    def get_response(self, user_message):
        user_message = user_message.lower()
        
        for keyword, responses in self.responses.items():
            if keyword in user_message:
                return random.choice(responses)
        
        return "SNS投稿数データと映画データベースを組み合わせて、様々な角度から映画を分析できます。どんなことが知りたいですか？"

# グローバル変数
trending_manager = None

def init_trending_manager():
    global trending_manager
    print("📈 TrendingDataManager初期化中...")
    trending_manager = TrendingDataManager(app)
    print("✅ TrendingDataManager初期化完了")

# 興収推移データ関連の関数
def parse_revenue_string(revenue_str):
    """興収文字列を数値に変換"""
    if not revenue_str or revenue_str == '-':
        return 0.0
    
    # カンマを削除
    revenue_str = revenue_str.replace(',', '')
    
    # 億円単位の処理
    if '億' in revenue_str:
        return float(revenue_str.replace('億', ''))
    
    # 数値のみの場合（万円単位と仮定）
    try:
        return float(revenue_str) / 10000  # 万円を億円に変換
    except:
        return 0.0

def calculate_week_over_week_change(current_value, previous_value):
    """前週比を計算"""
    if previous_value is None or previous_value == 0:
        return None
    
    change = ((current_value - previous_value) / previous_value) * 100
    return round(change, 1)

def get_box_office_rankings(movie):
    """興収ランキングを取得"""
    rankings = {}
    
    try:
        # 全作品での順位
        all_movies = Movie.query.filter(Movie.revenue.isnot(None)).order_by(Movie.revenue.desc()).all()
        for i, m in enumerate(all_movies, 1):
            if m.id == movie.id:
                rankings['all'] = i
                break
        
        # 年別順位
        if movie.year:
            year_movies = Movie.query.filter(Movie.year == movie.year, Movie.revenue.isnot(None)).order_by(Movie.revenue.desc()).all()
            for i, m in enumerate(year_movies, 1):
                if m.id == movie.id:
                    rankings['year'] = i
                    break
        
        # 邦画・洋画別順位
        if movie.category:
            category_movies = Movie.query.filter(Movie.category == movie.category, Movie.revenue.isnot(None)).order_by(Movie.revenue.desc()).all()
            for i, m in enumerate(category_movies, 1):
                if m.id == movie.id:
                    rankings['category'] = i
                    break
        
        # ジャンル別順位（アニメなど）
        if movie.genre and 'アニメ' in movie.genre:
            anime_movies = Movie.query.filter(Movie.genre.contains('アニメ'), Movie.revenue.isnot(None)).order_by(Movie.revenue.desc()).all()
            for i, m in enumerate(anime_movies, 1):
                if m.id == movie.id:
                    rankings['anime'] = i
                    break
        
    except Exception as e:
        print(f"❌ ランキング取得エラー: {e}")
    
    return rankings

# ===== ルート定義 =====

@app.route("/site-login", methods=['GET', 'POST'])
def site_login():
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        
        if password == SITE_ACCESS_PASSWORD:
            session['site_authenticated'] = True
            session.permanent = True
            print("✅ サイトアクセス認証成功")
            
            next_page = request.args.get('next') or request.form.get('next', url_for('search'))
            return redirect(next_page)
        else:
            print("❌ サイトアクセス認証失敗")
            return render_template('site_login.html', error="パスワードが正しくありません")
    
    if session.get('site_authenticated'):
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('search'))
    
    return render_template('site_login.html')

@app.route("/admin/login", methods=['GET', 'POST'])
@site_access_required
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        
        if password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            session.permanent = True
            print("✅ 管理者ログイン成功")
            return redirect(url_for('admin_dashboard'))
        else:
            print("❌ 管理者ログイン失敗")
            return render_template('admin_login.html', error="パスワードが正しくありません")
    
    return render_template('admin_login.html')

@app.route("/admin/logout")
@site_access_required
def admin_logout():
    session.pop('admin_authenticated', None)
    print("✅ 管理者ログアウト")
    return redirect(url_for('search'))

@app.route("/api/search-suggestions")
@site_access_required
def search_suggestions():
    query_type = request.args.get('type')
    term = request.args.get('term', '').strip()
    
    if not term or len(term) < 2:
        return jsonify([])
    
    suggestions = []
    
    try:
        if query_type == 'title':
            results = Movie.query.filter(Movie.title.contains(term)).limit(10).all()
            suggestions = [movie.title for movie in results]
        elif query_type == 'director':
            results = db.session.query(Movie.director).filter(
                Movie.director.contains(term), Movie.director.isnot(None)
            ).distinct().limit(10).all()
            suggestions = [r[0] for r in results if r[0]]
        elif query_type == 'actor':
            results = db.session.query(Movie.actor).filter(
                Movie.actor.contains(term), Movie.actor.isnot(None)
            ).distinct().limit(10).all()
            suggestions = [r[0] for r in results if r[0]]
        elif query_type == 'distributor':
            results = db.session.query(Movie.distributor).filter(
                Movie.distributor.contains(term), Movie.distributor.isnot(None)
            ).distinct().limit(10).all()
            suggestions = [r[0] for r in results if r[0]]
        elif query_type == 'genre':
            results = db.session.query(Movie.genre).filter(
                Movie.genre.contains(term), Movie.genre.isnot(None)
            ).distinct().limit(10).all()
            genre_set = set()
            for r in results:
                if r[0]:
                    for genre in r[0].split(','):
                        genre = genre.strip()
                        if term.lower() in genre.lower():
                            genre_set.add(genre)
            suggestions = list(genre_set)[:10]
    except Exception as e:
        print(f"❌ 検索候補取得エラー: {e}")
        suggestions = []
    
    return jsonify(suggestions[:10])

@app.route("/")
@app.route("/search")
@site_access_required
def search():
    query = Movie.query

    # 基本検索パラメータ
    title = request.args.get('title')
    director = request.args.get('director')
    actor = request.args.get('actor')
    distributor = request.args.get('distributor')
    category = request.args.get('category')
    min_revenue = request.args.get('min_revenue')
    max_revenue = request.args.get('max_revenue')
    
    # 新しい検索パラメータ
    years = request.args.getlist('years')
    genres = request.args.getlist('genres')
    year_match = request.args.get('year_match', 'any')
    genre_match = request.args.get('genre_match', 'any')
    
    # 並び替えパラメータの処理を修正
    order_by = request.args.get('order_by', 'revenue')  # デフォルトは興行収入
    sort = request.args.get('sort', 'desc')  # デフォルトは降順

    # 基本フィルタリング
    if title:
        query = query.filter(Movie.title.contains(title))
    if director:
        query = query.filter(Movie.director.contains(director))
    if actor:
        query = query.filter(Movie.actor.contains(actor))
    if distributor:
        # 配給会社のエイリアス処理
        groups = [
            ['WB', 'ワーナー', 'ワーナー・ブラザース映画'],
            ['SPE', 'ソニー・ピクチャーズエンタテインメント'],
            ['BV', 'WDS', 'ウォルト・ディズニー・ジャパン', 'ブエナビスタ', 'ディズニー']
        ]

        distributor_aliases = {}
        for group in groups:
            for term in group:
                distributor_aliases[term.upper()] = group

        patterns = distributor_aliases.get(distributor.upper(), [distributor])
        conditions = []
        for pattern in patterns:
            conditions.extend([
                Movie.distributor == pattern,
                Movie.distributor.like(f"%、{pattern}、%"),
                Movie.distributor.like(f"{pattern}、%"),
                Movie.distributor.like(f"%、{pattern}"),
                Movie.distributor.like(f"%{pattern}%")
            ])
        query = query.filter(or_(*conditions))

    if category:
        query = query.filter(Movie.category == category)
    
    if min_revenue:
        query = query.filter(Movie.revenue >= float(min_revenue))
    if max_revenue:
        query = query.filter(Movie.revenue <= float(max_revenue))

    # 年検索の処理
    if years:
        year_conditions = []
        if year_match == 'range' and len(years) >= 2:
            min_year = min([int(y) for y in years])
            max_year = max([int(y) for y in years])
            query = query.filter(Movie.year >= min_year, Movie.year <= max_year)
        else:
            year_conditions = [Movie.year == int(year) for year in years]
            query = query.filter(or_(*year_conditions))

    # ジャンル検索の処理
    if genres:
        genre_conditions = []
        for genre in genres:
            genre_conditions.append(
                or_(
                    Movie.genre.like(f"%{genre}%"),
                    Movie.genre.like(f"{genre},%"),
                    Movie.genre.like(f"%, {genre},%"),
                    Movie.genre.like(f"%, {genre}"),
                    Movie.genre == genre
                )
            )
        
        if genre_match == 'all':
            for condition in genre_conditions:
                query = query.filter(condition)
        else:
            query = query.filter(or_(*genre_conditions))

    movies = query.all()

    # ソート処理
    if movies:
        if order_by == 'release_date':
            movies.sort(key=lambda m: parse_date(m.release_date), reverse=(sort == 'desc'))
        elif order_by == 'revenue':
            movies.sort(key=lambda m: m.revenue if m.revenue is not None else 0, reverse=(sort == 'desc'))
        elif order_by == 'year':
            movies.sort(key=lambda m: m.year if m.year is not None else 0, reverse=(sort == 'desc'))
        else:
            # その他のソート項目はアルファベット順
            movies.sort(key=lambda m: getattr(m, order_by) or '', reverse=(sort == 'desc'))

    # ページネーション
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    pagination_items = movies[start:end]

    total_pages = (len(movies) + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages

    # args_no_page の作成（page, order_by, sortを除外）
    args_no_page = request.args.to_dict()
    args_no_page.pop("page", None)
    args_no_page.pop("order_by", None)
    args_no_page.pop("sort", None)
    
    # ページネーション用の引数（order_byとsortを保持）
    args_with_sort = request.args.to_dict()
    args_with_sort.pop("page", None)

    return render_template('search.html',
        movies=pagination_items,
        pagination={
            'page': page,
            'pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1,
            'next_num': page + 1
        },
        order_by=order_by,
        sort=sort,
        args_no_page=args_no_page,
        args_with_sort=args_with_sort,  # 追加
        total_results=len(movies)
    )

@app.route("/movie/<int:movie_id>")
@site_access_required
def movie_detail(movie_id):
    movie = Movie.query.filter_by(id=movie_id).first_or_404()
    return render_template("movie_detail.html", movie=movie)

# 興収推移データのルート追加
@app.route("/movie/<int:movie_id>/box-office")
@site_access_required
def box_office_detail(movie_id):
    movie = Movie.query.filter_by(id=movie_id).first_or_404()
    
    # 興収推移データを取得
    box_office_data = BoxOfficeData.query.filter_by(movie_id=movie.movie_id).order_by(BoxOfficeData.week).all()
    
    # データを処理
    processed_data = []
    for i, data in enumerate(box_office_data):
        weekend_revenue = parse_revenue_string(data.weekend_revenue)
        weekly_revenue = parse_revenue_string(data.weekly_revenue)
        total_revenue = parse_revenue_string(data.total_revenue)
        
        # 前週比計算
        weekend_change = None
        weekly_change = None
        
        if i > 0:
            prev_weekend = parse_revenue_string(box_office_data[i-1].weekend_revenue)
            prev_weekly = parse_revenue_string(box_office_data[i-1].weekly_revenue)
            
            weekend_change = calculate_week_over_week_change(weekend_revenue, prev_weekend)
            weekly_change = calculate_week_over_week_change(weekly_revenue, prev_weekly)
        
        processed_data.append({
            'week': data.week,
            'weekend_revenue': weekend_revenue,
            'weekly_revenue': weekly_revenue,
            'total_revenue': total_revenue,
            'weekend_change': weekend_change,
            'weekly_change': weekly_change
        })
    
    # ランキング情報を取得
    rankings = get_box_office_rankings(movie)
    
    return render_template("box_office_detail.html", 
                         movie=movie, 
                         box_office_data=processed_data,
                         rankings=rankings)

@app.route("/table")
@site_access_required
def table_view():
    query = Movie.query

    # 基本検索パラメータ
    title = request.args.get('title')
    director = request.args.get('director')
    actor = request.args.get('actor')
    distributor = request.args.get('distributor')
    category = request.args.get('category')
    min_revenue = request.args.get('min_revenue')
    max_revenue = request.args.get('max_revenue')
    
    # 新しい検索パラメータ
    years = request.args.getlist('years')
    genres = request.args.getlist('genres')
    year_match = request.args.get('year_match', 'any')
    genre_match = request.args.get('genre_match', 'any')
    
    order_by = request.args.get('order_by', 'release_date')
    sort = request.args.get('sort', 'desc')

    # 基本フィルタリング（search関数と同じロジック）
    if title:
        query = query.filter(Movie.title.contains(title))
    if director:
        query = query.filter(Movie.director.contains(director))
    if actor:
        query = query.filter(Movie.actor.contains(actor))
    if distributor:
        query = query.filter(
            or_(
                Movie.distributor == distributor,
                Movie.distributor.like(f"%、{distributor}、%"),
                Movie.distributor.like(f"{distributor}、%"),
                Movie.distributor.like(f"%、{distributor}"),
                Movie.distributor.like(f"%{distributor}%")
            )
        )
    if category:
        query = query.filter(Movie.category == category)
    if min_revenue:
        query = query.filter(Movie.revenue >= float(min_revenue))
    if max_revenue:
        query = query.filter(Movie.revenue <= float(max_revenue))

    # 年検索の処理
    if years:
        if year_match == 'range' and len(years) >= 2:
            min_year = min([int(y) for y in years])
            max_year = max([int(y) for y in years])
            query = query.filter(Movie.year >= min_year, Movie.year <= max_year)
        else:
            year_conditions = [Movie.year == int(year) for year in years]
            query = query.filter(or_(*year_conditions))

    # ジャンル検索の処理
    if genres:
        genre_conditions = []
        for genre in genres:
            genre_conditions.append(
                or_(
                    Movie.genre.like(f"%{genre}%"),
                    Movie.genre.like(f"{genre},%"),
                    Movie.genre.like(f"%, {genre},%"),
                    Movie.genre.like(f"%, {genre}"),
                    Movie.genre == genre
                )
            )
        
        if genre_match == 'all':
            for condition in genre_conditions:
                query = query.filter(condition)
        else:
            query = query.filter(or_(*genre_conditions))

    # ソート処理
    if order_by == 'release_date':
        movies = query.all()
        movies.sort(key=lambda m: parse_date(m.release_date), reverse=(sort == 'desc'))
    elif order_by == 'genre':
        movies = query.all()
        movies.sort(key=lambda m: m.genre or '', reverse=(sort == 'desc'))
    elif hasattr(Movie, order_by):
        column = getattr(Movie, order_by)
        if sort == 'asc':
            query = query.order_by(asc(column))
        else:
            query = query.order_by(desc(column))
        movies = query.all()
    else:
        movies = query.all()

    # ページネーション
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 50
    start = (page - 1) * per_page
    end = start + per_page
    pagination_items = movies[start:end]

    total_pages = (len(movies) + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages

    args_no_page = request.args.to_dict()
    args_no_page.pop("page", None)
    args_no_page.pop("order_by", None)  # 追加
    args_no_page.pop("sort", None)   

    return render_template("table_view.html", 
        movies=pagination_items, 
        order_by=order_by, 
        sort=sort,
        pagination={
            'page': page,
            'pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1,
            'next_num': page + 1
        },
        args_no_page=args_no_page,
        total_results=len(movies)
    )

# ===== 記事機能 =====

@app.route("/articles")
@site_access_required
def articles():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    
    query = Article.query
    if category:
        query = query.filter(Article.category == category)
    
    try:
        articles = query.order_by(desc(Article.published_date)).paginate(
            page=page, per_page=10, error_out=False
        )
    except Exception as e:
        print(f"❌ 記事取得エラー: {e}")
        from flask_sqlalchemy import Pagination
        articles = Pagination(page=page, per_page=10, total=0, items=[])
    
    categories = ['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
    
    return render_template('articles.html', articles=articles, categories=categories, current_category=category)

@app.route("/articles/<int:article_id>")
@site_access_required
def article_detail(article_id):
    article = Article.query.get_or_404(article_id)
    article.view_count += 1
    try:
        db.session.commit()
    except:
        db.session.rollback()
    
    related_articles = Article.query.filter(
        Article.category == article.category,
        Article.id != article.id
    ).limit(3).all()
    
    return render_template('article_detail.html', article=article, related_articles=related_articles)

@app.route("/chat")
@site_access_required
def movie_chat():
    return render_template('movie_chat.html')

@app.route("/api/chat", methods=['POST'])
@site_access_required
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        bot = MovieAnalysisBot()
        response = bot.get_response(user_message)
        
        try:
            chat_message = ChatMessage(
                session_id=session_id,
                message=user_message,
                response=response
            )
            db.session.add(chat_message)
            db.session.commit()
        except Exception as e:
            print(f"❌ チャット履歴保存エラー: {e}")
            db.session.rollback()
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ チャットAPIエラー: {e}")
        return jsonify({
            'response': '申し訳ございません。一時的にサービスを利用できません。',
            'timestamp': datetime.now().isoformat()
        }), 500

# ===== SNSトレンド機能 =====

# app.pyのsns_rankingルート修正版

# app.py sns_ranking ルート - 確実に動作する修正版
@app.route("/trending")
@site_access_required
def sns_ranking():
    """SNSランキング表示（前日比計算修正版）"""
    selected_date = request.args.get('date')
    
    try:
        # 利用可能な日付を取得
        available_dates = db.session.query(TrendingData.date)\
                                   .distinct()\
                                   .order_by(TrendingData.date.desc())\
                                   .all()
        available_dates = [d[0] for d in available_dates]
        
        print(f"🔍 利用可能日付: {available_dates[:5]}")  # 最新5日を表示
        
        # 選択日がない場合は最新日を使用
        if not selected_date and available_dates:
            selected_date = available_dates[0]
        
        trending_movies = []
        error = None
        
        if not selected_date:
            error = "利用可能な日付がありません"
        else:
            print(f"📅 選択日: {selected_date}")
            
            # 今日のトレンドデータを取得
            today_trends = TrendingData.query.filter_by(date=selected_date)\
                                            .order_by(TrendingData.post_count.desc())\
                                            .limit(10)\
                                            .all()
            
            print(f"📊 今日のデータ: {len(today_trends)}件")
            
            if not today_trends:
                error = f"選択された日付（{selected_date}）のデータがありません"
            else:
                # 前日の日付を特定（利用可能日付から前の日を探す）
                prev_date = None
                try:
                    current_index = available_dates.index(selected_date)
                    if current_index + 1 < len(available_dates):
                        prev_date = available_dates[current_index + 1]
                        print(f"📅 前日（利用可能日付から）: {prev_date}")
                    else:
                        print("⚠️ 前日データなし（これが最古の日付）")
                except ValueError:
                    print(f"⚠️ 選択日 {selected_date} が利用可能日付リストに見つかりません")
                
                # 前日データを取得
                prev_data_dict = {}
                if prev_date:
                    prev_trends = TrendingData.query.filter_by(date=prev_date)\
                                                   .order_by(TrendingData.post_count.desc())\
                                                   .all()
                    
                    print(f"📊 前日のデータ: {len(prev_trends)}件")
                    
                    # 前日データを辞書化
                    for i, trend in enumerate(prev_trends):
                        prev_data_dict[trend.movie_title] = {
                            'post_count': trend.post_count,
                            'rank': i + 1
                        }
                    
                    print(f"📈 前日データ辞書作成: {len(prev_data_dict)}件")
                    
                    # 前日データの確認（デバッグ）
                    for title, data in list(prev_data_dict.items())[:3]:
                        print(f"   前日データ例: {title} = {data['post_count']}投稿 (順位{data['rank']})")
                
                # 各映画の前日比を計算
                for i, trend in enumerate(today_trends):
                    current_rank = i + 1
                    current_count = trend.post_count
                    
                    # 映画データを検索
                    movie_data = Movie.query.filter_by(title=trend.movie_title).first()
                    if not movie_data:
                        # 部分一致で再検索
                        movie_data = Movie.query.filter(Movie.title.contains(trend.movie_title)).first()
                    
                    # 前日のデータを取得
                    prev_info = prev_data_dict.get(trend.movie_title, {'post_count': 0, 'rank': None})
                    prev_count = prev_info['post_count']
                    prev_rank = prev_info['rank']
                    
                    print(f"🎬 {trend.movie_title}:")
                    print(f"   今日: {current_count}投稿 (順位{current_rank})")
                    print(f"   前日: {prev_count}投稿 (順位{prev_rank})")
                    
                    # 投稿数の前日比計算
                    if prev_count > 0:
                        try:
                            change_percent = ((current_count - prev_count) / prev_count) * 100
                            if abs(change_percent) < 0.1:
                                post_change_display = "前日比 ±0%"
                                post_change_class = "change-neutral"
                            elif change_percent > 0:
                                post_change_display = f"前日比 +{change_percent:.1f}%"
                                post_change_class = "change-up"
                            else:
                                post_change_display = f"前日比 {change_percent:.1f}%"
                                post_change_class = "change-down"
                            print(f"   計算結果: {post_change_display}")
                        except Exception as calc_error:
                            print(f"   ⚠️ 計算エラー: {calc_error}")
                            post_change_display = "前日比 エラー"
                            post_change_class = "change-neutral"
                    else:
                        post_change_display = "前日比 NEW"
                        post_change_class = "change-neutral"
                        print(f"   計算結果: {post_change_display} (前日データなし)")
                    
                    # 順位変動の計算
                    if prev_rank is not None and prev_rank > 0:
                        rank_diff = prev_rank - current_rank
                        if rank_diff > 0:  # 順位上昇
                            if rank_diff >= 5:
                                rank_change_display = "🚀"
                                rank_change_class = "rank-up"
                            elif rank_diff >= 3:
                                rank_change_display = "⬆️"
                                rank_change_class = "rank-up"
                            else:
                                rank_change_display = "🔺"
                                rank_change_class = "rank-up"
                        elif rank_diff < 0:  # 順位下降
                            if rank_diff <= -5:
                                rank_change_display = "📉"
                                rank_change_class = "rank-down"
                            elif rank_diff <= -3:
                                rank_change_display = "⬇️"
                                rank_change_class = "rank-down"
                            else:
                                rank_change_display = "🔻"
                                rank_change_class = "rank-down"
                        else:  # 順位変わらず
                            rank_change_display = "━"
                            rank_change_class = "rank-keep"
                        print(f"   順位変動: {rank_diff} → {rank_change_display}")
                    else:
                        rank_change_display = "🆕"
                        rank_change_class = "rank-up"
                        print(f"   順位変動: NEW → {rank_change_display}")
                    
                    # フォールバック用changeフィールド
                    if "NEW" in post_change_display:
                        change_fallback = "NEW"
                    elif "+" in post_change_display:
                        change_fallback = post_change_display.replace("前日比 ", "")
                    elif "-" in post_change_display and post_change_display != "前日比 -":
                        change_fallback = post_change_display.replace("前日比 ", "")
                    else:
                        change_fallback = "-%"
                    
                    trending_movies.append({
                        'rank': current_rank,
                        'title': trend.movie_title,
                        'post_count': current_count,
                        'date': trend.date,
                        'movie_data': movie_data,
                        'trend_score': (current_count / today_trends[0].post_count * 100) if today_trends[0].post_count > 0 else 0,
                        'word_cloud': [],
                        # 前日比データ（確実に設定）
                        'post_change_display': post_change_display,
                        'post_change_class': post_change_class,
                        'rank_change_display': rank_change_display,
                        'rank_change_class': rank_change_class,
                        'prev_post_count': prev_count,
                        'prev_rank': prev_rank,
                        # フォールバック用
                        'change': change_fallback
                    })
        
        print(f"✅ 最終結果: {len(trending_movies)}件のトレンドデータを生成")
        if trending_movies:
            print(f"   1位: {trending_movies[0]['title']} - {trending_movies[0]['post_change_display']}")
            if len(trending_movies) > 1:
                print(f"   2位: {trending_movies[1]['title']} - {trending_movies[1]['post_change_display']}")
        
        return render_template('sns_ranking.html',
                             trending_movies=trending_movies,
                             available_dates=available_dates,
                             selected_date=selected_date,
                             error=error)
                             
    except Exception as e:
        import traceback
        error_info = traceback.format_exc()
        print(f"❌ SNSランキング全体エラー: {e}")
        print(f"詳細: {error_info}")
        
        return render_template('sns_ranking.html',
                             trending_movies=[],
                             available_dates=[],
                             selected_date=None,
                             error=f"システムエラー: {str(e)}")

# デバッグ用の詳細確認ルートを追加

@app.route("/debug/trending-data")
@site_access_required
def debug_trending_data():
    """トレンドデータの詳細確認（デバッグ用）"""
    try:
        from datetime import datetime, timedelta
        
        # 1. 利用可能な日付を全て取得
        all_dates = db.session.query(TrendingData.date)\
                             .distinct()\
                             .order_by(TrendingData.date.desc())\
                             .all()
        all_dates_list = [d[0] for d in all_dates]
        
        # 2. 最新の2日分のデータを詳細表示
        debug_info = {
            'available_dates': all_dates_list,
            'total_dates': len(all_dates_list),
            'latest_data': {},
            'prev_data': {},
            'calculation_test': {}
        }
        
        if len(all_dates_list) >= 2:
            latest_date = all_dates_list[0]
            prev_date = all_dates_list[1]
            
            # 最新日のデータ
            latest_trends = TrendingData.query.filter_by(date=latest_date)\
                                             .order_by(TrendingData.post_count.desc())\
                                             .limit(5).all()
            
            debug_info['latest_data'] = {
                'date': latest_date,
                'count': len(latest_trends),
                'movies': [
                    {
                        'title': t.movie_title,
                        'post_count': t.post_count,
                        'rank': i+1
                    } for i, t in enumerate(latest_trends)
                ]
            }
            
            # 前日のデータ
            prev_trends = TrendingData.query.filter_by(date=prev_date)\
                                           .order_by(TrendingData.post_count.desc())\
                                           .limit(5).all()
            
            debug_info['prev_data'] = {
                'date': prev_date,
                'count': len(prev_trends),
                'movies': [
                    {
                        'title': t.movie_title,
                        'post_count': t.post_count,
                        'rank': i+1
                    } for i, t in enumerate(prev_trends)
                ]
            }
            
            # 3. 前日比計算のテスト
            prev_dict = {t.movie_title: {'post_count': t.post_count, 'rank': i+1} 
                        for i, t in enumerate(prev_trends)}
            
            calculations = []
            for i, latest_movie in enumerate(latest_trends):
                current_rank = i + 1
                current_count = latest_movie.post_count
                
                if latest_movie.movie_title in prev_dict:
                    prev_info = prev_dict[latest_movie.movie_title]
                    prev_count = prev_info['post_count']
                    prev_rank = prev_info['rank']
                    
                    # 投稿数変化率
                    if prev_count > 0:
                        change_percent = ((current_count - prev_count) / prev_count) * 100
                        change_display = f"+{change_percent:.1f}%" if change_percent > 0 else f"{change_percent:.1f}%"
                    else:
                        change_display = "NEW"
                    
                    # 順位変動
                    rank_diff = prev_rank - current_rank
                    if rank_diff > 0:
                        rank_change = "🔺 UP"
                    elif rank_diff < 0:
                        rank_change = "🔻 DOWN"
                    else:
                        rank_change = "━ KEEP"
                    
                    calculations.append({
                        'movie': latest_movie.movie_title,
                        'current_rank': current_rank,
                        'current_count': current_count,
                        'prev_rank': prev_rank,
                        'prev_count': prev_count,
                        'change_percent': change_display,
                        'rank_change': rank_change
                    })
                else:
                    calculations.append({
                        'movie': latest_movie.movie_title,
                        'current_rank': current_rank,
                        'current_count': current_count,
                        'prev_rank': None,
                        'prev_count': 0,
                        'change_percent': "NEW",
                        'rank_change': "🆕 NEW"
                    })
            
            debug_info['calculation_test'] = calculations
        
        # 4. データベースの基本情報
        total_records = TrendingData.query.count()
        unique_movies = db.session.query(TrendingData.movie_title).distinct().count()
        
        debug_info['database_stats'] = {
            'total_records': total_records,
            'unique_movies': unique_movies,
            'unique_dates': len(all_dates_list)
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# HTMLで確認できるデバッグページも追加
@app.route("/debug/trending-page")
@site_access_required
def debug_trending_page():
    """デバッグ情報をHTMLで表示"""
    try:
        # デバッグ情報を取得
        from datetime import datetime, timedelta
        
        # 最新の2日分のデータを取得
        all_dates = db.session.query(TrendingData.date)\
                             .distinct()\
                             .order_by(TrendingData.date.desc())\
                             .limit(2).all()
        
        if len(all_dates) < 2:
            return render_template_string("""
            <h1>デバッグ情報</h1>
            <p style="color: red;">利用可能な日付が2日未満です。データが不足しています。</p>
            <p>利用可能日付: {{ dates }}</p>
            """, dates=[d[0] for d in all_dates])
        
        latest_date = all_dates[0][0]
        prev_date = all_dates[1][0]
        
        # データを取得
        latest_data = TrendingData.query.filter_by(date=latest_date)\
                                       .order_by(TrendingData.post_count.desc())\
                                       .limit(10).all()
        
        prev_data = TrendingData.query.filter_by(date=prev_date)\
                                     .order_by(TrendingData.post_count.desc())\
                                     .limit(10).all()
        
        # 前日データを辞書化
        prev_dict = {}
        for i, trend in enumerate(prev_data):
            prev_dict[trend.movie_title] = {
                'post_count': trend.post_count,
                'rank': i + 1
            }
        
        # 計算結果
        calculations = []
        for i, current in enumerate(latest_data):
            current_rank = i + 1
            prev_info = prev_dict.get(current.movie_title, {'post_count': 0, 'rank': None})
            
            # 前日比計算
            if prev_info['post_count'] > 0:
                change_percent = ((current.post_count - prev_info['post_count']) / prev_info['post_count']) * 100
                change_str = f"+{change_percent:.1f}%" if change_percent > 0 else f"{change_percent:.1f}%"
            else:
                change_str = "NEW"
            
            # 順位変動
            if prev_info['rank']:
                rank_diff = prev_info['rank'] - current_rank
                if rank_diff > 0:
                    rank_change = f"🔺 +{rank_diff}"
                elif rank_diff < 0:
                    rank_change = f"🔻 {rank_diff}"
                else:
                    rank_change = "━ 0"
            else:
                rank_change = "🆕 NEW"
            
            calculations.append({
                'rank': current_rank,
                'movie': current.movie_title,
                'current_count': current.post_count,
                'prev_count': prev_info['post_count'],
                'prev_rank': prev_info['rank'],
                'change_percent': change_str,
                'rank_change': rank_change
            })
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>トレンドデータ デバッグ</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .number { font-family: monospace; text-align: right; }
                .up { color: green; }
                .down { color: red; }
                .new { color: orange; }
                .keep { color: gray; }
            </style>
        </head>
        <body>
            <h1>🔍 トレンドデータ デバッグ情報</h1>
            
            <h2>📊 基本情報</h2>
            <p><strong>最新日:</strong> {{ latest_date }}</p>
            <p><strong>前日:</strong> {{ prev_date }}</p>
            <p><strong>最新日データ数:</strong> {{ latest_count }}件</p>
            <p><strong>前日データ数:</strong> {{ prev_count }}件</p>
            
            <h2>📈 前日比計算結果</h2>
            <table>
                <tr>
                    <th>順位</th>
                    <th>映画タイトル</th>
                    <th>今日の投稿数</th>
                    <th>前日の投稿数</th>
                    <th>前日順位</th>
                    <th>投稿数変化</th>
                    <th>順位変動</th>
                </tr>
                {% for calc in calculations %}
                <tr>
                    <td class="number">{{ calc.rank }}</td>
                    <td>{{ calc.movie }}</td>
                    <td class="number">{{ "{:,}".format(calc.current_count) }}</td>
                    <td class="number">{{ "{:,}".format(calc.prev_count) if calc.prev_count > 0 else "-" }}</td>
                    <td class="number">{{ calc.prev_rank if calc.prev_rank else "-" }}</td>
                    <td class="{% if calc.change_percent.startswith('+') %}up{% elif calc.change_percent.startswith('-') %}down{% else %}new{% endif %}">
                        {{ calc.change_percent }}
                    </td>
                    <td class="{% if '🔺' in calc.rank_change %}up{% elif '🔻' in calc.rank_change %}down{% elif '🆕' in calc.rank_change %}new{% else %}keep{% endif %}">
                        {{ calc.rank_change }}
                    </td>
                </tr>
                {% endfor %}
            </table>
            
            <h2>🔗 リンク</h2>
            <p><a href="/trending">通常のランキングページに戻る</a></p>
            <p><a href="/debug/trending-data">JSON形式のデバッグデータ</a></p>
        </body>
        </html>
        """
        
        from flask import render_template_string
        return render_template_string(html_template,
                                    latest_date=latest_date,
                                    prev_date=prev_date,
                                    latest_count=len(latest_data),
                                    prev_count=len(prev_data),
                                    calculations=calculations)
        
    except Exception as e:
        import traceback
        return f"<h1>エラー</h1><pre>{traceback.format_exc()}</pre>"


# デバッグ用のAPIエンドポイントを追加
@app.route("/api/debug-trending")
@site_access_required 
def debug_trending():
    """トレンドデータのデバッグ情報を返す"""
    selected_date = request.args.get('date')
    
    if not selected_date:
        return jsonify({'error': '日付が指定されていません'})
    
    try:
        from datetime import datetime, timedelta
        
        # 今日のデータ
        today_trends = TrendingData.query.filter_by(date=selected_date)\
                                        .order_by(TrendingData.post_count.desc())\
                                        .limit(5).all()
        
        # 前日のデータ
        current_date_obj = datetime.strptime(selected_date, '%Y/%m/%d')
        prev_date_obj = current_date_obj - timedelta(days=1)
        prev_date = prev_date_obj.strftime('%Y/%m/%d')
        
        prev_trends = TrendingData.query.filter_by(date=prev_date)\
                                       .order_by(TrendingData.post_count.desc())\
                                       .limit(5).all()
        
        debug_info = {
            'selected_date': selected_date,
            'prev_date': prev_date,
            'today_data': [
                {
                    'title': t.movie_title,
                    'post_count': t.post_count,
                    'rank': i+1
                } for i, t in enumerate(today_trends)
            ],
            'prev_data': [
                {
                    'title': t.movie_title,
                    'post_count': t.post_count,
                    'rank': i+1
                } for i, t in enumerate(prev_trends)
            ]
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/api/trending-update")
@site_access_required
def trending_update():
    global trending_manager
    
    selected_date = request.args.get('date')
    
    if trending_manager is None:
        return jsonify({'error': 'トレンドマネージャーが初期化されていません'})
    
    trending_movies = trending_manager.get_trending_by_date(selected_date, limit=10)
    return jsonify(trending_movies)

@app.route("/api/word-cloud/<movie_title>")
@site_access_required
def word_cloud_api(movie_title):
    global trending_manager
    
    if trending_manager is None:
        return jsonify([])
    
    word_cloud_data = trending_manager.generate_fallback_wordcloud(movie_title)
    return jsonify(word_cloud_data)

# ===== 管理者機能 =====

@app.route("/admin")
@site_access_required
@admin_required
def admin_dashboard():
    try:
        total_articles = Article.query.count()
        featured_articles = Article.query.filter_by(is_featured=True).count()
        recent_articles = Article.query.filter(
            Article.published_date >= datetime.now() - timedelta(days=7)
        ).count()
        
        category_stats = db.session.query(
            Article.category,
            db.func.count(Article.id).label('count')
        ).group_by(Article.category).all()
        
        recent_articles_list = Article.query.order_by(
            desc(Article.published_date)
        ).limit(5).all()
        
        return render_template('admin_dashboard.html',
            total_articles=total_articles,
            featured_articles=featured_articles,
            recent_articles=recent_articles,
            category_stats=category_stats,
            recent_articles_list=recent_articles_list
        )
    except Exception as e:
        print(f"❌ 管理画面エラー: {e}")
        return render_template('admin_dashboard.html',
            total_articles=0,
            featured_articles=0,
            recent_articles=0,
            category_stats=[],
            recent_articles_list=[]
        )

@app.route("/admin/articles")
@site_access_required
@admin_required
def admin_articles():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    search = request.args.get('search', '').strip()
    
    query = Article.query
    
    if category:
        query = query.filter(Article.category == category)
    
    if search:
        query = query.filter(
            or_(
                Article.title.contains(search),
                Article.content.contains(search),
                Article.author.contains(search)
            )
        )
    
    try:
        articles = query.order_by(desc(Article.published_date)).paginate(
            page=page, per_page=10, error_out=False
        )
    except Exception as e:
        print(f"❌ 記事一覧取得エラー: {e}")
        from flask_sqlalchemy import Pagination
        articles = Pagination(page=page, per_page=10, total=0, items=[])
    
    categories = ['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
    
    return render_template('admin_articles.html', 
        articles=articles, 
        categories=categories,
        current_category=category,
        search_term=search
    )

@app.route("/admin/articles/new", methods=['GET', 'POST'])
@site_access_required
@admin_required
def admin_create_article():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            author = request.form.get('author', '').strip()
            category = request.form.get('category', '').strip()
            tags = request.form.get('tags', '').strip()
            is_featured = request.form.get('is_featured') == 'on'
            
            if not title or not content:
                return render_template('admin_article_form.html', 
                    error="タイトルと内容は必須です",
                    form_data=request.form,
                    categories=['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
                )
            
            if not excerpt:
                excerpt = content[:200] + '...' if len(content) > 200 else content
            
            article = Article(
                title=title,
                content=content,
                excerpt=excerpt,
                author=author or '管理者',
                category=category,
                tags=tags,
                is_featured=is_featured,
                published_date=datetime.now()
            )
            
            db.session.add(article)
            db.session.commit()
            
            print(f"✅ 新規記事作成: {title}")
            return redirect(url_for('admin_articles'))
            
        except Exception as e:
            print(f"❌ 記事作成エラー: {e}")
            db.session.rollback()
            return render_template('admin_article_form.html', 
                error=f"記事の作成に失敗しました: {str(e)}",
                form_data=request.form,
                categories=['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
            )
    
    categories = ['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
    return render_template('admin_article_form.html', 
        categories=categories,
        article=None
    )

@app.route("/admin/articles/<int:article_id>/edit", methods=['GET', 'POST'])
@site_access_required
@admin_required
def admin_edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    
    if request.method == 'POST':
        try:
            article.title = request.form.get('title', '').strip()
            article.content = request.form.get('content', '').strip()
            article.excerpt = request.form.get('excerpt', '').strip()
            article.author = request.form.get('author', '').strip()
            article.category = request.form.get('category', '').strip()
            article.tags = request.form.get('tags', '').strip()
            article.is_featured = request.form.get('is_featured') == 'on'
            
            if not article.title or not article.content:
                return render_template('admin_article_form.html', 
                    error="タイトルと内容は必須です",
                    article=article,
                    categories=['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
                )
            
            if not article.excerpt:
                article.excerpt = article.content[:200] + '...' if len(article.content) > 200 else article.content
            
            db.session.commit()
            
            print(f"✅ 記事更新: {article.title}")
            return redirect(url_for('admin_articles'))
            
        except Exception as e:
            print(f"❌ 記事更新エラー: {e}")
            db.session.rollback()
            return render_template('admin_article_form.html', 
                error=f"記事の更新に失敗しました: {str(e)}",
                article=article,
                categories=['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
            )
    
    categories = ['映画分析', '興行収入', 'トレンド', 'インタビュー', 'レビュー', '業界動向']
    return render_template('admin_article_form.html', 
        categories=categories,
        article=article
    )

@app.route("/admin/articles/<int:article_id>/delete", methods=['POST'])
@site_access_required
@admin_required
def admin_delete_article(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        title = article.title
        
        db.session.delete(article)
        db.session.commit()
        
        print(f"✅ 記事削除: {title}")
        return jsonify({'success': True, 'message': '記事を削除しました'})
        
    except Exception as e:
        print(f"❌ 記事削除エラー: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'削除に失敗しました: {str(e)}'})

@app.route("/admin/articles/<int:article_id>/toggle-featured", methods=['POST'])
@site_access_required
@admin_required
def admin_toggle_featured(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        article.is_featured = not article.is_featured
        
        db.session.commit()
        
        status = "注目記事に設定" if article.is_featured else "注目記事を解除"
        print(f"✅ {article.title}: {status}")
        
        return jsonify({
            'success': True, 
            'message': f'{status}しました',
            'is_featured': article.is_featured
        })
        
    except Exception as e:
        print(f"❌ 注目記事切り替えエラー: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'切り替えに失敗しました: {str(e)}'})

@app.route("/api/box-office-check/<int:movie_id>")
@site_access_required
def check_box_office_data(movie_id):
    """興収推移データの存在確認API"""
    try:
        movie = Movie.query.filter_by(id=movie_id).first()
        if not movie or not movie.movie_id:
            return jsonify({'has_data': False})
        
        # 興収推移データの存在確認
        box_office_data = BoxOfficeData.query.filter_by(movie_id=movie.movie_id).first()
        
        return jsonify({
            'has_data': box_office_data is not None,
            'movie_id': movie.movie_id,
            'data_count': BoxOfficeData.query.filter_by(movie_id=movie.movie_id).count() if box_office_data else 0
        })
        
    except Exception as e:
        print(f"❌ 興収推移データ確認エラー: {e}")
        return jsonify({'has_data': False, 'error': str(e)})

# app.pyの import文の部分に追加（ファイルの上部）
import traceback
import logging

# ログ設定（import文の後、アプリ初期化の前に追加）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 既存のエラーハンドラーを削除して、以下で置き換え
# 堅牢なエラーハンドラー（既存の @app.errorhandler部分と置き換え）
@app.errorhandler(404)
def not_found_error(error):
    """404エラーハンドラー - テンプレート不要バージョン"""
    try:
        return render_template('404.html'), 404
    except Exception as e:
        # テンプレートが見つからない場合のフォールバック
        logger.error(f"404テンプレートエラー: {e}")
        return create_fallback_404_response(), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラー - 堅牢版"""
    try:
        # データベースのロールバック（安全のため）
        try:
            db.session.rollback()
        except:
            pass
        
        # ログに詳細を記録
        logger.error(f"内部エラー: {error}")
        logger.error(f"トレースバック: {traceback.format_exc()}")
        
        # テンプレートを試行
        return render_template('500.html'), 500
        
    except Exception as template_error:
        # テンプレートが見つからない場合のフォールバック
        logger.error(f"500テンプレートエラー: {template_error}")
        logger.error(f"元のエラー: {error}")
        
        return create_fallback_500_response(str(error)), 500

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """予期しないエラーのキャッチオール"""
    try:
        # データベースのロールバック
        try:
            db.session.rollback()
        except:
            pass
        
        # 詳細ログ
        logger.error(f"予期しないエラー: {error}")
        logger.error(f"エラータイプ: {type(error)}")
        logger.error(f"トレースバック: {traceback.format_exc()}")
        
        # 500エラーとして処理
        return internal_error(error)
        
    except Exception as handler_error:
        # エラーハンドラー自体がエラーの場合
        logger.critical(f"エラーハンドラーでエラー: {handler_error}")
        return create_emergency_response(), 500

def create_fallback_404_response():
    """テンプレート不要の404レスポンス"""
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>404 - ページが見つかりません</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #333;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 400px;
            }
            .error-code { font-size: 72px; font-weight: bold; color: #667eea; margin-bottom: 16px; }
            .error-title { font-size: 24px; margin-bottom: 12px; }
            .error-message { color: #666; margin-bottom: 24px; line-height: 1.5; }
            .back-button {
                display: inline-block;
                padding: 12px 24px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            }
            .back-button:hover { background: #5a6fd8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-code">404</div>
            <h1 class="error-title">ページが見つかりません</h1>
            <p class="error-message">お探しのページは存在しないか、移動されています。</p>
            <a href="/" class="back-button">🏠 トップページに戻る</a>
        </div>
    </body>
    </html>
    """
    return html

def create_fallback_500_response(error_details="不明なエラー"):
    """テンプレート不要の500レスポンス"""
    # 本番環境では詳細なエラー情報を隠す
    is_production = os.environ.get('FLASK_ENV') != 'development'
    error_info = "詳細は管理者にお問い合わせください" if is_production else f"エラー詳細: {error_details}"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>500 - サーバーエラー</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #ea4335 0%, #d93025 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #333;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 500px;
            }}
            .error-code {{ font-size: 72px; font-weight: bold; color: #ea4335; margin-bottom: 16px; }}
            .error-title {{ font-size: 24px; margin-bottom: 12px; }}
            .error-message {{ color: #666; margin-bottom: 16px; line-height: 1.5; }}
            .error-details {{ 
                background: #f8f9fa; 
                border-radius: 6px; 
                padding: 12px; 
                margin: 16px 0; 
                font-size: 14px; 
                color: #666; 
                text-align: left;
                word-break: break-all;
            }}
            .button-group {{ margin-top: 24px; }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                margin: 0 6px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                transition: transform 0.2s;
            }}
            .button:hover {{ transform: translateY(-1px); }}
            .primary {{ background: #ea4335; color: white; }}
            .secondary {{ background: #666; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-code">500</div>
            <h1 class="error-title">サーバーエラー</h1>
            <p class="error-message">
                申し訳ございません。サーバー内部でエラーが発生しました。
            </p>
            <div class="error-details">
                <strong>🔧 情報:</strong><br>
                {error_info}
            </div>
            <div class="button-group">
                <a href="/" class="button primary">🏠 トップページ</a>
                <a href="javascript:location.reload()" class="button secondary">🔄 再読み込み</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def create_emergency_response():
    """緊急時のプレーンテキストレスポンス"""
    return """
    映画データベース - サーバーエラー
    
    申し訳ございません。システムで重大なエラーが発生しました。
    
    対処方法:
    1. ページを再読み込みしてください
    2. 数分待ってから再度アクセスしてください  
    3. 問題が続く場合は管理者にお問い合わせください
    
    トップページに戻る: /
    """, 500, {'Content-Type': 'text/plain; charset=utf-8'}

# アプリケーション起動
if __name__ == "__main__":
    # 環境変数読み込み
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 .envファイルを読み込みました")
    except ImportError:
        print("⚠️ python-dotenvがインストールされていません")
    
    print("🚀 映画データベース アプリケーション起動中（Render対応版）...")
    
    # 🔧 データベース自動初期化（ここが重要！）
    with app.app_context():
        try:
            print("🔧 データベース初期化開始...")
            
            # テーブル作成
            db.create_all()
            print("✅ データベーステーブル作成完了")
            
            # 接続確認
            try:
                if database_url.startswith("postgresql://"):
                    result = db.session.execute(db.text('SELECT version()'))
                    version = result.fetchone()[0]
                    print(f"✅ PostgreSQL接続確認: {version[:50]}...")
                else:
                    print("✅ SQLite接続確認完了")
            except Exception as e:
                print(f"⚠️ 接続確認スキップ: {e}")
            
            # テーブル件数確認
            try:
                movie_count = Movie.query.count()
                article_count = Article.query.count()
                trending_count = TrendingData.query.count()
                box_office_count = BoxOfficeData.query.count()
                
                print(f"📊 現在のデータ:")
                print(f"   🎬 映画: {movie_count} 件")
                print(f"   📰 記事: {article_count} 件") 
                print(f"   📈 トレンド: {trending_count} 件")
                print(f"   📊 興収推移: {box_office_count} 件")
                
                # サンプルデータが全くない場合のみ追加
                if movie_count == 0 and article_count == 0:
                    print("🔧 初期サンプルデータを追加中...")
                    
                    # 最小限のサンプル映画データ
                    sample_movies = [
                        Movie(
                            movie_id="1",
                            title="劇場版「鬼滅の刃」無限列車編",
                            revenue=404.3,
                            year=2020,
                            release_date="2020/10/16",
                            category="邦画",
                            distributor="東宝",
                            description="炭治郎と仲間たちが無限列車で鬼と戦う物語",
                            director="外崎春雄",
                            genre="アニメ、アクション"
                        ),
                        Movie(
                            movie_id="2", 
                            title="千と千尋の神隠し",
                            revenue=316.8,
                            year=2001,
                            release_date="2001/7/20",
                            category="邦画",
                            distributor="東宝",
                            description="不思議な世界に迷い込んだ少女の冒険",
                            director="宮崎駿",
                            genre="アニメ、ファミリー"
                        ),
                        Movie(
                            movie_id="3",
                            title="君の名は。", 
                            revenue=251.7,
                            year=2016,
                            release_date="2016/8/26",
                            category="邦画",
                            distributor="東宝",
                            description="時空を超えて入れ替わる男女の恋愛物語",
                            director="新海誠",
                            genre="アニメ、恋愛"
                        )
                    ]
                    
                    for movie in sample_movies:
                        db.session.add(movie)
                    
                    # 最小限のサンプル記事データ
                    sample_article = Article(
                        title="映画データベースへようこそ",
                        content="このサイトでは日本の映画興行収入データを検索・閲覧できます。検索機能やトレンド分析をお楽しみください。",
                        excerpt="映画データベースの使い方とサイトの概要",
                        author="管理者",
                        category="お知らせ",
                        tags="サイト紹介,使い方",
                        is_featured=True
                    )
                    db.session.add(sample_article)
                    
                    # 最小限のトレンドデータ
                    today = datetime.now().strftime('%Y/%m/%d')
                    sample_trends = [
                        TrendingData(date=today, movie_title="鬼滅の刃", post_count=5000),
                        TrendingData(date=today, movie_title="千と千尋の神隠し", post_count=3000),
                        TrendingData(date=today, movie_title="君の名は", post_count=2500)
                    ]
                    
                    for trend in sample_trends:
                        db.session.add(trend)
                    
                    # サンプル興収推移データ
                    sample_box_office = [
                        BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                                    week="第1週", weekend_revenue="46.2", weekly_revenue="46.2", total_revenue="46.2"),
                        BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                                    week="第2週", weekend_revenue="27.1", weekly_revenue="27.1", total_revenue="107.5"),
                        BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                                    week="第3週", weekend_revenue="21.9", weekly_revenue="21.9", total_revenue="157.9"),
                    ]
                    
                    for box_office in sample_box_office:
                        db.session.add(box_office)
                    
                    db.session.commit()
                    print(f"✅ サンプルデータ追加完了: 映画{len(sample_movies)}件、記事1件、トレンド{len(sample_trends)}件、興収推移{len(sample_box_office)}件")
                else:
                    print("ℹ️ データが既に存在するため、サンプルデータ追加をスキップ")
                    
            except Exception as e:
                print(f"⚠️ データ確認エラー: {e}")
                print("ℹ️ テーブルは作成されましたが、データ確認に失敗しました")
            
            print("✅ データベース初期化完了")
            
        except Exception as e:
            print(f"❌ データベース初期化エラー: {e}")
            print("⚠️ アプリケーションは起動しますが、データベースエラーが発生する可能性があります")
    
    # トレンドマネージャー初期化
    try:
        init_trending_manager()
    except Exception as e:
        print(f"⚠️ トレンドマネージャー初期化エラー: {e}")
    
    # ポート設定（Render対応）
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    
    print(f"🎉 起動完了！ポート: {port}")
    print(f"🔧 デバッグモード: {debug_mode}")
    print("🌐 アプリケーションにアクセス可能です")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)