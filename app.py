import random

def generate_random_key():
    # الحرف المسموحة بعد استبعاد (O, 0, I, 1, B, 8)
    # الأحرف المتبقية: A, C, D, E, F, G, H, J, K, L, M, N, P, Q, R, S, T, U, V, W, X, Y, Z (20 حرف)
    # الأرقام المتبقية: 2, 3, 4, 5, 6, 7, 9 (7 أرقام)
    chars = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"
    
    # دالة لتوليد مقطع واحد مكون من 5 خانات عشوائية
    def generate_segment():
        return "".join(random.choices(chars, k=5))
    
    # تكوين النمط المطلوب: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    segments = [generate_segment() for _ in range(5)]
    return "-".join(segments)

# تجربة توليد مفتاح عشوائي
if __name__ == "__main__":
    print("المفتاح المولّد:")
    print(generate_random_key())
