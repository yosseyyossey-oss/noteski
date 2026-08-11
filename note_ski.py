import time
import random
import os
import json
import urllib.parse
import re
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
    MAX_LIKES = 20  # 20件目標

    # 重複除外用セット（同一起動内での同クリエイターへの重複防止）
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
        page.wait_for_timeout(3000)

        # ログイン確認
        if "つくる、つながる" in page.title():
            print("❌ ログイン失敗判定。終了します。")
            browser.close()
            return
        print("✅ ログイン成功を確認！")

        for word in keywords:
            if total_count >= MAX_LIKES:
                break

            print(f"🔎 検索開始: 【{word}】 (目標: 20件 / 現在: {total_count}件)")
            # 新着順（sort=new）で検索URLを生成
            url = f"https://note.com/search?q={urllib.parse.quote(word)}&mode=search&sort=new"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            time_pattern = re.compile(r'\d+(?:か月|日|時間|分|年)前')
            time_locator = page.get_by_text(time_pattern)

            # 投稿時間テキストの描画完了を待機
            try:
                time_locator.first.wait_for(state="visible", timeout=15000)
            except Exception:
                print(f"⚠️ 【{word}】 投稿時間テキストの描画タイムアウト（次のワードへ）")
                continue

            time_elements = time_locator.all()
            print(f"🔎 【{word}】 画面表面の投稿時間テキストを {len(time_elements)} 件検出")

            for time_elem in time_elements:
                if total_count >= MAX_LIKES:
                    break

                try:
                    post_time = time_elem.inner_text().strip()

                    # 投稿時間テキストの「すぐ直後」に存在するbutton（ハートマーク）を指定
                    btn = time_elem.locator('xpath=following::button[1]')

                    if btn.count() == 0 or not btn.is_visible():
                        continue

                    # 既にスキ済み（aria-pressed="true"）の場合は重複防止でスキップ
                    if btn.get_attribute("aria-pressed") == "true":
                        continue

                    # 投稿時間テキストの「すぐ直前」に存在するリンク要素から情報を取得
                    link = time_elem.locator('xpath=preceding::a[1]')
                    target_url = "Unknown"
                    user_name = "Unknown"

                    if link.count() > 0:
                        href = link.get_attribute("href")
                        if href:
                            target_url = href if href.startswith("http") else f"https://note.com{href}"
                        text = link.inner_text().strip()
                        if text:
                            user_name = text

                    # 今回の起動で既にスキ済みの同一ユーザーなら重複防止でスキップ
                    if user_name != "Unknown" and user_name in processed_users:
                        continue

                    btn.scroll_into_view_if_needed()
                    page.wait_for_timeout(random.randint(1500, 3000))

                    btn.click(force=True)
                    total_count += 1

                    if user_name != "Unknown":
                        processed_users.add(user_name)

                    print(f"🎉 [{total_count}/{MAX_LIKES}] スキ成功！")
                    print(f"  ├ キーワード : {word}")
                    print(f"  ├ 対象/ユーザー: {user_name}")
                    print(f"  ├ 投稿時間   : {post_time}")
                    print(f"  └ 参照URL    : {target_url}\n")

                except Exception as e:
                    continue

            if total_count >= MAX_LIKES:
                print("🎯 目標（20件）を達成したため処理を終了します。")
                break

        # クッキー更新保存
        try:
            with open("cookie.txt", "w", encoding="utf-8") as f:
                json.dump(context.cookies(), f, indent=2)
        except Exception as e:
            print(f"⚠️ クッキー保存失敗: {e}")

        browser.close()
        print(f"--- 実行完了: 合計 {total_count}件 ---")

if __name__ == "__main__":
    run()
