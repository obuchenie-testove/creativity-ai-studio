#!/usr/bin/env python3
"""Compile complete, readable task contexts for environments without internet scripts."""
import json
from pathlib import Path
from resolve import resolve, json_read

def build(root):
    root=Path(root)
    manifest=json_read((root/'references/protocol-bank/manifest.json').read_bytes())
    outputs=[]
    for entry in manifest['entries']:
        if entry['kind']!='task':continue
        context=resolve(root,entry['id'])
        lines=[f"# {entry['title']} — Creativity LTD",'',
               'Пилотен пакет 0.1.0. Прочети всички правила по-долу. Не е нормативна база.',
               'При работа без хеширащ инструмент отчети integrity_status=NOT_RUN. Записаните хешове не означават извършена от теб проверка.',
               'При получен файл със съмнителен произход или установено несъответствие спри използването му.',
               'Режим: portable-snapshot; няма автоматично live обновяване.',
               f"Manifest SHA-256: {context['snapshot_sha256']}",
               'Изпълни ролите по посочения ред; Завършващият проверява окончателния резултат след изпълнението на задачата.', '']
        for item in context['selected_protocols']:
            content=item['content']
            lines += [f"## {content['title']} ({item['id']})",'',
                      f"Версия: {item['version']}; SHA-256: {item['sha256']}",'']
            lines += [f'{i}. {rule}' for i,rule in enumerate(content['rules'],1)]
            if content['output_fields']:
                lines += ['','Полета на резултата: '+', '.join(content['output_fields'])]
            lines += ['']
        lines += ['## Интеграции и източници','',(root/'references/integration.md').read_text(encoding='utf-8')]
        if (root/'references/curriculum.md').exists():
            lines += ['## Педагогическа рамка','',(root/'references/curriculum.md').read_text(encoding='utf-8')]
        path=root/'references/packs'/f"{entry['id'].removeprefix('task-')}.md"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        outputs.append(path.name)
    return outputs

if __name__=='__main__':
    print(json.dumps(build(Path(__file__).resolve().parents[1]),ensure_ascii=False))
