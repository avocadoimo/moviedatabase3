#!/usr/bin/env python3
"""
強化版データベース初期化スクリプト（興収推移データ対応）
SNSランキング表示用により多くのサンプルデータを投入
"""

import os
import sys
from datetime import datetime, timedelta

def main():
    print("🚀 強化版データベース初期化開始（興収推移データ対応）")
    print("=" * 60)
    
    # 環境変数確認
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL確認: {database_url[:50]}...")
    
    # PostgreSQL URLをSQLAlchemy形式に変換
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        os.environ["DATABASE_URL"] = database_url
        print("✅ DATABASE_URL形式を修正しました")
    
    try:
        # アプリのインポート
        from app import app, db, Movie, Article, TrendingData, ChatMessage, BoxOfficeData
        print("✅ アプリモジュールのインポート成功")
    except Exception as e:
        print(f"❌ アプリのインポート失敗: {e}")
        sys.exit(1)
    
    with app.app_context():
        try:
            # データベース接続テスト
            result = db.session.execute(db.text('SELECT version()'))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL接続成功: {version[:80]}...")
            
            # 既存テーブルを削除（強制リセット）
            print("🔧 既存テーブルを強制削除中...")
            try:
                db.drop_all()
                print("✅ 既存テーブル削除完了")
            except Exception as e:
                print(f"⚠️ テーブル削除スキップ（初回作成の可能性）: {e}")
            
            # 全テーブルを新規作成
            print("🔧 全テーブルを新規作成中...")
            db.create_all()
            print("✅ 全テーブル作成完了")
            
            # 強化版サンプルデータの投入
            print("🔧 強化版サンプルデータを投入中...")
            
            # 映画データ（15作品）
            sample_movies = [
                Movie(movie_id="1", title="劇場版「鬼滅の刃」無限列車編", revenue=404.3, year=2020, 
                      release_date="2020/10/16", category="邦画", distributor="東宝", 
                      description="炭治郎と仲間たちが無限列車で鬼と戦う物語。", director="外崎春雄", 
                      author="吾峠呼世晴", actor="花江夏樹、鬼頭明里、下野紘", genre="アニメ、アクション"),
                
                Movie(movie_id="2", title="千と千尋の神隠し", revenue=316.8, year=2001, 
                      release_date="2001/7/20", category="邦画", distributor="東宝", 
                      description="不思議な世界に迷い込んだ少女の冒険。", director="宮崎駿", 
                      author="宮崎駿", actor="柊瑠美、入野自由、夏木マリ", genre="アニメ、ファミリー"),
                
                Movie(movie_id="3", title="タイタニック", revenue=262.0, year=1997, 
                      release_date="1997/12/20", category="洋画", distributor="20世紀フォックス", 
                      description="豪華客船タイタニック号での悲劇的な恋愛物語。", director="ジェームズ・キャメロン", 
                      author="ジェームズ・キャメロン", actor="レオナルド・ディカプリオ、ケイト・ウィンスレット", genre="ドラマ、恋愛"),
                
                Movie(movie_id="4", title="アナと雪の女王", revenue=255.0, year=2014, 
                      release_date="2014/3/14", category="洋画", distributor="ウォルト・ディズニー・ジャパン", 
                      description="魔法の力を持つ姉妹の絆を描いたミュージカル。", director="クリス・バック、ジェニファー・リー", 
                      author="ハンス・クリスチャン・アンデルセン", actor="神田沙也加、松たか子", genre="アニメ、ミュージカル"),
                
                Movie(movie_id="5", title="君の名は。", revenue=251.7, year=2016, 
                      release_date="2016/8/26", category="邦画", distributor="東宝", 
                      description="時空を超えて入れ替わる男女の恋愛物語。", director="新海誠", 
                      author="新海誠", actor="神木隆之介、上白石萌音", genre="アニメ、恋愛"),
                
                Movie(movie_id="6", title="ハリー・ポッターと賢者の石", revenue=203.0, year=2001, 
                      release_date="2001/12/1", category="洋画", distributor="ワーナー・ブラザース映画", 
                      description="魔法使いの少年ハリー・ポッターの冒険を描いた第1作。", director="クリス・コロンバス", 
                      author="J.K.ローリング", actor="ダニエル・ラドクリフ、エマ・ワトソン、ルパート・グリント", genre="ファンタジー、アドベンチャー"),
                
                Movie(movie_id="7", title="もののけ姫", revenue=201.8, year=1997, 
                      release_date="1997/7/12", category="邦画", distributor="東宝", 
                      description="人間と自然の対立を描いた宮崎駿監督の名作アニメーション。", director="宮崎駿", 
                      author="宮崎駿", actor="松田洋治、石田ゆり子、田中裕子", genre="アニメ、ドラマ"),
                
                Movie(movie_id="8", title="ハウルの動く城", revenue=196.0, year=2004, 
                      release_date="2004/11/20", category="邦画", distributor="東宝", 
                      description="魔法によって老婆にされた少女ソフィーとハウルの恋物語。", director="宮崎駿", 
                      author="ダイアナ・ウィン・ジョーンズ", actor="倍賞千恵子、木村拓哉、美輪明宏", genre="アニメ、恋愛"),
                
                Movie(movie_id="9", title="踊る大捜査線 THE MOVIE 2", revenue=173.5, year=2003, 
                      release_date="2003/7/19", category="邦画", distributor="東宝", 
                      description="青島俊作刑事の活躍を描いた人気シリーズの劇場版第2弾。", director="本広克行", 
                      author="君塚良一", actor="織田裕二、柳葉敏郎、深津絵里", genre="アクション、コメディ"),
                
                Movie(movie_id="10", title="風の谷のナウシカ", revenue=165.0, year=1984, 
                      release_date="1984/3/11", category="邦画", distributor="東映", 
                      description="汚染された世界で生きる少女ナウシカの物語。", director="宮崎駿", 
                      author="宮崎駿", actor="島本須美、納谷悟朗、松田洋治", genre="アニメ、SF"),
                
                Movie(movie_id="11", title="スパイダーマン", revenue=150.0, year=2002, 
                      release_date="2002/5/1", category="洋画", distributor="ソニー・ピクチャーズ", 
                      description="クモに噛まれて超能力を得た青年の活躍。", director="サム・ライミ", 
                      author="スタン・リー", actor="トビー・マグワイア、キルスティン・ダンスト", genre="アクション、SF"),
                
                Movie(movie_id="12", title="ワンピース", revenue=135.0, year=2022, 
                      release_date="2022/8/6", category="邦画", distributor="東映", 
                      description="海賊王を目指すルフィの冒険。", director="谷口悟朗", 
                      author="尾田栄一郎", actor="田中真弓、岡村明美、中井和哉", genre="アニメ、アドベンチャー"),
                
                Movie(movie_id="13", title="呪術廻戦", revenue=130.0, year=2021, 
                      release_date="2021/12/24", category="邦画", distributor="東宝", 
                      description="呪術師として戦う高校生たちの物語。", director="朴性厚", 
                      author="芥見下々", actor="榎木淳弥、瀬戸麻沙美、内田雄馬", genre="アニメ、アクション"),
                
                Movie(movie_id="14", title="アバター", revenue=125.0, year=2009, 
                      release_date="2009/12/23", category="洋画", distributor="20世紀フォックス", 
                      description="異星で展開されるSFスペクタクル。", director="ジェームズ・キャメロン", 
                      author="ジェームズ・キャメロン", actor="サム・ワーシントン、ゾーイ・サルダナ", genre="SF、アクション"),
                
                Movie(movie_id="15", title="スーパーマン", revenue=120.0, year=2013, 
                      release_date="2013/8/30", category="洋画", distributor="ワーナー・ブラザース映画", 
                      description="地球を守るスーパーヒーローの活躍。", director="ザック・スナイダー", 
                      author="ジェリー・シーゲル", actor="ヘンリー・カヴィル、エイミー・アダムス", genre="アクション、SF")
            ]
            
            for movie in sample_movies:
                db.session.add(movie)
            
            print(f"✅ サンプル映画データ追加: {len(sample_movies)} 件")
            
            # 興収推移データ（上位5作品のみ詳細データ）
            box_office_data = [
                # 鬼滅の刃
                BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                            week="第1週", weekend_revenue="46.2", weekly_revenue="46.2", total_revenue="46.2"),
                BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                            week="第2週", weekend_revenue="27.1", weekly_revenue="27.1", total_revenue="107.5"),
                BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                            week="第3週", weekend_revenue="21.9", weekly_revenue="21.9", total_revenue="157.9"),
                BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                            week="第4週", weekend_revenue="17.8", weekly_revenue="17.8", total_revenue="204.8"),
                BoxOfficeData(movie_id="1", year=2020, title="劇場版「鬼滅の刃」無限列車編", 
                            week="第5週", weekend_revenue="12.5", weekly_revenue="12.5", total_revenue="259.2"),
                
                # 千と千尋の神隠し
                BoxOfficeData(movie_id="2", year=2001, title="千と千尋の神隠し", 
                            week="第1週", weekend_revenue="9.8", weekly_revenue="9.8", total_revenue="9.8"),
                BoxOfficeData(movie_id="2", year=2001, title="千と千尋の神隠し", 
                            week="第2週", weekend_revenue="8.2", weekly_revenue="8.2", total_revenue="25.6"),
                BoxOfficeData(movie_id="2", year=2001, title="千と千尋の神隠し", 
                            week="第3週", weekend_revenue="7.9", weekly_revenue="7.9", total_revenue="39.8"),
                BoxOfficeData(movie_id="2", year=2001, title="千と千尋の神隠し", 
                            week="第4週", weekend_revenue="6.5", weekly_revenue="6.5", total_revenue="52.3"),
                BoxOfficeData(movie_id="2", year=2001, title="千と千尋の神隠し", 
                            week="第5週", weekend_revenue="5.8", weekly_revenue="5.8", total_revenue="65.1"),
                
                # タイタニック
                BoxOfficeData(movie_id="3", year=1997, title="タイタニック", 
                            week="第1週", weekend_revenue="8.5", weekly_revenue="8.5", total_revenue="8.5"),
                BoxOfficeData(movie_id="3", year=1997, title="タイタニック", 
                            week="第2週", weekend_revenue="12.3", weekly_revenue="12.3", total_revenue="26.8"),
                BoxOfficeData(movie_id="3", year=1997, title="タイタニック", 
                            week="第3週", weekend_revenue="15.2", weekly_revenue="15.2", total_revenue="48.9"),
                BoxOfficeData(movie_id="3", year=1997, title="タイタニック", 
                            week="第4週", weekend_revenue="18.7", weekly_revenue="18.7", total_revenue="75.6"),
                BoxOfficeData(movie_id="3", year=1997, title="タイタニック", 
                            week="第5週", weekend_revenue="16.8", weekly_revenue="16.8", total_revenue="102.4"),
                
                # アナと雪の女王
                BoxOfficeData(movie_id="4", year=2014, title="アナと雪の女王", 
                            week="第1週", weekend_revenue="9.7", weekly_revenue="9.7", total_revenue="9.7"),
                BoxOfficeData(movie_id="4", year=2014, title="アナと雪の女王", 
                            week="第2週", weekend_revenue="11.2", weekly_revenue="11.2", total_revenue="29.3"),
                BoxOfficeData(movie_id="4", year=2014, title="アナと雪の女王", 
                            week="第3週", weekend_revenue="13.8", weekly_revenue="13.8", total_revenue="52.1"),
                BoxOfficeData(movie_id="4", year=2014, title="アナと雪の女王", 
                            week="第4週", weekend_revenue="15.4", weekly_revenue="15.4", total_revenue="78.9"),
                BoxOfficeData(movie_id="4", year=2014, title="アナと雪の女王", 
                            week="第5週", weekend_revenue="12.1", weekly_revenue="12.1", total_revenue="101.2"),
                
                # 君の名は。
                BoxOfficeData(movie_id="5", year=2016, title="君の名は。", 
                            week="第1週", weekend_revenue="12.8", weekly_revenue="12.8", total_revenue="12.8"),
                BoxOfficeData(movie_id="5", year=2016, title="君の名は。", 
                            week="第2週", weekend_revenue="16.3", weekly_revenue="16.3", total_revenue="38.9"),
                BoxOfficeData(movie_id="5", year=2016, title="君の名は。", 
                            week="第3週", weekend_revenue="18.2", weekly_revenue="18.2", total_revenue="68.7"),
                BoxOfficeData(movie_id="5", year=2016, title="君の名は。", 
                            week="第4週", weekend_revenue="14.7", weekly_revenue="14.7", total_revenue="92.4"),
                BoxOfficeData(movie_id="5", year=2016, title="君の名は。", 
                            week="第5週", weekend_revenue="11.9", weekly_revenue="11.9", total_revenue="116.8"),
            ]
            
            for box_office in box_office_data:
                db.session.add(box_office)
            
            print(f"✅ サンプル興収推移データ追加: {len(box_office_data)} 件")
            
            # トレンドデータ（過去7日分）
            base_date = datetime.now()
            trend_data = []
            
            # 映画タイトルリスト（データベースのタイトルと一致させる）
            trending_movies = [
                "劇場版「鬼滅の刃」無限列車編", "千と千尋の神隠し", "君の名は。", "タイタニック", 
                "アナと雪の女王", "ハリー・ポッターと賢者の石", "もののけ姫", "ハウルの動く城",
                "踊る大捜査線 THE MOVIE 2", "風の谷のナウシカ", "スパイダーマン", "ワンピース",
                "呪術廻戦", "アバター", "スーパーマン"
            ]
            
            # 過去7日分のデータを生成
            for days_ago in range(7):
                current_date = (base_date - timedelta(days=days_ago)).strftime('%Y/%m/%d')
                
                # 各映画の投稿数を生成（1位から15位まで）
                for i, movie_title in enumerate(trending_movies):
                    # 基本投稿数（順位が高いほど多い）
                    base_count = 10000 - (i * 500)
                    
                    # 日による変動（±30%）
                    import random
                    variation = random.randint(70, 130) / 100
                    post_count = int(base_count * variation)
                    
                    # 週末は1.2倍
                    date_obj = base_date - timedelta(days=days_ago)
                    if date_obj.weekday() in [5, 6]:  # 土日
                        post_count = int(post_count * 1.2)
                    
                    trend_data.append(TrendingData(
                        date=current_date,
                        movie_title=movie_title,
                        post_count=max(100, post_count)  # 最小100投稿
                    ))
            
            for trend in trend_data:
                db.session.add(trend)
            
            print(f"✅ サンプルトレンドデータ追加: {len(trend_data)} 件")
            
            # 記事データ
            sample_articles = [
                Article(
                    title="映画データベースへようこそ",
                    content="日本の映画興行収入データとSNSトレンド分析を提供する総合映画データベースです。リアルタイムの投稿数ランキングと詳細な興収推移データをお楽しみください。",
                    excerpt="映画データベースの使い方とサイトの概要（興収推移機能付き）",
                    author="管理者", category="お知らせ", tags="サイト紹介,使い方,興収推移", is_featured=True
                ),
                Article(
                    title="興収推移機能の使い方",
                    content="新機能「興収推移データ」では、映画の週末興収・累計興収・週間興収の詳細な推移をグラフとテーブルで確認できます。映画詳細ページの興行収入欄にある「推移データ」をクリックしてご利用ください。",
                    excerpt="興収推移機能の詳細な使い方ガイド",
                    author="編集部", category="使い方", tags="興収推移,使い方,グラフ,機能"
                )
            ]
            
            for article in sample_articles:
                db.session.add(article)
            
            print(f"✅ サンプル記事データ追加: {len(sample_articles)} 件")
            
            # データをコミット
            db.session.commit()
            print("✅ 全データのコミット完了")
            
            # 最終確認
            final_movie_count = Movie.query.count()
            final_article_count = Article.query.count()
            final_trending_count = TrendingData.query.count()
            final_box_office_count = BoxOfficeData.query.count()
            
            # 利用可能日付確認
            dates = db.session.query(TrendingData.date).distinct().order_by(TrendingData.date.desc()).all()
            date_list = [d[0] for d in dates]
            
            print("\n📊 データベース初期化完了:")
            print(f"   🎬 映画データ: {final_movie_count} 件")
            print(f"   📰 記事データ: {final_article_count} 件")
            print(f"   📈 トレンドデータ: {final_trending_count} 件")
            print(f"   📊 興収推移データ: {final_box_office_count} 件")
            print(f"   📅 利用可能日付: {len(date_list)} 日")
            print(f"   📅 日付範囲: {date_list[-1] if date_list else 'なし'} ～ {date_list[0] if date_list else 'なし'}")
            
            # 最新日のトップ5表示
            if date_list:
                latest_date = date_list[0]
                top_trends = TrendingData.query.filter_by(date=latest_date)\
                                              .order_by(TrendingData.post_count.desc())\
                                              .limit(5).all()
                
                print(f"\n🏆 最新日({latest_date})のトップ5:")
                for i, trend in enumerate(top_trends, 1):
                    print(f"   {i}. {trend.movie_title}: {trend.post_count:,} 投稿")
            
            # 興収推移データがある映画の確認
            box_office_movies = db.session.query(BoxOfficeData.movie_id).distinct().all()
            print(f"\n📊 興収推移データがある映画: {len(box_office_movies)} 作品")
            for box_office_movie in box_office_movies[:5]:
                movie = Movie.query.filter_by(movie_id=box_office_movie[0]).first()
                if movie:
                    box_office_count = BoxOfficeData.query.filter_by(movie_id=movie.movie_id).count()
                    print(f"   {movie.title}: {box_office_count} 週分のデータ")
            
            print("\n🎉 強化版データベース初期化成功！")
            print("💡 /trending でSNSランキングを確認できます。")
            print("💡 映画詳細ページの「推移データ」で興収推移を確認できます。")
            return True
            
        except Exception as e:
            print(f"❌ データベース初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass
            return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ 初期化に失敗しました")
        sys.exit(1)
    else:
        print("✅ 初期化完了")
        sys.exit(0)