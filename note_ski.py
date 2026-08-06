import time
import random
import os
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

def run():
    # --- 日本時間の取得 ---
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    hour = now.hour

    # 深夜 2:00 ～ 5:00 は停止
    if 2 <= hour < 5:
        print(f"💤 現在 {hour}時（深夜2:00-5:00）のため、動作を停止します。")
        return

    # ボリューム重視の固定キーワード
    keywords = [
        "日記", "エッセイ", "毎日note", "自己紹介", "毎日更新",
        "ビジネス", "ライフスタイル", "生き方", "考え方", "習慣",
        "感謝", "副業", "学び", "メンタルケア", "人間関係",
        "仕事", "写真", "デザイン", "読書", "料理",
        "イラスト", "マンガ", "小説", "最近の学び", "振り返り"
    ]
    
    random.shuffle(keywords)
    total_count = 0
    MAX_LIKES = 20
    
    # 処理済みユーザーを記録するセット（同一稼働内での重複防止）
    processed_users = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.3856.59",
            viewport={'width': 1920, 'height': 1080}
        )

        # クッキー適用
        if os.path.exists("cookie.txt"):
            try:
                with open("cookie.txt", "r", encoding="utf-8") as f:
                    raw_cookies = json.load(f)
                context.add_cookies(raw_cookies)
                print(f"✅ クッキー適用完了: {len(raw_cookies)}件")
            except Exception as e:
                print(f"⚠️ クッキーエラー回避: {e}")

        page = context.new_page()

        print(f"🚀 noteへアクセス中... (現在時刻: {hour}時)")
        page.goto("https://note.com/notifications", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(10000) 

        # ログイン確認
        if "つくる、つながる" in page.title():
            print("❌ ログイン失敗判定。終了します。")
            browser.close()
            return
        print("✅ ログイン成功を確認！")

        # --- キーワードループ ---
        for word in keywords:
            if total_count >= MAX_LIKES:
                break
            
            print(f"🔎 検索開始: 【{word}】 (現在の合計: {total_count}/{MAX_LIKES})")
            url = f"https://note.com/search?q={urllib.parse.quote(word)}&mode=search&sort=new"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # 【重要】複数回スクロールして読み込みを安定させる
            for _ in range(3):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2500)
            
            # 未実行のボタンを動的に取得するためのロケーター
            btns_locator = page.locator('button[aria-label="スキ"][aria-pressed="false"]')
            count_in_page = btns_locator.count()
            print(f"🔎 「{word}」で未実行のボタンを {count_in_page} 個発見")

            for i in range(count_in_page):
                if total_count >= MAX_LIKES:
                    break
                
                try:
                    target_btn = btns_locator.nth(i)
                    # ボタンが有効かつ表示されているか確認
                    if target_btn.is_visible():
                        
                        # --- 【提供ソースを基に確実な抽出へ修正】 ---
                        user_name = "Unknown"
                        try:
                            # スキボタンから上へ辿り、同じ記事ブロック（m-largeNoteWrapper）の中にあるユーザー名領域を特定
                            parent_card = target_btn.locator('xpath=./ancestor::section[contains(@class, "m-largeNoteWrapper")][1]')
                            user_element = parent_card.locator('.o-largeNoteSummary__userName')
                            if user_element.count() > 0:
                                user_name = user_element.inner_text().strip()
                        except:
                            pass

                        # 既に今回の起動でスキ済みのユーザーならスキップ
                        if user_name != "Unknown" and user_name in processed_users:
                            continue
                        
                        target_btn.scroll_into_view_if_needed()
                        page.wait_for_timeout(random.randint(2000, 4000)) # クリック前の溜め
                        
                        target_btn.click(force=True)
                        total_count += 1
                        
                        # スキしたユーザー名を記録
                        if user_name != "Unknown":
                            processed_users.add(user_name)
                            print(f"[{total_count}/{MAX_LIKES}] スキ！ ({word} / ユーザー: {user_name})")
                        else:
                            print(f"[{total_count}/{MAX_LIKES}] スキ！ ({word})")
                        
                        # 検知回避のための待機（少し短縮して効率化）
                        time.sleep(random.uniform(10, 18))
                except:
                    continue
            
            if total_count < MAX_LIKES:
                print(f"💡 「{word}」の処理を終了。次へ進みます。")

        # 最後にセッションを更新保存
        with open("cookie.txt", "w", encoding="utf-8") as f:
            json.dump(context.cookies(), f, indent=2)

        browser.close()
    print(f"--- 全行程完了: 合計 {total_count}件 ---")

if __name__ == "__main__":
    run()
