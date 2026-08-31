from googlesearch import search
import pandas as pd

def search_instagram_comments(username):
    print(f"[*] جاري البحث عن تعليقات وإشارات تخص الحساب: {username}")
    
    # صيغ بحث أوتوماتيكية متقدمة تستهدف أرشيف محركات البحث
    queries = [
        f'site:instagram.com/reel/ "{username}"',
        f'site:instagram.com/p/ "{username}"',
        f'site:instagram.com "@{username}"'
    ]
    
    results_list = []
    
    for query in queries:
        print(f"[*] تنفيذ الاستعلام: {query}")
        try:
            # البحث في جوجل بدون حظر سريع
            for url in search(query, num_results=10):
                results_list.append({"Query": query, "URL": url})
        except Exception as e:
            print(f"[-] حدث خطأ أثناء البحث: {e}")
            
    # حفظ النتائج بملف CSV
    if results_list:
        df = pd.DataFrame(results_list)
        df.to_csv("results.csv", index=False)
        print("[+] تم حفظ النتائج بنجاح في ملف results.csv")
    else:
        print("[-] لم يتم العثور على نتائج مطابقة.")

if __name__ == "__main__":
    # اليوزرنيم المستهدف للبحث
    target_user = "rrenguk"
    search_instagram_comments(target_user)
