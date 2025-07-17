#!/usr/bin/env python3
"""
Render起動時の自動初期化スクリプト
Renderのビルドコマンドまたは起動前に実行される
"""

import os
import sys
from datetime import datetime

def main():
    print("🚀 Render起動時初期化スクリプト開始")
    print("=" * 60)
    
    # 環境確認
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL確認: {database_url[:50]}...")
    
    # Flaskアプリのインポートと初期化
    try:
        from app import app, db, Movie, Article, TrendingData
        print("✅ Flaskアプリのインポート成功")
    except ImportError as e:
        print(f"❌ Flaskアプリのインポート失敗: {e}")
        sys.exit(1)
    
    # データベース初期化
    with app.app_context():
        try:
            # テーブル作成
            db.create_all()
            print("✅ データベーステーブル作成完了")
            
            # 接続確認
            if database_url.startswith("postgresql://"):
                result = db.session.execute(db.text('SELECT version()'))
                version = result.fetchone()[0]
                print(f"✅ PostgreSQL接続確認: {version[:80]}...")
            
            # 各テーブルの件数確認
            movie_count = Movie.query.count()
            article_count = Article.query.count()
            trending_count = TrendingData.query.count()
            
            print(f"📊 現在のデータ状況:")
            print(f"   🎬 映画データ: {movie_count} 件")
            print(f"   📰 記事データ: {article_count} 件")
            print(f"   📈 トレンドデータ: {trending_count} 件")
            
            # 初期データがない場合のみサンプルデータを追加
            needs_sample_data = movie_count == 0 and article_count == 0
            
            if needs_sample_data:
                print("🔧 初期サンプルデータを追加中...")
                
                # サンプル映画データ
                sample_movies = [
                    Movie(
                        movie_id="1",
                        title="劇場版「鬼滅の刃」無限列車編",
                        revenue=404.3,
                        year=2020,
                        release_date="2020/10/16",
                        category="邦画",
                        distributor="東宝",
                        description="炭治郎と仲間たちが無限列車で鬼と戦う物語。劇場版アニメとして歴史的な大ヒットを記録した作品。",
                        director="外崎春雄",
                        author="吾峠呼世晴",
                        actor="花江夏樹、鬼頭明里、下野紘、松岡禎丞",
                        genre="アニメ、アクション、ドラマ"
                    ),
                    Movie(
                        movie_id="2",
                        title="千と千尋の神隠し",
                        revenue=316.8,
                        year=2001,
                        release_date="2001/7/20",
                        category="邦画",
                        distributor="東宝",
                        description="不思議な世界に迷い込んだ少女千尋の冒険と成長を描いたスタジオジブリの代表作。",
                        director="宮崎駿",
                        author="宮崎駿",
                        actor="柊瑠美、入野自由、夏木マリ",
                        genre="アニメ、ファミリー、ファンタジー"
                    ),
                    Movie(
                        movie_id="3",
                        title="タイタニック",
                        revenue=262.0,
                        year=1997,
                        release_date="1997/12/20",
                        category="洋画",
                        distributor="20世紀フォックス",
                        description="1912年のタイタニック号沈没事故を背景にした壮大な恋愛ドラマ。",
                        director="ジェームズ・キャメロン",
                        author="ジェームズ・キャメロン",
                        actor="レオナルド・ディカプリオ、ケイト・ウィンスレット",
                        genre="ドラマ、恋愛、歴史"
                    ),
                    Movie(
                        movie_id="4",
                        title="アナと雪の女王",
                        revenue=255.0,
                        year=2014,
                        release_date="2014/3/14",
                        category="洋画",
                        distributor="ウォルト・ディズニー・ジャパン",
                        description="魔法の力を持つ姉妹エルサとアナの絆を描いたディズニーミュージカル。",
                        director="クリス・バック、ジェニファー・リー",
                        author="ハンス・クリスチャン・アンデルセン",
                        actor="神田沙也加、松たか子、津田英佑",
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
                        description="時空を超えて入れ替わる男女の恋愛を描いた新海誠監督作品。",
                        director="新海誠",
                        author="新海誠",
                        actor="神木隆之介、上白石萌音",
                        genre="アニメ、恋愛、ドラマ"
                    ),
                    Movie(
                        movie_id="6",
                        title="ハリー・ポッターと賢者の石",
                        revenue=203.0,
                        year=2001,
                        release_date="2001/12/1",
                        category="洋画",
                        distributor="ワーナー・ブラザース映画",
                        description="魔法使いの少年ハリー・ポッターの冒険を描いた第1作。",
                        director="クリス・コロンバス",
                        author="J.K.ローリング",
                        actor="ダニエル・ラドクリフ、エマ・ワトソン、ルパート・グリント",
                        genre="ファンタジー、アドベンチャー、ファミリー"
                    ),
                    Movie(
                        movie_id="7",
                        title="もののけ姫",
                        revenue=201.8,
                        year=1997,
                        release_date="1997/7/12",
                        category="邦画",
                        distributor="東宝",
                        description="人間と自然の対立を描いた宮崎駿監督の名作アニメーション。",
                        director="宮崎駿",
                        author="宮崎駿",
                        actor="松田洋治、石田ゆり子、田中裕子",
                        genre="アニメ、ドラマ、ファンタジー"
                    ),
                    Movie(
                        movie_id="8",
                        title="ハウルの動く城",
                        revenue=196.0,
                        year=2004,
                        release_date="2004/11/20",
                        category="邦画",
                        distributor="東宝",
                        description="魔法によって老婆にされた少女ソフィーとハウルの恋物語。",
                        director="宮崎駿",
                        author="ダイアナ・ウィン・ジョーンズ",
                        actor="倍賞千恵子、木村拓哉、美輪明宏",
                        genre="アニメ、恋愛、ファンタジー"
                    ),
                    Movie(
                        movie_id="9",
                        title="踊る大捜査線 THE MOVIE 2 レインボーブリッジを封鎖せよ！",
                        revenue=173.5,
                        year=2003,
                        release_date="2003/7/19",
                        category="邦画",
                        distributor="東宝",
                        description="青島俊作刑事の活躍を描いた人気シリーズの劇場版第2弾。",
                        director="本広克行",
                        author="君塚良一",
                        actor="織田裕二、柳葉敏郎、深津絵里",
                        genre="アクション、コメディ、ドラマ"
                    ),
                    Movie(
                        movie_id="10",
                        title="風の谷のナウシカ",
                        revenue=165.0,
                        year=1984,
                        release_date="1984/3/11",
                        category="邦画",
                        distributor="東映",
                        description="汚染された世界で生きる少女ナウシカの物語。スタジオジブリ設立前の宮崎駿作品。",
                        director="宮崎駿",
                        author="宮崎駿",
                        actor="島本須美、納谷悟朗、松田洋治",
                        genre="アニメ、SF、ドラマ"
                    )
                ]
                
                for movie in sample_movies:
                    db.session.add(movie)
                
                # サンプル記事データ
                sample_articles = [
                    Article(
                        title="日本映画興行収入歴代トップ10の分析",
                        content="""日本の映画興行収入歴代トップ10を分析すると、アニメーション作品が圧倒的な強さを見せています。特にスタジオジブリ作品と「鬼滅の刃」が上位を占めており、日本のアニメ文化の影響力の大きさがうかがえます。

「劇場版 鬼滅の刃 無限列車編」は404.3億円という歴史的な興行収入を記録し、日本映画史上最高額を達成しました。これは原作の人気に加え、テレビアニメの高いクオリティとパンデミック下での映画館への期待感が重なった結果と考えられます。

宮崎駿監督作品では「千と千尋の神隠し」「もののけ姫」「ハウルの動く城」がトップ10入りを果たしており、国際的な評価も高い作品群となっています。これらは単なる子供向けアニメではなく、大人も楽しめる深いテーマを持った作品として世代を超えて愛され続けています。

洋画では「タイタニック」「アナと雪の女王」「ハリー・ポッター」シリーズがランクインしており、ハリウッド大作映画の影響力も依然として強いことがわかります。特にディズニー作品は日本でも根強い人気を持っています。

このランキングから読み取れるのは、日本の観客は質の高いアニメーション作品を求めており、また感動的なストーリーと優れた映像美を持つ作品に対して高い支持を示すということです。""",
                        excerpt="「鬼滅の刃」から「千と千尋の神隠し」まで、日本映画興行収入トップ10の傾向と特徴を詳しく分析します。",
                        author="映画データアナリスト",
                        category="映画分析",
                        tags="興行収入,ランキング,アニメ,スタジオジブリ,鬼滅の刃",
                        is_featured=True
                    ),
                    Article(
                        title="アニメ映画が日本で成功する理由",
                        content="""日本でアニメ映画が圧倒的な成功を収める理由はいくつかあります。まず、日本独特のアニメ文化の成熟度が挙げられます。マンガ・アニメは子供だけでなく大人も楽しむエンターテインメントとして社会に根付いており、幅広い年齢層にアピールできる土壌があります。

技術的な観点では、日本のアニメーション技術は世界最高峰であり、特に手描きアニメーションにおいては他国の追随を許さないクオリティを保持しています。スタジオジブリの作品群や近年の「鬼滅の刃」などは、その技術力の高さを如実に示しています。

ストーリーテリングの面では、日本のアニメ映画は単純な勧善懲悪ではなく、複雑な人間関係や社会問題を扱うことが多く、観客に深い感動と考える機会を提供します。宮崎駿作品の環境問題への言及や、「鬼滅の刃」の家族愛のテーマなどは、観客の心に深く響きます。

また、日本のアニメ映画は音楽にも特別な注意を払います。久石譲の音楽が宮崎駿作品に与えた影響や、「鬼滅の刃」のLiSAの楽曲が社会現象になったことからも、音楽とアニメーションの相乗効果の重要性がわかります。

マーケティング戦略としても、テレビアニメとの連動、キャラクターグッズの展開、SNSでの話題性など、総合的なエンターテインメント体験を提供することで、単なる映画鑑賞を超えた価値を創造しています。""",
                        excerpt="技術力、ストーリーテリング、音楽、マーケティング戦略など、多角的な視点からアニメ映画成功の秘訣を探ります。",
                        author="アニメ産業研究者",
                        category="映画分析",
                        tags="アニメ,日本映画,スタジオジブリ,技術,ストーリー"
                    ),
                    Article(
                        title="SNS時代の映画マーケティング戦略",
                        content="""SNSの普及により、映画のマーケティング戦略は根本的に変化しました。従来のテレビCMや新聞広告中心の宣伝から、TwitterやInstagram、TikTokを活用したバイラルマーケティングが主流になっています。

「鬼滅の刃」の成功は、SNSマーケティングの好例です。ファンが自発的にイラストや感想を投稿し、それが新たな観客層の開拓につながりました。また、主題歌「炎」がTikTokで大流行したことも、映画の認知度向上に大きく貢献しました。

リアルタイム検索データを分析すると、映画の話題性と興行収入には強い相関関係があることがわかります。公開前の期待値、公開直後の口コミ、ロングランでの継続的な話題性、すべてがSNSでの投稿数に反映されています。

映画配給会社も、インフルエンサーとのタイアップ、ハッシュタグキャンペーン、限定コンテンツの配信など、SNSを活用した施策を積極的に展開しています。特に若年層をターゲットとした作品では、SNS戦略の成否が興行成績を大きく左右します。

今後は、AI分析によるトレンド予測、パーソナライズされた広告配信、バーチャル試写会など、より高度なデジタルマーケティング手法が導入されることが予想されます。""",
                        excerpt="SNS時代における映画マーケティングの変化と、成功事例から学ぶ新しい宣伝戦略について解説します。",
                        author="デジタルマーケティング専門家",
                        category="トレンド",
                        tags="SNS,マーケティング,デジタル,鬼滅の刃,トレンド分析"
                    ),
                    Article(
                        title="コロナ禍が映画業界に与えた影響と変化",
                        content="""新型コロナウイルスの感染拡大は、映画業界に甚大な影響を与えました。2020年春の緊急事態宣言下では多くの映画館が休業を余儀なくされ、映画の公開延期が相次ぎました。

しかし興味深いことに、この状況下で公開された「劇場版 鬼滅の刃 無限列車編」は歴史的な大ヒットを記録しました。これは「映画館でしか味わえない体験」への観客の渇望と、家族で安心して楽しめるコンテンツへの需要が重なった結果と考えられます。

映画館では感染対策として、座席の間隔確保、上映回数の調整、換気システムの強化などの対策が実施されました。また、オンライン予約システムの充実により、接触機会の削減も図られました。

配信サービスの利用も急速に拡大し、映画の配給形態に変化をもたらしました。劇場公開と同時配信、劇場公開期間の短縮など、従来の「劇場→DVD→配信」という流れに変化が生じています。

ポストコロナの映画業界では、劇場体験の価値向上（IMAX、4D、プレミアムシートなど）と、多様な配信チャネルの活用という二極化が進むと予想されます。また、VRやARを活用した新しい映画体験の開発も進んでおり、映画業界の未来は大きな変革期を迎えています。""",
                        excerpt="パンデミックが映画業界に与えた影響と、それに伴う配給形態や観客行動の変化について分析します。",
                        author="映画業界アナリスト",
                        category="業界動向",
                        tags="コロナ禍,映画業界,配信,劇場,変化"
                    )
                ]
                
                for article in sample_articles:
                    db.session.add(article)
                
                # サンプルトレンドデータ
                today = datetime.now().strftime('%Y/%m/%d')
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
                
                sample_trends = [
                    # 今日のデータ
                    TrendingData(date=today, movie_title="劇場版「鬼滅の刃」無限列車編", post_count=8500),
                    TrendingData(date=today, movie_title="君の名は。", post_count=5200),
                    TrendingData(date=today, movie_title="千と千尋の神隠し", post_count=4800),
                    TrendingData(date=today, movie_title="アナと雪の女王", post_count=3600),
                    TrendingData(date=today, movie_title="もののけ姫", post_count=3200),
                    TrendingData(date=today, movie_title="ハウルの動く城", post_count=2800),
                    TrendingData(date=today, movie_title="タイタニック", post_count=2400),
                    TrendingData(date=today, movie_title="風の谷のナウシカ", post_count=2100),
                    TrendingData(date=today, movie_title="踊る大捜査線", post_count=1800),
                    TrendingData(date=today, movie_title="ハリー・ポッター", post_count=1500),
                    
                    # 昨日のデータ
                    TrendingData(date=yesterday, movie_title="劇場版「鬼滅の刃」無限列車編", post_count=7800),
                    TrendingData(date=yesterday, movie_title="君の名は。", post_count=4900),
                    TrendingData(date=yesterday, movie_title="千と千尋の神隠し", post_count=4600),
                    TrendingData(date=yesterday, movie_title="アナと雪の女王", post_count=3400),
                    TrendingData(date=yesterday, movie_title="もののけ姫", post_count=3000),
                ]
                
                for trend in sample_trends:
                    db.session.add(trend)
                
                # データをコミット
                db.session.commit()
                
                print(f"✅ サンプルデータ追加完了:")
                print(f"   🎬 映画データ: {len(sample_movies)} 件")
                print(f"   📰 記事データ: {len(sample_articles)} 件")
                print(f"   📈 トレンドデータ: {len(sample_trends)} 件")
            else:
                print("ℹ️ 既存データがあるため、サンプルデータの追加をスキップしました")
            
            # 最終統計
            final_movie_count = Movie.query.count()
            final_article_count = Article.query.count()
            final_trending_count = TrendingData.query.count()
            
            print("\n📊 データベース初期化完了:")
            print(f"   🎬 映画データ: {final_movie_count} 件")
            print(f"   📰 記事データ: {final_article_count} 件")
            print(f"   📈 トレンドデータ: {final_trending_count} 件")
            
            return True
            
        except Exception as e:
            print(f"❌ データベース初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print(f"⏰ 実行時刻: {datetime.now()}")
    
    success = main()
    
    print("=" * 60)
    if success:
        print("✅ Render初期化スクリプト完了！")
        print("🚀 アプリケーションを起動できます。")
    else:
        print("❌ 初期化に失敗しました。ログを確認してください。")
        sys.exit(1)