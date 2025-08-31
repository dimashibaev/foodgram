import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Загрузка ингредиентов из списка"

    def add_arguments(self, parser):
        parser.add_argument("json_path", help="Путь к JSON-файлу")
        parser.add_argument("--update", action="store_true",
                            help="Обновлять единицу измерения у существующих")

    def handle(self, *args, **opts):
        path = Path(opts["json_path"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as e:
            raise CommandError(f"Не удалось прочитать JSON: {e}")

        if not isinstance(data, list):
            raise CommandError("Ожидался список объектов.")

        seen = set()
        created = updated = skipped = 0

        for i, item in enumerate(data, 1):
            name = (item.get("name") or "").strip()
            mu = (item.get("measurement_unit") or "").strip()

            if not name or not mu:
                skipped += 1
                continue

            key = name.casefold()
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            obj, is_new = Ingredient.objects.get_or_create(
                name=name,
                defaults={"measurement_unit": mu}
            )
            if is_new:
                created += 1
                continue

            if opts["update"] and obj.measurement_unit != mu:
                obj.measurement_unit = mu
                obj.save(update_fields=["measurement_unit"])
                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово: создано {created}, "
            f"обновлено {updated}, пропущено {skipped}"
        ))
