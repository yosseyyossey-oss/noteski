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
        page.wait_for_timeout(8000) 

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
            # 新着順ソート（mode=search&sort=new）のURLを作成
            url = f"https://note.com/search?q={urllib.parse.quote(word)}&context=note&mode=search&sort=new"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 【補強処理】UI上の「新着」タブを確実にクリックして新着順を保証
            try:
                new_tab = page.locator('a:has-text("新着"), button:has-text("新着")').first
                if new_tab.is_visible():
                    new_tab.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            # 複数回スクロールして最新記事を読み込ませる
            for _ in range(3):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(2000)
            
            # 全てのスキボタン要素を取得
            btns_locator = page.locator('button[aria-label*="スキ"]')
            count_in_page = btns_locator.count()
            
            valid_btns = []
            for idx in range(count_in_page):
                btn = btns_locator.nth(idx)
                try:
                    aria_pressed = btn.get_attribute("aria-pressed")
                    aria_label = btn.get_attribute("aria-label") or ""
                    
                    # 【重要】過去に既にスキを押した記事（aria-pressed="true" や「スキを取り消す」）を除外
                    if aria_pressed == "true" or "スキを取り消す" in aria_label or "取り消す" in aria_label:
                        continue
                        
                    # 「この記事にスキをつけたユーザーを見る」が含まれる未実行ボタンのみを保持
                    if "この記事にスキをつけたユーザーを見る" in aria_label:
                        valid_btns.append(btn)
                except Exception:
                    continue

            print(f"🔎 「{word}」で未実行（新着）のボタンを {len(valid_btns)} 個発見")

            for target_btn in valid_btns:
                if total_count >= MAX_LIKES:
                    break
                
                try:
                    if target_btn.is_visible():
                        user_name = "Unknown"
                        try:
                            # 記事カードの親要素からユーザー名を特定
                            parent_card = target_btn.locator('xpath=./ancestor::*[self::article or self::section or contains(@class, "Wrapper") or contains(@class, "Note")][1]')
                            user_element = parent_card.locator('a[href*="/n/"], [class*="userName"], [class*="user"]').first
                            if user_element.count() > 0:
                                user_name = user_element.inner_text().strip().split('\n')[0]
                        except Exception:
                            pass

                        # 今回の起動ですでにスキを押した同一ユーザーならスキップ
                        if user_name != "Unknown" and user_name in processed_users:
                            continue
                        
                        target_btn.scroll_into_view_if_needed()
                        page.wait_for_timeout(random.randint(2000, 4000))
                        
                        target_btn.click(force=True)
                        total_count += 1
                        
                        if user_name != "Unknown":
                            processed_users.add(user_name)
                            print(f"[{total_count}/{MAX_LIKES}] スキ！ ({word} / ユーザー: {user_name})")
                        else:
                            print(f"[{total_count}/{MAX_LIKES}] スキ！ ({word})")
                        
                        # 検出回避のためのランダム待機
                        time.sleep(random.uniform(10, 18))
                except Exception:
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
