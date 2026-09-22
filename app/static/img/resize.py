from PIL import Image
import os
import sys


def resize_to_png(input_path: str, size: int = 128) -> str:
    """
    Берёт картинку, ресайзит до size x size,
    сохраняет рядом как PNG с прозрачностью (RGBA).
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")

    with Image.open(input_path) as img:
        # Сохраняем альфа-канал, если он есть; иначе добавляем
        img = img.convert("RGBA")

        resized = img.resize((size, size), Image.LANCZOS)

        directory, filename = os.path.split(input_path)
        name, _ = os.path.splitext(filename)
        output_path = os.path.join(directory, f"{name}_{size}x{size}.png")

        resized.save(output_path, "PNG")  # PNG сохраняет прозрачность

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python resize.py <путь_к_картинке>")
        sys.exit(1)

    out = resize_to_png(sys.argv[1], 128)
    print(f"Готово: {out}")
