class LayoutCalculator:
    def __init__(self, sheet_width, sheet_height, card_width, card_height,
                 margin, bleed, rotate=False):
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.card_width = card_width
        self.card_height = card_height
        self.margin = margin
        self.bleed = bleed
        self.rotate = rotate

        # Рабочая область с учетом полей и вылетов
        self.work_width = sheet_width - 2 * margin + 2 * bleed
        self.work_height = sheet_height - 2 * margin + 2 * bleed

    def calculate_layout(self):
        """Рассчитать оптимальную раскладку"""
        # Пробуем оба варианта: обычный и повернутый
        layouts = []

        # Без поворота
        normal_layout = self._calculate_single_layout(False)
        if normal_layout['cards_total'] > 0:
            layouts.append(normal_layout)

        # С поворотом
        if self.rotate:
            rotated_layout = self._calculate_single_layout(True)
            if rotated_layout['cards_total'] > 0:
                layouts.append(rotated_layout)

        # Выбираем лучшую раскладку
        if not layouts:
            return self._get_empty_layout()

        best_layout = max(layouts, key=lambda x: x['cards_total'])
        return best_layout

    def _calculate_single_layout(self, rotated):
        """Рассчитать раскладку для одного варианта"""
        if rotated:
            card_w, card_h = self.card_height, self.card_width  # Меняем местами
        else:
            card_w, card_h = self.card_width, self.card_height

        # Проверяем, помещается ли хотя бы одна визитка
        if card_w > self.work_width or card_h > self.work_height:
            return self._get_empty_layout()

        # Рассчитываем количество визиток
        cards_x = int(self.work_width // card_w)
        cards_y = int(self.work_height // card_h)

        if cards_x == 0 or cards_y == 0:
            return self._get_empty_layout()

        # Рассчитываем отступы для центрирования
        total_width = cards_x * card_w
        total_height = cards_y * card_h

        offset_x = (self.work_width - total_width) / 2 + self.margin - self.bleed
        offset_y = (self.work_height - total_height) / 2 + self.margin - self.bleed

        # Генерируем позиции для каждой визитки
        positions = []
        for y in range(cards_y):
            for x in range(cards_x):
                pos_x = offset_x + x * card_w
                pos_y = offset_y + y * card_h
                positions.append({
                    'x': pos_x,
                    'y': pos_y,
                    'width': card_w,
                    'height': card_h,
                    'rotated': rotated
                })

        return {
            'cards_x': cards_x,
            'cards_y': cards_y,
            'cards_total': cards_x * cards_y,
            'positions': positions,
            'rotated': rotated,
            'efficiency': (total_width * total_height) / (self.work_width * self.work_height)
        }

    def _get_empty_layout(self):
        return {
            'cards_x': 0,
            'cards_y': 0,
            'cards_total': 0,
            'positions': [],
            'rotated': False,
            'efficiency': 0
        }

    def calculate_sheets_needed(self, total_cards):
        """Рассчитать количество листов"""
        layout = self.calculate_layout()
        if layout['cards_total'] == 0:
            return 0
        return (total_cards + layout['cards_total'] - 1) // layout['cards_total']