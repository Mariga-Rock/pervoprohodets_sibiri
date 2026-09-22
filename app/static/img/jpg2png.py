from PIL import Image
import os
import sys


def jpg_to_png(input_path: str) -> str:
    """
    Конвертирует JPG в PNG и кладёт рядом с оригиналом.
    Возвращает путь к новому файлу.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Файл не найден: {input_path}")

    with Image.open(input_path) as img:
        # Формируем путь: та же папка, то же имя, но .png
        directory, filename = os.path.split(input_path)
        name, _ = os.path.splitext(filename)
        output_path = os.path.join(directory, f"{name}.png")

        img.save(output_path, "PNG")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python jpg2png.py <путь_к_картинке.jpg>")
        sys.exit(1)

    out = jpg_to_png(sys.argv[1])
    print(f"Готово: {out}")
