"""
Renderデプロイ用データベース初期化スクリプト
PostgreSQLデータベースのテーブル作成とサンプルデータの投入
"""

import os
from datetime import datetime
from app import app, db, Movie, Article, TrendingData

def init_database():
    """データベースの初期化"""
    print("🔧 PostgreSQLデータベースを初期化中...")
    
    with app.app_context():
        try:
            # データベース接続確認
            result = db.session.execute(db.text('SELECT version()'))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL接続成功: {version}")
            
            # 全テーブルを作成
            db.create_all()
            print("✅ 全テーブルを作成しました")
            
            # 各テーブルの存在確認
            tables = ['movies', 'articles', 'trending_data', 'chat_messages']
            for table in tables:
                try:
                    result = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"📊 {table}テーブル: {count} 件")
                except Exception as e:
                    print(f"❌ {table}テーブルエラー: {e}")
            
            # サンプル映画データを追加（テーブルが空の場合）
            if Movie.query.count() == 0:
                print("🎬 サンプル映画データを追加中...")
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
                        title="タイタニック",
                        revenue=262.0,
                        year=1997,
                        release_date="1997/12/20",
                        category="洋画",
                        distributor="20世紀フォックス",
                        description="豪華客船タイタニック号での悲劇的な恋愛物語",
                        director="ジェームズ・キャメロン",
                        genre="ドラマ、恋愛"
                    ),
                    Movie(
                        movie_id="4",
                        title="アナと雪の女王",
                        revenue=255.0,
                        year=2014,
                        release_date="2014/3/14",
                        category="洋画",
                        distributor="ウォルト・ディズニー・ジャパン",
                        description="魔法の力を持つ姉妹の絆を描いたミュージカル",
                        director="クリス・バック、ジェニファー・リー",
                        genre="アニメ、ミュージカル、ファミリー"
                    ),
                    Movie(
                        movie_id="5",
                        title="君の名は。",
                        revenue=251.7,
                        year=2016,
                        release_date="2016/8/26",
                        category="邦画",
                        distributor="東宝",
                        description="時空を超えて入れ替わる男女の恋愛物語",
                        director="新海誠",
                        genre="アニメ、恋愛、ドラマ"
                    )
                ]
                
                for movie in sample_movies:
                    db.session.add(movie)
                
                db.session.commit()
                print(f"✅ {len(sample_movies)} 件のサンプル映画データを追加しました")
            
            # サンプル記事データを追加（テーブルが空の場合）
            if Article.query.count() == 0:
                print("📰 サンプル記事データを追加中...")
                sample_articles = [
                    Article(
                        title="2024年興行収入ランキング分析",
                        content="2024年の映画興行収入について詳しく分析します。アニメ映画が上位を占める傾向が続いており、特に「劇場版 鬼滅の刃」シリーズの人気が際立っています。",
                        excerpt="2024年の映画興行収入トップ10とその傾向を分析",
                        author="映画アナリスト",
                        category="映画分析",
                        tags="興行収入,2024年,ランキング",
                        is_featured=True
                    ),
                    Article(
                        title="SNS投稿数から見る映画の話題性",
                        content="TwitterやInstagramの投稿数と興行収入の関係について調査しました。SNSでの話題性が興行収入に与える影響は予想以上に大きいことが判明しています。",
                        excerpt="SNSデータから読み解く映画マーケティングの新潮流",
                        author="データサイエンティスト",
                        category="トレンド",
                        tags="SNS,投稿数,マーケティング"
                    )
                ]
                
                for article in sample_articles:
                    db.session.add(article)
                
                db.session.commit()
                print(f"✅ {len(sample_articles)} 件のサンプル記事データを追加しました")
            
            # サンプルトレンドデータを追加（テーブルが空の場合）
            if TrendingData.query.count() == 0:
                print("📈 サンプルトレンドデータを追加中...")
                today = datetime.now().strftime('%Y/%m/%d')
                sample_trends = [
                    TrendingData(date=today, movie_title="鬼滅の刃", post_count=5000),
                    TrendingData(date=today, movie_title="スパイダーマン", post_count=3200),
                    TrendingData(date=today, movie_title="君の名は", post_count=2800),
                    TrendingData(date=today, movie_title="ワンピース", post_count=2500),
                    TrendingData(date=today, movie_title="アナと雪の女王", post_count=1800)
                ]
                
                for trend in sample_trends:
                    db.session.add(trend)
                
                db.session.commit()
                print(f"✅ {len(sample_trends)} 件のサンプルトレンドデータを追加しました")
            
            print("\n🎉 データベース初期化完了！")
            print("=" * 50)
            
            # 最終統計表示
            movie_count = Movie.query.count()
            article_count = Article.query.count()
            trend_count = TrendingData.query.count()
            
            print(f"📊 最終統計:")
            print(f"   🎬 映画データ: {movie_count} 件")
            print(f"   📰 記事データ: {article_count} 件")
            print(f"   📈 トレンドデータ: {trend_count} 件")
            
            return True
            
        except Exception as e:
            print(f"❌ データベース初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

def check_database_health():
    """データベースの健全性チェック"""
    print("🔍 データベース健全性チェック中...")
    
    with app.app_context():
        try:
            # 基本接続テスト
            db.session.execute(db.text('SELECT 1'))
            print("✅ データベース接続: OK")
            
            # テーブル存在チェック
            tables_to_check = [
                ('movies', Movie),
                ('articles', Article), 
                ('trending_data', TrendingData)
            ]
            
            for table_name, model_class in tables_to_check:
                try:
                    count = model_class.query.count()
                    print(f"✅ {table_name}テーブル: {count} 件")
                except Exception as e:
                    print(f"❌ {table_name}テーブルエラー: {e}")
                    return False
            
            # インデックス確認
            try:
                result = db.session.execute(db.text("""
                    SELECT tablename, indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """))
                indexes = result.fetchall()
                print(f"📋 インデックス数: {len(indexes)}")
                
            except Exception as e:
                print(f"⚠️ インデックス確認スキップ: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ ヘルスチェック失敗: {e}")
            return False

if __name__ == "__main__":
    print("🚀 PostgreSQL データベース初期化スクリプト")
    print("=" * 60)
    
    # 環境変数確認
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        exit(1)
    
    print(f"🔗 データベースURL: {database_url[:50]}...")
    
    # 健全性チェック
    if check_database_health():
        print("ℹ️ データベースは既に初期化済みです")
    else:
        print("⚡ データベースを初期化します...")
        if init_database():
            print("✅ 初期化成功！")
        else:
            print("❌ 初期化失敗")
            exit(1)
    
    print("=" * 60)
    print("🎉 データベース準備完了！アプリケーションを起動できます。")