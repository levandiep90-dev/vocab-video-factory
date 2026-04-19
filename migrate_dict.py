import os
from dictionary_lib import get_dict

# 1. Đây là dữ liệu MINI_DICT cũ của Cốm (Copy y hệt từ file main sang đây)
OLD_MINI_DICT = {
    "run": ("chạy", "I run every morning."),
    "walk": ("đi bộ", "I walk to school."),
    "jump": ("nhảy", "The boy jumps high."),
    "climb": ("leo trèo", "She climbs a tree."),
    "stand": ("đứng", "Please stand here."),
    "sit": ("ngồi", "Sit on the chair."),
    "eat": ("ăn", "I eat rice."),
    "drink": ("uống", "I drink water."),
    "sleep": ("ngủ", "The baby sleeps."),
    "wake up": ("thức dậy", "I wake up early."),
    "laugh": ("cười", "She laughs happily."),
    "cry": ("khóc", "The baby cries."),
    "open": ("mở", "Open the door."),
    "close": ("đóng", "Close the door."),
    "push": ("đẩy", "Push the door."),
    "pull": ("kéo", "Pull the rope."),
    "throw": ("ném", "Throw the ball."),
    "catch": ("bắt", "Catch the ball."),
    "write": ("viết", "I write my name."),
    "read": ("đọc", "I read a book."),
    "draw": ("vẽ", "I draw a picture."),
    "color": ("tô màu", "Color the picture."),
    "cut": ("cắt", "Cut the paper."),
    "glue": ("dán", "Glue the paper."),
    "swim": ("bơi", "Fish swim in water."),
    "dance": ("nhảy múa", "She dances well."),
    "sing": ("hát", "He sings a song."),
    "stop": ("dừng lại", "Stop here."),
    "run fast": ("chạy nhanh", "I run fast."),
    "walk slow": ("đi chậm", "Walk slowly."),
    "dog": ("con chó", "The dog is running."),
    "cat": ("con mèo", "The cat is sleeping."),
    "bird": ("con chim", "A bird can fly."),
    "fish": ("con cá", "Fish swim in water."),
    "duck": ("con vịt", "The duck swims."),
    "chicken": ("con gà", "The chicken is eating."),
    "cow": ("con bò", "The cow eats grass."),
    "pig": ("con lợn", "The pig is fat."),
    "horse": ("con ngựa", "The horse runs fast."),
    "sheep": ("con cừu", "The sheep is white."),
    "goat": ("con dê", "The goat climbs."),
    "rabbit": ("con thỏ", "The rabbit jumps."),
    "lion": ("con sư tử", "The lion is strong."),
    "tiger": ("con hổ", "The tiger is big."),
    "elephant": ("con voi", "The elephant is big."),
    "monkey": ("con khỉ", "The monkey climbs."),
    "bear": ("con gấu", "The bear eats honey."),
    "giraffe": ("con hươu cao cổ", "The giraffe is tall."),
    "frog": ("con ếch", "The frog jumps."),
    "snake": ("con rắn", "The snake is long."),
    "turtle": ("con rùa", "The turtle walks slowly."),
    "crocodile": ("con cá sấu", "The crocodile is dangerous."),
    "fox": ("con cáo", "The fox is clever."),
    "wolf": ("con sói", "The wolf howls."),
    "bee": ("con ong", "The bee makes honey."),
    "butterfly": ("con bướm", "The butterfly is beautiful."),
    "ant": ("con kiến", "The ant is small."),
    "spider": ("con nhện", "The spider spins a web."),
    "fly": ("con ruồi", "The fly is annoying."),
    "mosquito": ("con muỗi", "The mosquito bites."),
    "apple": ("quả táo", "I eat an apple."),
    "banana": ("quả chuối", "She eats a banana."),
    "orange": ("quả cam", "The orange is sweet."),
    "mango": ("quả xoài", "I like mango."),
    "grape": ("quả nho", "Grapes are sweet."),
    "watermelon": ("dưa hấu", "Watermelon is big."),
    "pineapple": ("dứa", "Pineapple is tasty."),
    "strawberry": ("dâu tây", "Strawberries are red."),
    "lemon": ("chanh", "Lemon is sour."),
    "peach": ("đào", "The peach is soft."),
    "pear": ("lê", "The pear is sweet."),
    "cherry": ("anh đào", "Cherries are small."),
    "rice": ("cơm", "I eat rice."),
    "bread": ("bánh mì", "I eat bread."),
    "noodles": ("mì", "I eat noodles."),
    "soup": ("súp", "The soup is hot."),
    "egg": ("trứng", "I eat an egg."),
    "meat": ("thịt", "I eat meat."),
    "fish food": ("cá (món ăn)", "I eat fish."),
    "milk": ("sữa", "I drink milk."),
    "juice": ("nước ép", "I drink juice."),
    "water": ("nước", "Drink water."),
    "tea": ("trà", "I drink tea."),
    "coffee": ("cà phê", "I drink coffee."),
    "cake": ("bánh", "I eat cake."),
    "candy": ("kẹo", "I like candy."),
    "chocolate": ("sô cô la", "Chocolate is sweet."),
    "cookie": ("bánh quy", "I eat cookies."),
    "donut": ("bánh donut", "The donut is sweet."),
    "pizza": ("pizza", "I eat pizza."),
    "burger": ("hamburger", "I eat a burger."),
    "red": ("màu đỏ", "The apple is red."),
    "blue": ("màu xanh dương", "The sky is blue."),
    "yellow": ("màu vàng", "The sun is yellow."),
    "green": ("màu xanh lá", "The tree is green."),
    "black": ("màu đen", "The cat is black."),
    "white": ("màu trắng", "The sheep is white."),
    "orange color": ("màu cam", "The orange is orange."),
    "purple": ("màu tím", "The flower is purple."),
    "pink": ("màu hồng", "The dress is pink."),
    "brown": ("màu nâu", "The bear is brown."),
    "gray": ("màu xám", "The sky is gray."),
    "one": ("một", "I have one book."),
    "two": ("hai", "Two cats are here."),
    "three": ("ba", "I see three dogs."),
    "four": ("bốn", "Four apples are here."),
    "five": ("năm", "I have five fingers."),
    "six": ("sáu", "Six birds fly."),
    "seven": ("bảy", "Seven days a week."),
    "eight": ("tám", "Eight cookies."),
    "nine": ("chín", "Nine balls."),
    "ten": ("mười", "Ten fingers."),
    "father": ("bố", "My father is kind."),
    "mother": ("mẹ", "My mother cooks."),
    "brother": ("anh/em trai", "My brother plays."),
    "sister": ("chị/em gái", "My sister sings."),
    "baby": ("em bé", "The baby sleeps."),
    "grandma": ("bà", "Grandma loves me."),
    "grandpa": ("ông", "Grandpa tells stories."),
    "family": ("gia đình", "I love my family."),
    "friend": ("bạn bè", "My friend is nice."),
    "sit down": ("ngồi xuống", "Please sit down."),
    "stand up": ("đứng lên", "Stand up."),
    "come here": ("lại đây", "Come here."),
    "go home": ("về nhà", "Go home."),
}

def migrate():
    print("🚀 Bắt đầu quá trình chuyển đổi dữ liệu...")
    
    # 1. Khởi tạo thư viện
    d = get_dict()
    
    # 2. Định nghĩa các nhóm tương ứng với dữ liệu cũ
    # Vì MINI_DICT cũ không chia nhóm, mình sẽ gán tạm vào nhóm "OTHERS" 
    # hoặc Cốm có thể tự sửa lại mapping này nếu muốn chia nhóm ngay từ đầu.
    mapping = {
        "ACTIONS": ["run", "walk", "jump", "climb", "stand", "sit", "eat", "drink", "sleep", "wake up", "laugh", "cry", "open", "close", "push", "pull", "throw", "catch", "write", "read", "draw", "color", "cut", "glue", "swim", "dance", "sing", "stop", "run fast", "walk slow"],
        "ANIMALS": ["dog", "cat", "bird", "fish", "duck", "chicken", "cow", "pig", "horse", "sheep", "goat", "rabbit", "lion", "tiger", "elephant", "monkey", "bear", "giraffe", "frog", "snake", "turtle", "crocodile", "fox", "wolf", "bee", "butterfly", "ant", "spider", "fly", "mosquito"],
        "FOOD": ["apple", "banana", "orange", "mango", "grape", "watermelon", "pineapple", "strawberry", "lemon", "peach", "pear", "cherry", "rice", "bread", "noodles", "soup", "egg", "meat", "fish food", "milk", "juice", "water", "tea", "coffee", "cake", "candy", "chocolate", "cookie", "donut", "pizza", "burger"],
        "COLORS": ["red", "blue", "yellow", "green", "black", "white", "orange color", "purple", "pink", "brown", "gray"],
        "NUMBERS": ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"],
        "FAMILY": ["father", "mother", "brother", "sister", "baby", "grandma", "grandpa", "family", "friend"],
        "COMMANDS": ["sit down", "stand up", "come here", "go home", "open book", "read book", "write name", "draw picture", "play game", "watch tv", "listen music", "sing song", "dance happily"]
    }

    count = 0
    
    # 3. Duyệt qua từng từ trong OLD_MINI_DICT
    for word, (meaning, example) in OLD_MINI_DICT.items():
        target_group = "OTHERS" # Mặc định là nhóm khác
        
        # Kiểm tra xem từ này thuộc nhóm nào trong mapping
        for group_name, word_list in mapping.items():
            if word.lower() in word_list:
                target_group = group_name
                break
        
        # 4. Thêm vào thư viện
        # Kiểm tra nếu từ đã tồn tại trong nhóm đó chưa để tránh trùng
        current_words = d.get_words_in_group(target_group)
        if word.lower() not in current_words:
            d.add_word(target_group, word, meaning, example)
            count += 1
            print(f"✅ Đã chuyển: [{target_group}] {word} -> {meaning}")
        else:
            print(f"⚠️ Bỏ qua (đã tồn tại): {word}")

    # 5. Lưu lại
    d.save()
    print("\n" + "="*30)
    print(f"🎉 HOÀN THÀNH! Đã chuyển thành công {count} từ vào dictionary_data.json")
    print("="*30)

if __name__ == "__main__":
    migrate()
