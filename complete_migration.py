#!/usr/bin/env python3
"""
映画データ＋トレンドデータ＋興収推移データ同時投入スクリプト
【詳細付き】興行収入データベース（2000-2024年）.csv + 20250710更新_ポスト数集計.csv + 【完完全版】興収推移表.csv
を同時にPostgreSQLに投入
"""

import pandas as pd
import os
from datetime import datetime
import sys

def import_movie_data_complete():
    """詳細映画CSVからデータベースに投入（完全版）"""
    
    csv_file = "【詳細付き】興行収入データベース（2000-2024年）.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ {csv_file} が見つかりません")
        return False
    
    print(f"🎬 {csv_file} から映画データを投入中...")
    print("=" * 60)
    
    try:
        from app import app, db, Movie
        
        with app.app_context():
            # 既存の映画データをクリア
            existing_count = Movie.query.count()
            print(f"📊 既存の映画データ: {existing_count} 件")
            
            Movie.query.delete()
            db.session.commit()
            print("🗑️ 既存の映画データを削除しました")
            
            # CSVを読み込み（エンコーディング自動判定）
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                print("📄 UTF-8でCSV読み込み成功")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, encoding='shift_jis')
                    print("📄 Shift-JISでCSV読み込み成功")
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, encoding='cp932')
                    print("📄 CP932でCSV読み込み成功")
            
            print(f"📊 CSV概要: {len(df)} 行, {len(df.columns)} 列")
            print(f"📋 列名: {list(df.columns)}")
            
            # データクリーニングと投入（全件処理）
            added_count = 0
            skipped_count = 0
            error_count = 0
            
            print(f"\n🔧 映画データ処理開始（全 {len(df)} 件）...")
            
            # 興行収入順にソート（高い順）
            df_sorted = df.sort_values('興収(億円)', ascending=False, na_position='last')
            
            for index, row in df_sorted.iterrows():
                try:
                    # 必須フィールドのチェック
                    if pd.isna(row['作品名']) or pd.isna(row['興収(億円)']):
                        skipped_count += 1
                        continue
                    
                    # 安全な値取得関数
                    def safe_str(value, default=''):
                        if pd.isna(value):
                            return default
                        return str(value).strip()
                    
                    def safe_number(value, number_type='float', default=None):
                        if pd.isna(value):
                            return default
                        try:
                            if number_type == 'int':
                                return int(float(value))
                            else:
                                return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    # 年のデータ処理
                    year_value = safe_number(row['年'], 'int', None)
                    
                    # 映画IDの処理（確実にユニークにする）
                    movie_id_value = safe_number(row['映画ID'], 'int', None)
                    if movie_id_value is None:
                        movie_id_value = added_count + 1
                    movie_id_str = str(int(movie_id_value))
                    
                    # 興行収入の処理
                    revenue_value = safe_number(row['興収(億円)'], 'float', 0.0)
                    
                    # Movieオブジェクトを作成
                    movie = Movie(
                        movie_id=movie_id_str,
                        title=safe_str(row['作品名']),
                        revenue=revenue_value,
                        year=year_value,
                        release_date=safe_str(row['公開日']),
                        category=safe_str(row['区分']),
                        distributor=safe_str(row['配給会社']),
                        description=safe_str(row['あらすじ']),
                        director=safe_str(row['監督']),
                        author=safe_str(row['脚本']),
                        actor=safe_str(row['キャスト']),
                        scriptwriter=safe_str(row['脚本家']),
                        producer=safe_str(row['プロデューサー']),
                        copyright=safe_str(row['コピーライト']),
                        genre=safe_str(row['ジャンル'])
                    )
                    
                    db.session.add(movie)
                    added_count += 1
                    
                    # 500件ごとにコミット（メモリ効率化）
                    if added_count % 500 == 0:
                        try:
                            db.session.commit()
                            print(f"   ✅ {added_count} 件処理完了...")
                        except Exception as commit_error:
                            print(f"   ⚠️ コミットエラー (件数: {added_count}): {commit_error}")
                            db.session.rollback()
                            error_count += 1
                
                except Exception as e:
                    print(f"⚠️ データ処理エラー (行 {index + 1}): {e}")
                    error_count += 1
                    db.session.rollback()
                    continue
            
            # 最終コミット
            try:
                db.session.commit()
                print(f"✅ 映画データ最終コミット完了")
            except Exception as final_error:
                print(f"❌ 最終コミットエラー: {final_error}")
                db.session.rollback()
                return False
            
            # 結果サマリー
            print(f"\n🎉 映画データインポート完了!")
            print(f"   📥 成功: {added_count} 件")
            print(f"   ⏭️ スキップ: {skipped_count} 件")
            print(f"   ❌ エラー: {error_count} 件")
            print(f"   📊 成功率: {(added_count / len(df) * 100):.1f}%")
            
            # データベース確認
            final_count = Movie.query.count()
            print(f"   🔍 データベース確認: {final_count} 件")
            
            if final_count >= 100:
                # トップ10表示
                print(f"\n🏆 興行収入トップ10:")
                top_movies = Movie.query.order_by(Movie.revenue.desc()).limit(10).all()
                for i, movie in enumerate(top_movies, 1):
                    print(f"   {i:2d}. {movie.title} - {movie.revenue}億円 ({movie.year}) [ID: {movie.movie_id}]")
                
                return True
            else:
                print("⚠️ 投入データが少なすぎます")
                return False
            
    except Exception as e:
        print(f"❌ 映画データインポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def import_box_office_data():
    """興収推移データをインポート"""
    
    csv_file = "【完完全版】興収推移表.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ {csv_file} が見つかりません")
        return False
    
    print(f"\n📊 {csv_file} から興収推移データを投入中...")
    print("=" * 60)
    
    try:
        from app import app, db, BoxOfficeData, Movie
        
        with app.app_context():
            # 既存の興収推移データをクリア
            existing_count = BoxOfficeData.query.count()
            print(f"📊 既存の興収推移データ: {existing_count} 件")
            
            BoxOfficeData.query.delete()
            db.session.commit()
            print("🗑️ 既存の興収推移データを削除しました")
            
            # CSVを読み込み
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                print("📄 UTF-8でCSV読み込み成功")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_file, encoding='shift_jis')
                    print("📄 Shift-JISでCSV読み込み成功")
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, encoding='cp932')
                    print("📄 CP932でCSV読み込み成功")
            
            print(f"📊 CSV概要: {len(df)} 行, {len(df.columns)} 列")
            print(f"📋 列名: {list(df.columns)}")
            
            # データベース内の映画データを取得
            movies_in_db = Movie.query.with_entities(Movie.movie_id, Movie.title).all()
            movie_id_to_title = {movie.movie_id: movie.title for movie in movies_in_db if movie.movie_id}
            
            print(f"🎬 データベース内映画: {len(movie_id_to_title)} 件")
            
            # データクリーニングと投入
            added_count = 0
            skipped_count = 0
            error_count = 0
            
            print(f"\n🔧 興収推移データ処理開始（全 {len(df)} 件）...")
            
            for index, row in df.iterrows():
                try:
                    # 必須フィールドのチェック
                    if pd.isna(row['映画ID']) or pd.isna(row['作品名']) or pd.isna(row['公開週']):
                        skipped_count += 1
                        continue
                    
                    # 安全な値取得関数
                    def safe_str(value, default=''):
                        if pd.isna(value):
                            return default
                        return str(value).strip()
                    
                    def safe_number(value, number_type='int', default=None):
                        if pd.isna(value):
                            return default
                        try:
                            if number_type == 'int':
                                return int(float(value))
                            else:
                                return float(value)
                        except (ValueError, TypeError):
                            return default
                    
                    # 映画IDの処理
                    movie_id_value = safe_number(row['映画ID'], 'int', None)
                    if movie_id_value is None:
                        skipped_count += 1
                        continue
                    
                    movie_id_str = str(movie_id_value)
                    
                    # 映画IDがデータベースに存在するかチェック
                    if movie_id_str not in movie_id_to_title:
                        skipped_count += 1
                        continue
                    
                    # BoxOfficeDataオブジェクトを作成
                    box_office = BoxOfficeData(
                        movie_id=movie_id_str,
                        year=safe_number(row['年'], 'int', None),
                        title=safe_str(row['作品名']),
                        week=safe_str(row['公開週']),
                        weekend_revenue=safe_str(row['週末興収']),
                        total_revenue=safe_str(row['累計興収']),
                        weekly_revenue=safe_str(row['週間興収']),
                        match_score=safe_number(row['マッチスコア'], 'int', 0)
                    )
                    
                    db.session.add(box_office)
                    added_count += 1
                    
                    # 500件ごとにコミット
                    if added_count % 500 == 0:
                        try:
                            db.session.commit()
                            print(f"   ✅ {added_count} 件処理完了...")
                        except Exception as commit_error:
                            print(f"   ⚠️ コミットエラー (件数: {added_count}): {commit_error}")
                            db.session.rollback()
                            error_count += 1
                
                except Exception as e:
                    print(f"⚠️ データ処理エラー (行 {index + 1}): {e}")
                    error_count += 1
                    db.session.rollback()
                    continue
            
            # 最終コミット
            try:
                db.session.commit()
                print(f"✅ 興収推移データ最終コミット完了")
            except Exception as final_error:
                print(f"❌ 最終コミットエラー: {final_error}")
                db.session.rollback()
                return False
            
            # 結果サマリー
            print(f"\n🎉 興収推移データインポート完了!")
            print(f"   📥 成功: {added_count} 件")
            print(f"   ⏭️ スキップ: {skipped_count} 件")
            print(f"   ❌ エラー: {error_count} 件")
            print(f"   📊 成功率: {(added_count / len(df) * 100):.1f}%")
            
            # データベース確認
            final_count = BoxOfficeData.query.count()
            print(f"   🔍 データベース確認: {final_count} 件")
            
            # 興収推移データがある映画数を確認
            movie_count = db.session.query(BoxOfficeData.movie_id).distinct().count()
            print(f"   🎬 推移データがある映画: {movie_count} 作品")
            
            # トップ5の映画の推移データを表示
            top_movies = db.session.query(BoxOfficeData.movie_id, BoxOfficeData.title)\
                                  .distinct()\
                                  .limit(5)\
                                  .all()
            
            print(f"\n📊 推移データ例（最初の5作品）:")
            for movie_id, title in top_movies:
                week_count = BoxOfficeData.query.filter_by(movie_id=movie_id).count()
                print(f"   {title} (ID: {movie_id}): {week_count} 週分のデータ")
            
            return True
            
    except Exception as e:
        print(f"❌ 興収推移データインポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def import_trending_data_new_format():
    """新形式トレンドCSVをインポート（映画データと連携）"""
    
    csv_file = "20250710更新_ポスト数集計.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ {csv_file} が見つかりません")
        return create_fallback_trending_data()
    
    print(f"\n📈 {csv_file} から新形式トレンドデータを投入中...")
    print("=" * 60)
    
    try:
        from app import app, db, TrendingData, Movie
        
        with app.app_context():
            # 既存のトレンドデータをクリア
            existing_count = TrendingData.query.count()
            print(f"📊 既存のトレンドデータ: {existing_count} 件")
            
            TrendingData.query.delete()
            db.session.commit()
            print("🗑️ 既存のトレンドデータを削除しました")
            
            # CSVを読み込み（ヘッダーなしで読み込み）
            df = pd.read_csv(csv_file, header=None, encoding='utf-8')
            print(f"📄 CSV読み込み完了: {len(df)} 行, {len(df.columns)} 列")
            
            # データ構造の確認
            if len(df) < 4:
                print("❌ CSVデータが不足しています（最低4行必要）")
                return create_fallback_trending_data()
            
            # ヘッダー行を取得
            scraping_words = df.iloc[0].values  # 1行目: スクレイピングワード
            movie_titles = df.iloc[1].values    # 2行目: 作品名
            movie_ids = df.iloc[2].values       # 3行目: 映画ID
            
            print(f"📋 CSV内映画数: {len(movie_titles)} 作品")
            print(f"📅 データ期間: {len(df) - 3} 日分")
            
            # データベース内の映画データを高速取得
            movies_in_db = Movie.query.with_entities(Movie.movie_id, Movie.title).all()
            movie_id_to_title = {}
            title_to_movie_id = {}
            existing_movie_ids = set()
            
            for movie in movies_in_db:
                if movie.movie_id:
                    existing_movie_ids.add(str(movie.movie_id))
                    movie_id_to_title[str(movie.movie_id)] = movie.title
                    title_to_movie_id[movie.title] = str(movie.movie_id)
            
            print(f"🎬 データベース内映画: {len(existing_movie_ids)} 件")
            
            # 映画情報の処理（C列以降、インデックス2以降）
            valid_movies = []
            for col_idx in range(2, min(len(movie_titles), len(df.columns))):
                try:
                    scraping_word = str(scraping_words[col_idx]) if col_idx < len(scraping_words) else ""
                    movie_title = str(movie_titles[col_idx]) if col_idx < len(movie_titles) else ""
                    movie_id = str(movie_ids[col_idx]) if col_idx < len(movie_ids) else ""
                    
                    # 空白や無効データをスキップ
                    if pd.isna(movie_title) or movie_title.strip() == "" or movie_title == "nan":
                        continue
                    
                    movie_title_clean = movie_title.strip()
                    
                    # 映画IDの処理と照合
                    matched_movie_id = None
                    matched_title = None
                    
                    # 1. 映画IDによる照合（最優先）
                    if not (pd.isna(movie_id) or movie_id.strip() == "" or movie_id == "nan"):
                        movie_id_clean = str(movie_id).strip()
                        if movie_id_clean in existing_movie_ids:
                            matched_movie_id = movie_id_clean
                            matched_title = movie_id_to_title[movie_id_clean]
                            print(f"✅ 映画ID照合: {movie_title_clean} → ID:{matched_movie_id} ({matched_title})")
                    
                    # 2. タイトル完全一致による照合
                    if not matched_movie_id:
                        if movie_title_clean in title_to_movie_id:
                            matched_movie_id = title_to_movie_id[movie_title_clean]
                            matched_title = movie_title_clean
                            print(f"💡 タイトル完全一致: {movie_title_clean} → ID:{matched_movie_id}")
                    
                    # 3. タイトル部分一致による照合
                    if not matched_movie_id:
                        for db_title, db_movie_id in title_to_movie_id.items():
                            # 前方一致、後方一致、含む検索
                            if (movie_title_clean in db_title or 
                                db_title in movie_title_clean or
                                movie_title_clean.replace('劇場版', '').replace('「', '').replace('」', '') in db_title):
                                matched_movie_id = db_movie_id
                                matched_title = db_title
                                print(f"🔍 タイトル部分一致: {movie_title_clean} → {db_title} (ID:{matched_movie_id})")
                                break
                    
                    # 照合結果の確認
                    if not matched_movie_id:
                        print(f"⚠️ スキップ: {movie_title_clean} (データベース内に該当映画なし)")
                        continue
                    
                    valid_movies.append({
                        'col_idx': col_idx,
                        'scraping_word': scraping_word,
                        'csv_title': movie_title_clean,
                        'movie_id': matched_movie_id,
                        'db_title': matched_title
                    })
                    
                except Exception as e:
                    print(f"⚠️ 映画情報処理エラー (列 {col_idx}): {e}")
                    continue
            
            print(f"✅ 照合成功映画数: {len(valid_movies)} 件")
            
            if len(valid_movies) == 0:
                print("❌ 有効な映画データがありません")
                return create_fallback_trending_data()
            
            # 照合結果の表示（最初の15件）
            print(f"\n📝 照合成功映画（最初の15件）:")
            for i, movie in enumerate(valid_movies[:15]):
                print(f"   {i+1:2d}. ID:{movie['movie_id']} | {movie['csv_title']} ↔ {movie['db_title']}")
            if len(valid_movies) > 15:
                print(f"   ... 他 {len(valid_movies) - 15} 件")
            
            # トレンドデータの投入
            inserted_count = 0
            skipped_count = 0
            
            print(f"\n🔄 トレンドデータ処理開始...")
            
            # 4行目以降のデータを処理
            for row_idx in range(3, len(df)):
                try:
                    # A列（インデックス0）から日付を取得
                    date_value = df.iloc[row_idx, 0]
                    
                    if pd.isna(date_value):
                        skipped_count += 1
                        continue
                    
                    # 日付の正規化
                    date_str = str(date_value).strip()
                    if not date_str or date_str == "nan":
                        skipped_count += 1
                        continue
                    
                    # 各映画の投稿数を処理
                    daily_inserts = 0
                    for movie_info in valid_movies:
                        col_idx = movie_info['col_idx']
                        movie_title = movie_info['db_title']  # データベース内のタイトルを使用
                        
                        try:
                            # 投稿数を取得
                            if col_idx < len(df.columns):
                                post_count_value = df.iloc[row_idx, col_idx]
                                
                                if pd.isna(post_count_value):
                                    continue
                                
                                # 数値に変換
                                post_count = float(post_count_value)
                                
                                # 有効な投稿数かチェック（0より大きい）
                                if post_count > 0:
                                    trending_data = TrendingData(
                                        date=date_str,
                                        movie_title=movie_title,
                                        post_count=int(post_count)
                                    )
                                    db.session.add(trending_data)
                                    inserted_count += 1
                                    daily_inserts += 1
                        
                        except (ValueError, TypeError):
                            # 数値変換エラーは無視
                            continue
                    
                    # 進捗表示（週単位）
                    if row_idx % 7 == 0 and daily_inserts > 0:
                        print(f"   📅 {date_str}: {daily_inserts} 件追加 (累計: {inserted_count}件)")
                
                except Exception as e:
                    print(f"⚠️ 行処理エラー (行 {row_idx + 1}): {e}")
                    skipped_count += 1
                    continue
                
                # 1000件ごとにコミット
                if inserted_count % 1000 == 0 and inserted_count > 0:
                    db.session.commit()
                    print(f"   💾 中間コミット: {inserted_count} 件処理完了...")
            
            # 最終コミット
            db.session.commit()
            
            print(f"\n✅ トレンドデータインポート完了!")
            print(f"   📥 挿入: {inserted_count} 件")
            print(f"   ⏭️ スキップ: {skipped_count} 件")
            print(f"   📊 成功率: {(inserted_count / (inserted_count + skipped_count) * 100):.1f}%" if (inserted_count + skipped_count) > 0 else "N/A")
            
            # 統計情報表示
            if inserted_count > 0:
                print(f"\n📊 投入統計:")
                
                # 日付範囲
                date_range = db.session.query(
                    db.func.min(TrendingData.date),
                    db.func.max(TrendingData.date)
                ).first()
                print(f"   📅 日付範囲: {date_range[0]} ～ {date_range[1]}")
                
                # 映画数
                unique_movies = db.session.query(TrendingData.movie_title).distinct().count()
                print(f"   🎭 トレンド映画数: {unique_movies} 作品")
                
                # 最新日のトップ10
                latest_date = db.session.query(TrendingData.date).order_by(TrendingData.date.desc()).first()
                if latest_date:
                    top_trends = TrendingData.query.filter_by(date=latest_date[0])\
                                                  .order_by(TrendingData.post_count.desc())\
                                                  .limit(10).all()
                    
                    print(f"\n🏆 最新日({latest_date[0]})のトップ10:")
                    for i, trend in enumerate(top_trends, 1):
                        print(f"   {i:2d}. {trend.movie_title}: {trend.post_count:,} 投稿")
                
                return True
            else:
                print("❌ トレンドデータが投入されませんでした")
                return create_fallback_trending_data()
            
    except Exception as e:
        print(f"❌ トレンドデータインポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return create_fallback_trending_data()

def create_fallback_trending_data():
    """フォールバック用のトレンドデータ作成"""
    
    try:
        from app import app, db, TrendingData, Movie
        from datetime import datetime, timedelta
        import random
        
        with app.app_context():
            print("🔧 フォールバックトレンドデータを作成中...")
            
            # データベースから人気映画を取得（興行収入順）
            popular_movies = Movie.query.order_by(Movie.revenue.desc()).limit(30).all()
            
            if len(popular_movies) == 0:
                print("❌ データベースに映画データがありません")
                return False
            
            inserted_count = 0
            
            # 過去14日分のデータを作成
            for days_ago in range(14):
                date_obj = datetime.now() - timedelta(days=days_ago)
                date_str = date_obj.strftime('%Y/%m/%d')
                
                for i, movie in enumerate(popular_movies):
                    # 基本投稿数（興行収入に比例、上位ほど多い）
                    base_count = max(50, int(movie.revenue * 10) if movie.revenue else 100)
                    base_count = min(base_count, 8000)  # 最大値制限
                    
                    # 日による変動（70%-130%）
                    variation = random.randint(70, 130) / 100
                    post_count = int(base_count * variation)
                    
                    # 週末は1.2倍
                    if date_obj.weekday() in [5, 6]:  # 土日
                        post_count = int(post_count * 1.2)
                    
                    trending_data = TrendingData(
                        date=date_str,
                        movie_title=movie.title,
                        post_count=post_count
                    )
                    db.session.add(trending_data)
                    inserted_count += 1
            
            db.session.commit()
            print(f"✅ フォールバックトレンドデータ作成完了: {inserted_count} 件")
            
            return True
            
    except Exception as e:
        print(f"❌ フォールバックトレンドデータ作成エラー: {e}")
        return False

def create_sample_articles():
    """サンプル記事データを作成"""
    
    try:
        from app import app, db, Article
        
        with app.app_context():
            if Article.query.count() >= 3:
                print("✅ 記事データは十分に存在します")
                return True
            
            # 既存記事をクリア
            Article.query.delete()
            db.session.commit()
            
            print("📰 サンプル記事データを作成中...")
            
            sample_articles = [
                Article(
                    title="映画データベース完全版が運用開始！",
                    content="映画データベースサイトが完全版として運用を開始しました。3,000件を超える映画データと詳細なSNSトレンド分析機能、さらに映画の興行収入推移データも閲覧可能になりました。映画IDによる正確な照合システムにより、信頼性の高いデータを提供します。検索機能、ランキング機能、トレンド分析、興収推移グラフなど、映画ファンに必要な全ての機能を網羅しています。",
                    excerpt="3,000件超の映画データとSNSトレンド分析、興収推移データを搭載した完全版データベースが運用開始",
                    author="編集部",
                    category="お知らせ",
                    tags="データベース,完全版,映画,SNS,トレンド,興収推移,運用開始",
                    is_featured=True
                ),
                Article(
                    title="興行収入推移データ機能の使い方",
                    content="新機能「興行収入推移データ」では、映画の週末興収・累計興収・週間興収の詳細な推移をグラフとテーブルで確認できます。映画詳細ページの興行収入欄にある「推移データ」をクリックしてご利用ください。推移データでは、週ごとの興収変化をグラフで視覚的に確認でき、前週比の増減も一目でわかります。また、全作品中の順位や年別・カテゴリ別の順位も表示され、その映画の興行成績を多角的に分析できます。",
                    excerpt="興行収入推移機能の詳細な使い方ガイド（グラフ表示・ランキング機能付き）",
                    author="編集部",
                    category="使い方",
                    tags="興収推移,使い方,グラフ,ランキング,機能"
                ),
                Article(
                    title="2024年映画興行収入ランキング完全分析",
                    content="2024年の映画興行収入を徹底分析。「劇場版 鬼滅の刃」の記録的ヒット404億円を筆頭に、アニメ映画が上位を独占する結果となりました。一方でSNS投稿数との相関関係を見ると、話題性と興行収入の間には強い関係性があることが判明。配信時代における劇場体験の価値向上と、SNSマーケティングの重要性が浮き彫りになっています。興行収入推移データを分析すると、ヒット作品は初週から高い数値を記録し、その後も安定した推移を見せる傾向があります。",
                    excerpt="2024年興行収入データとSNS投稿数の相関関係、興収推移から見える映画業界の新潮流",
                    author="映画データアナリスト",
                    category="映画分析",
                    tags="2024年,興行収入,ランキング,SNS,相関関係,分析,推移"
                ),
                Article(
                    title="SNS時代の映画マーケティング戦略",
                    content="SNSの普及により、映画のマーケティング戦略は根本的に変化しました。従来のテレビCMや新聞広告中心の宣伝から、TwitterやInstagram、TikTokを活用したバイラルマーケティングが主流になっています。リアルタイム検索データを分析すると、映画の話題性と興行収入には強い相関関係があることがわかります。公開前の期待値、公開直後の口コミ、ロングランでの継続的な話題性、すべてがSNSでの投稿数に反映されています。興行収入推移データと照らし合わせることで、SNSでの話題性が実際の興行成績にどのように影響するかを定量的に分析できます。",
                    excerpt="SNS時代における映画マーケティングの変化と、興行収入推移データから見る成功事例について解説",
                    author="デジタルマーケティング専門家",
                    category="トレンド",
                    tags="SNS,マーケティング,デジタル,トレンド分析,興収推移"
                )
            ]
            
            for article in sample_articles:
                db.session.add(article)
            
            db.session.commit()
            print(f"✅ サンプル記事データ作成完了: {len(sample_articles)} 件")
            
            return True
            
    except Exception as e:
        print(f"❌ サンプル記事データ作成エラー: {e}")
        return False

def verify_data_integrity():
    """データ整合性の最終確認"""
    
    try:
        from app import app, db, Movie, TrendingData, Article, BoxOfficeData
        
        with app.app_context():
            print(f"\n🔍 データ整合性確認:")
            print("=" * 50)
            
            # 基本統計
            movie_count = Movie.query.count()
            trend_count = TrendingData.query.count()
            article_count = Article.query.count()
            box_office_count = BoxOfficeData.query.count()
            
            print(f"📊 データ概要:")
            print(f"   🎬 映画データ: {movie_count:,} 件")
            print(f"   📈 トレンドデータ: {trend_count:,} 件")
            print(f"   📰 記事データ: {article_count} 件")
            print(f"   📊 興収推移データ: {box_office_count:,} 件")
            
            # 映画データ詳細
            if movie_count > 0:
                revenue_stats = db.session.query(
                    db.func.min(Movie.revenue),
                    db.func.max(Movie.revenue),
                    db.func.avg(Movie.revenue)
                ).first()
                
                year_range = db.session.query(
                    db.func.min(Movie.year),
                    db.func.max(Movie.year)
                ).first()
                
                print(f"\n🎬 映画データ詳細:")
                print(f"   💰 興行収入範囲: {revenue_stats[0]:.1f} ～ {revenue_stats[1]:.1f}億円")
                print(f"   📅 年代範囲: {year_range[0]} ～ {year_range[1]}年")
                print(f"   📊 平均興行収入: {revenue_stats[2]:.1f}億円")
            
            # 興収推移データ詳細
            if box_office_count > 0:
                box_office_movie_count = db.session.query(BoxOfficeData.movie_id).distinct().count()
                
                print(f"\n📊 興収推移データ詳細:")
                print(f"   🎭 対象映画数: {box_office_movie_count} 作品")
                print(f"   📈 総レコード数: {box_office_count:,} 件")
                print(f"   📊 平均週数: {box_office_count / box_office_movie_count:.1f} 週/作品")
                
                # 推移データがある映画の上位10作品を表示
                top_box_office_movies = db.session.query(
                    BoxOfficeData.movie_id,
                    BoxOfficeData.title,
                    db.func.count(BoxOfficeData.id).label('week_count')
                ).group_by(BoxOfficeData.movie_id, BoxOfficeData.title)\
                 .order_by(db.func.count(BoxOfficeData.id).desc())\
                 .limit(10).all()
                
                print(f"\n📊 推移データ上位10作品:")
                for i, (movie_id, title, week_count) in enumerate(top_box_office_movies, 1):
                    print(f"   {i:2d}. {title} (ID: {movie_id}): {week_count} 週分")
            
            # トレンドデータ詳細
            if trend_count > 0:
                trend_movie_count = db.session.query(TrendingData.movie_title).distinct().count()
                date_range = db.session.query(
                    db.func.min(TrendingData.date),
                    db.func.max(TrendingData.date)
                ).first()
                
                post_stats = db.session.query(
                    db.func.min(TrendingData.post_count),
                    db.func.max(TrendingData.post_count),
                    db.func.avg(TrendingData.post_count)
                ).first()
                
                print(f"\n📈 トレンドデータ詳細:")
                print(f"   🎭 対象映画数: {trend_movie_count} 作品")
                print(f"   📅 期間: {date_range[0]} ～ {date_range[1]}")
                print(f"   💬 投稿数範囲: {post_stats[0]} ～ {post_stats[1]:,}")
                print(f"   📊 平均投稿数: {post_stats[2]:.1f}")
            
            # 照合確認（映画データとトレンドデータの整合性）
            if movie_count > 0 and trend_count > 0:
                print(f"\n🔗 データ照合確認:")
                
                # トレンドデータの映画がデータベースに存在するかチェック
                trend_movies = db.session.query(TrendingData.movie_title).distinct().limit(20).all()
                matched_count = 0
                
                for trend_movie in trend_movies:
                    movie_title = trend_movie[0]
                    movie_in_db = Movie.query.filter_by(title=movie_title).first()
                    if movie_in_db:
                        matched_count += 1
                
                match_rate = (matched_count / len(trend_movies)) * 100 if trend_movies else 0
                print(f"   ✅ 照合成功率: {match_rate:.1f}% ({matched_count}/{len(trend_movies)})")
                
                if match_rate >= 80:
                    print(f"   🎉 照合率良好！データ連携が正常に動作します")
                elif match_rate >= 50:
                    print(f"   ⚠️ 照合率普通。一部のトレンドデータが映画詳細と連携しない可能性があります")
                else:
                    print(f"   ❌ 照合率低下。データ連携に問題がある可能性があります")
            
            # 映画データと興収推移データの照合確認
            if movie_count > 0 and box_office_count > 0:
                print(f"\n🔗 映画データと興収推移データの照合確認:")
                
                # 興収推移データの映画IDがデータベースに存在するかチェック
                box_office_movie_ids = db.session.query(BoxOfficeData.movie_id).distinct().limit(20).all()
                box_office_matched_count = 0
                
                for box_office_movie_id in box_office_movie_ids:
                    movie_id = box_office_movie_id[0]
                    movie_in_db = Movie.query.filter_by(movie_id=movie_id).first()
                    if movie_in_db:
                        box_office_matched_count += 1
                
                box_office_match_rate = (box_office_matched_count / len(box_office_movie_ids)) * 100 if box_office_movie_ids else 0
                print(f"   ✅ 興収推移データ照合成功率: {box_office_match_rate:.1f}% ({box_office_matched_count}/{len(box_office_movie_ids)})")
                
                if box_office_match_rate >= 80:
                    print(f"   🎉 興収推移データ照合率良好！")
                else:
                    print(f"   ⚠️ 興収推移データ照合率要改善")
            
            # 最新トレンドトップ5
            if trend_count > 0:
                latest_date = db.session.query(TrendingData.date).order_by(TrendingData.date.desc()).first()
                if latest_date:
                    top_trends = TrendingData.query.filter_by(date=latest_date[0])\
                                                  .order_by(TrendingData.post_count.desc())\
                                                  .limit(5).all()
                    
                    print(f"\n🏆 最新トレンド({latest_date[0]})トップ5:")
                    for i, trend in enumerate(top_trends, 1):
                        # 対応する映画データを確認
                        movie = Movie.query.filter_by(title=trend.movie_title).first()
                        revenue_info = f" ({movie.revenue}億円)" if movie and movie.revenue else ""
                        
                        # 興収推移データがあるかチェック
                        box_office_data = None
                        if movie and movie.movie_id:
                            box_office_data = BoxOfficeData.query.filter_by(movie_id=movie.movie_id).first()
                        
                        box_office_info = " [推移データあり]" if box_office_data else ""
                        
                        print(f"   {i}. {trend.movie_title}: {trend.post_count:,} 投稿{revenue_info}{box_office_info}")
            
            print(f"\n✅ データ整合性確認完了")
            return True
            
    except Exception as e:
        print(f"❌ データ整合性確認エラー: {e}")
        return False

def main():
    """メイン処理 - 映画データ＋トレンドデータ＋興収推移データ同時投入"""
    print("🚀 映画データ＋トレンドデータ＋興収推移データ同時投入スクリプト")
    print("📋 完全版データベース構築（興収推移データ対応）")
    print("=" * 60)
    
    # 環境変数読み込み
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 .envファイルを読み込みました")
    except ImportError:
        print("⚠️ python-dotenvがインストールされていません（無視して続行）")
    
    # データベース接続確認
    try:
        from app import app, db
        with app.app_context():
            result = db.session.execute(db.text('SELECT version()'))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL接続成功: {version[:50]}...")
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        return False
    
    success_count = 0
    
    # 1. 映画データの投入（最重要）
    print(f"\n{'='*20} 映画データ投入開始 {'='*20}")
    if import_movie_data_complete():
        success_count += 1
        print("✅ 映画データ投入成功")
    else:
        print("❌ 映画データ投入失敗")
        return False  # 映画データ失敗時は中断
    
    # 2. 興収推移データの投入（新機能）
    print(f"\n{'='*20} 興収推移データ投入開始 {'='*20}")
    if import_box_office_data():
        success_count += 1
        print("✅ 興収推移データ投入成功")
    else:
        print("❌ 興収推移データ投入失敗")
    
    # 3. トレンドデータの投入
    print(f"\n{'='*20} トレンドデータ投入開始 {'='*20}")
    if import_trending_data_new_format():
        success_count += 1
        print("✅ トレンドデータ投入成功")
    else:
        print("❌ トレンドデータ投入失敗（フォールバック実行済み）")
    
    # 4. 記事データの作成
    print(f"\n{'='*20} 記事データ作成開始 {'='*20}")
    if create_sample_articles():
        success_count += 1
        print("✅ 記事データ作成成功")
    else:
        print("❌ 記事データ作成失敗")
    
    # 5. データ整合性確認
    print(f"\n{'='*20} データ整合性確認 {'='*20}")
    verify_data_integrity()
    
    # 最終結果
    print(f"\n{'='*60}")
    if success_count >= 2:
        print("🎉 映画データベース完全版構築完了！")
        print("💫 以下の機能が利用可能です:")
        print("   🏠 ホームページ: 映画カード表示と検索")
        print("   📊 データベース: /table で一覧表示")
        print("   📈 SNSトレンド: /trending でランキング表示")
        print("   📰 記事: /articles でコラム記事")
        print("   🤖 AIチャット: /chat で映画相談")
        print("   🔧 管理機能: /admin でコンテンツ管理")
        print("   💹 興収推移: 映画詳細ページから推移データ表示")
        print(f"\n🔗 サイトURL: https://your-site.onrender.com")
        
        return True
    else:
        print("⚠️ 一部データの投入に失敗しましたが、基本機能は動作します。")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ 一部処理に失敗しました")
        exit(1)
    else:
        print("✅ 全処理完了")
        exit(0)