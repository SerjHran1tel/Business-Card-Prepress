# Стандартные размеры листов (ширина × высота в мм)
SHEET_SIZES = {
    'A3': (297, 420),
    'A4': (210, 297),
    'A5': (148, 210),
    'Letter': (216, 279)
}

# Стандартные размеры визиток (ширина × высота в мм)
CARD_SIZES = {
    'Стандартная (90×50)': (90, 50),
    'Евро (85×55)': (85, 55),
    'Квадратная (90×90)': (90, 90),
    'Произвольный': None
}

class PrintConfig:
    def __init__(self):
        self.sheet_size = 'A4'
        self.card_size = 'Стандартная (90×50)'
        self.custom_card_width = 90
        self.custom_card_height = 50
        self.margin = 5
        self.bleed = 3
        self.gutter = 0
        self.rotate_cards = False
        self.add_crop_marks = True
        self.front_files = []  # NEW: список путей к файлам лицевых сторон
        self.back_files = []   # NEW: список путей к файлам оборотных сторон

    def get_sheet_dimensions(self):
        return SHEET_SIZES.get(self.sheet_size, (210, 297))

    def get_card_dimensions(self):
        if self.card_size == 'Произвольный':
            return (self.custom_card_width, self.custom_card_height)
        return CARD_SIZES.get(self.card_size, (90, 50))